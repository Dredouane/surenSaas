"""
Service d'extraction de chaîne d'emails.

Utilise le parsing .eml pour extraire tous les emails d'une chaîne de forwards,
les stocke dans la base, et les lie au même thread Gmail.
"""

import asyncio
import base64
import hashlib
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailChainService:
    """Service d'extraction et stockage des chaînes d'emails."""

    async def process_chain(
        self,
        gmail_client,
        gmail_message_id: str,
        gmail_thread_id: str,
        account_id: str,
        org_id: str,
        company_id: Optional[str] = None,
        delivered_to: str = "",
        routing_status: str = "routed",
    ) -> Dict[str, Any]:
        """
        Traite une chaîne d'emails à partir d'un message Gmail.

        Étapes:
        1. Télécharge le .eml brut via Gmail API (format=raw)
        2. Parse le .eml pour extraire tous les emails de la chaîne
        3. Stocke chaque email dans la base
        4. Lie tous les emails au même thread Gmail

        Args:
            gmail_client: Client Gmail connecté
            gmail_message_id: ID du message Gmail
            gmail_thread_id: ID du thread Gmail
            account_id: ID du compte email
            org_id: ID de l'organisation
            company_id: ID de l'entreprise (optionnel)
            delivered_to: Adresse de livraison
            routing_status: Statut du routage

        Returns:
            {stored: bool, email_ids: list[str], chain_length: int}
        """
        logger.info(f"📥 Traitement chaîne {gmail_message_id} (thread: {gmail_thread_id})")

        # 1. Télécharger le .eml brut
        raw_eml = await self._download_raw_eml(gmail_client, gmail_message_id)
        if not raw_eml:
            logger.error(f"❌ Impossible de télécharger le .eml pour {gmail_message_id}")
            return {"stored": False, "email_ids": [], "chain_length": 0}

        # 2. Parser le .eml
        from app.services.emails.eml_parser import parse_email_chain

        chain_emails = parse_email_chain(raw_eml)
        if not chain_emails:
            logger.warning(f"⚠️ Aucun email extrait du .eml {gmail_message_id}")
            return {"stored": False, "email_ids": [], "chain_length": 0}

        logger.info(f"🔗 {len(chain_emails)} emails extraits du .eml")

        # 3. Stocker chaque email
        from app.services.email_database_service import email_db

        email_ids = []
        for idx, email_data in enumerate(chain_emails):
            email_id = await self._store_chain_email(
                email_db=email_db,
                email_data=email_data,
                gmail_message_id=gmail_message_id,
                gmail_thread_id=gmail_thread_id,
                account_id=account_id,
                org_id=org_id,
                company_id=company_id,
                delivered_to=delivered_to,
                routing_status=routing_status,
                chain_index=idx,
                chain_total=len(chain_emails),
            )
            if email_id:
                email_ids.append(email_id)

        # 4. Mettre à jour les métriques du thread
        if gmail_thread_id and email_ids:
            try:
                await self._update_thread_metrics(
                    org_id=org_id,
                    company_id=company_id,
                    gmail_thread_id=gmail_thread_id,
                    subject=chain_emails[0].get("subject", ""),
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur mise à jour thread: {e}", exc_info=True)

        logger.info(f"✅ Chaîne traitée: {len(email_ids)}/{len(chain_emails)} emails stockés")
        
        # Nettoyer le fichier .eml temporaire
        if hasattr(self, '_tmp_eml_path') and self._tmp_eml_path:
            try:
                import os
                if os.path.exists(self._tmp_eml_path):
                    os.remove(self._tmp_eml_path)
                    logger.debug(f"🧹 .eml supprimé: {self._tmp_eml_path}")
            except Exception as e:
                logger.warning(f"⚠️ Erreur nettoyage .eml: {e}")
            self._tmp_eml_path = None
        
        return {
            "stored": len(email_ids) > 0,
            "email_ids": email_ids,
            "chain_length": len(chain_emails),
        }

    async def _download_raw_eml(self, gmail_client, message_id: str) -> Optional[bytes]:
        """Télécharge le .eml brut via IMAP."""
        try:
            eml_bytes = await gmail_client.download_raw_email(message_id)

            if not eml_bytes:
                logger.warning(f"⚠️ Pas de données raw pour {message_id}")
                return None

            logger.info(f"📄 .eml téléchargé: {len(eml_bytes)} bytes")

            # Sauvegarder dans /tmp pour debug (supprimé après parsing)
            tmp_path = f"/tmp/{message_id}.eml"
            with open(tmp_path, "wb") as f:
                f.write(eml_bytes)
            logger.debug(f"💾 .eml sauvegardé: {tmp_path}")
            
            # Nettoyer le fichier temporaire après usage
            self._tmp_eml_path = tmp_path

            return eml_bytes

        except Exception as e:
            logger.error(f"❌ Erreur téléchargement .eml {message_id}: {e}")
            return None

    async def _store_chain_email(
        self,
        email_db,
        email_data: Dict[str, Any],
        gmail_message_id: str,
        gmail_thread_id: str,
        account_id: str,
        org_id: str,
        company_id: Optional[str],
        delivered_to: str,
        routing_status: str,
        chain_index: int,
        chain_total: int,
    ) -> Optional[str]:
        """Stocke un email extrait de la chaîne dans la base."""
        try:
            # Générer un message_id unique pour cet email de la chaîne
            chain_email_id = f"{gmail_message_id}_chain_{chain_index}"

            # Vérifier si déjà stocké (gestion doublons)
            existing = await email_db.get_email_by_message_id(chain_email_id)
            if existing:
                logger.debug(f"Email chaîne {chain_email_id} déjà existant")
                return existing["id"]

            # Calculer un hash de dédup (from + date + subject + message_id)
            # pour éviter les doublons cross-sessions Gmail (ex: même forward
            # reçu dans un nouveau poll ou une nouvelle semaine)
            dedup_raw = email_data.get("from_email", "") or ""
            dedup_raw += "|" + (email_data.get("date", "") or "")
            dedup_raw += "|" + (email_data.get("subject", "") or "")
            dedup_raw += "|" + (email_data.get("message_id", "") or "")
            dedup_hash = hashlib.sha256(dedup_raw.encode()).hexdigest()

            existing_by_hash = await email_db.get_email_by_dedup_hash(dedup_hash, org_id)
            if existing_by_hash:
                logger.info(f"📦 Email chaîne dédoublonné par hash (même contenu): {dedup_hash[:12]}...")
                return existing_by_hash["id"]

            now = datetime.utcnow().isoformat()
            body_text = email_data.get("body_text", "") or ""
            body_html = email_data.get("body_html", "") or ""

            from app.services.emails.eml_parser import _parse_date

            raw_date = email_data.get("date") or ""
            parsed_date = _parse_date(raw_date)
            sent_at = parsed_date if parsed_date and "T" in parsed_date else now

            record = {
                "org_id": org_id,
                "company_id": company_id or org_id,
                "email_account_id": account_id,
                "delivered_to_alias": delivered_to,
                "routing_status": routing_status,
                "gmail_thread_id": gmail_thread_id,
                "gmail_message_id": chain_email_id,
                "sender_email": email_data.get("from_email", ""),
                "sender_name": email_data.get("from_name"),
                "recipient_emails": email_data.get("to_emails", []),
                "cc_emails": email_data.get("cc_emails", []),
                "subject": email_data.get("subject", ""),
                "subject_cleaned": email_data.get("subject", ""),
                "content_text": body_text,
                "content_text_raw": body_text,
                "content_html": body_html or body_text,
                "sent_at": sent_at,
                "received_at": now,
                "in_reply_to": email_data.get("in_reply_to"),
                "references": email_data.get("references"),
                "headers": {},
                "has_attachments": False,
                "attachments_count": 0,
                "total_size_bytes": 0,
                "processing_status": "pending",
                "dedup_hash": dedup_hash,
            }

            # Nettoyer les champs None
            record = {k: v for k, v in record.items() if v is not None}

            result = await email_db.create_email(record)
            email_id = result["id"] if isinstance(result, dict) else result
            logger.debug(f"✅ Email chaîne [{chain_index}/{chain_total}] stocké: {email_id}")

            # Lancer la vectorisation async
            try:
                from app.services.emails.embedding_service import embedding_service

                asyncio.create_task(embedding_service.vectorize_email_async(email_id))
            except Exception as e:
                logger.warning(f"⚠️ Erreur vectorisation: {e}")

            return email_id

        except Exception as e:
            logger.error(f"❌ Erreur stockage email chaîne [{chain_index}]: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def _update_thread_metrics(
        self,
        org_id: str,
        company_id: Optional[str],
        gmail_thread_id: str,
        subject: str,
    ):
        """Met à jour les métriques du thread."""
        from app.services.email_thread_service import thread_service

        thread = thread_service.get_or_create_thread(
            org_id=UUID(org_id) if isinstance(org_id, str) else org_id,
            company_id=UUID(company_id) if isinstance(company_id, str) and company_id else None,
            gmail_thread_id=gmail_thread_id,
            subject=subject,
        )

        thread_service.update_thread_metrics(UUID(thread["id"]))
        logger.debug(f"📊 Métriques thread mises à jour: {thread['id']}")


# Instance singleton
email_chain_service = EmailChainService()
