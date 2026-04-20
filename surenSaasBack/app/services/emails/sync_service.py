"""
Service de synchronisation des emails.

Orchestre le polling Gmail, le routing, l'extraction et la vectorisation.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.email_database_service import email_db
from app.agents.generic_extractor import create_invoice_extractor

logger = get_logger(__name__)
from app.services.emails.gmail_client import create_gmail_client
from app.services.emails.alias_router import alias_router
from app.services.emails.content_cleaner import content_cleaner
from app.services.emails.embedding_service import embedding_service
from app.services.file_storage_service import FileStorageService


class SyncService:
    """Service de synchronisation des emails Gmail."""
    
    def __init__(self):
        self.file_storage = FileStorageService()
    
    async def sync_account(
        self,
        account_id: str,
        sync_mode: str = "incremental",
        date_range: Optional[Dict[str, str]] = None,
        max_emails: int = 1000
    ) -> Dict[str, Any]:
        """
        Synchronise les emails d'un compte Gmail.
        
        Args:
            account_id: UUID du compte email
            sync_mode: "incremental" ou "historical"
            date_range: {start_date, end_date} si mode historical
            max_emails: Limite de sécurité
            
        Returns:
            Statistiques de synchro
        """
        stats = {
            "account_id": account_id,
            "synced": 0,
            "ignored": 0,
            "ignored_breakdown": {
                "no_alias": 0,
                "org_mismatch": 0,
                "company_not_found": 0,
                "invalid_format": 0
            },
            "vectorized": 0,
            "errors": 0,
            "last_uid": 0,
            "duration_seconds": 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # 1. Récupérer les infos du compte
            account = await email_db.get_email_account(account_id)
            
            if not account:
                raise ValueError(f"Account {account_id} not found")
            refresh_token = account["oauth_refresh_token"]
            last_sync_uid = account.get("last_sync_uid", 0)
            
            # 2. Connecter le client Gmail
            gmail_client = create_gmail_client(refresh_token)
            
            # 3. Récupérer les messages
            if sync_mode == "historical" and date_range:
                from datetime import datetime as dt
                start = dt.strptime(date_range["start_date"], "%Y-%m-%d")
                end = dt.strptime(date_range["end_date"], "%Y-%m-%d")
                messages = await gmail_client.list_messages_by_date_range(start, end, max_emails)
            else:
                messages = await gmail_client.list_messages(since_uid=last_sync_uid if last_sync_uid > 0 else None)
            
            logger.info(f"Found {len(messages)} messages to process")
            
            # 4. Traiter chaque message
            for msg in messages:
                try:
                    result = await self._process_message(
                        gmail_client=gmail_client,
                        gmail_message=msg,
                        account_id=account_id,
                        org_id=account["org_id"]
                    )
                    
                    if result["stored"]:
                        stats["synced"] += 1
                        stats["last_uid"] = max(stats["last_uid"], int(msg.get("historyId", 0)))
                    else:
                        stats["ignored"] += 1
                        reason = result.get("ignore_reason", "unknown")
                        if reason in stats["ignored_breakdown"]:
                            stats["ignored_breakdown"][reason] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing message {msg.get('id')}: {e}")
                    stats["errors"] += 1
            
            # 5. Mettre à jour le compte
            await email_db.update_email_account(account_id, {
                "last_sync_uid": stats["last_uid"],
                "last_sync_at": datetime.utcnow().isoformat()
            })
            
            # Calculer la durée
            duration = (datetime.utcnow() - start_time).total_seconds()
            stats["duration_seconds"] = int(duration)
            
            logger.info(f"Sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise
    
    async def _process_message(
        self,
        gmail_client,
        gmail_message: Dict[str, Any],
        account_id: str,
        org_id: str
    ) -> Dict[str, Any]:
        """
        Traite un message Gmail individuel.
        
        Returns:
            {stored: bool, ignore_reason: str, email_id: str}
        """
        message_id = gmail_message["id"]
        
        # 1. Récupérer le message complet
        message = await gmail_client.get_message(message_id)
        
        # 2. Extraire les headers
        headers = gmail_client.parse_headers(message)
        delivered_to = headers.get("Delivered-To", "")
        
        # 3. Routing par alias
        routing = await alias_router.route(delivered_to)
        
        if routing.routing_status != "routed":
            logger.info(f"Message {message_id} ignored: {routing.routing_status}")
            return {
                "stored": False,
                "ignore_reason": routing.routing_status.replace("ignored_", "")
            }
        
        # 4. Vérifier si l'email existe déjà
        existing = await email_db.get_email_by_message_id(message_id)
        
        if existing:
            logger.info(f"Message {message_id} already exists, skipping")
            return {"stored": True, "email_id": existing["id"]}
        
        # 5. Extraire le contenu
        raw_body = gmail_client.get_body_text(message)
        raw_subject = headers.get("Subject", "")
        
        # Extraction du forward + nettoyage
        extracted = content_cleaner.extract_original(raw_body, raw_subject)
        
        # 6. Stocker l'email
        email_data = {
            "org_id": str(routing.org_id),
            "company_id": str(routing.company_id),
            "email_account_id": account_id,
            "delivered_to_alias": delivered_to,
            "routing_status": routing.routing_status,
            "gmail_thread_id": message.get("threadId"),
            "gmail_message_id": message_id,
            "gmail_history_id": int(message.get("historyId", 0)),
            "subject": extracted.subject,
            "subject_cleaned": extracted.subject,
            "sender_email": extracted.from_email or headers.get("From", ""),
            "sender_name": extracted.from_name,
            "recipient_emails": extracted.to_emails or [delivered_to],
            "sent_at": extracted.date or headers.get("Date"),
            "received_at": datetime.utcnow().isoformat(),
            "content_text": extracted.body_cleaned,
            "content_text_raw": extracted.body,
            "content_html": gmail_client.get_body_text(message),  # Ou extraire HTML si présent
            "content_cleaned_at": datetime.utcnow().isoformat(),
            "processing_status": "pending",  # Sera mis à jour après vectorisation
            "in_reply_to": extracted.in_reply_to or headers.get("In-Reply-To"),
            "references": extracted.references or ([headers["References"]] if "References" in headers else None),
            "has_attachments": False,
            "attachments_count": 0,
            "total_size_bytes": int(message.get("sizeEstimate", 0)),
            "headers": headers
        }
        
        email = await email_db.create_email(email_data)
        email_id = email["id"]
        
        # 7. Traiter les pièces jointes
        attachments = gmail_client.get_attachments(message)
        
        for att in attachments:
            try:
                # Télécharger
                content = await gmail_client.download_attachment(message_id, att["attachmentId"])
                
                # Stocker sur R2
                storage_path = await self.file_storage.store_file(
                    file_data=content,
                    filename=att["filename"],
                    org_id=str(routing.org_id),
                    folder="emails"
                )
                
                # OCR via GenericDocumentExtractor existant
                try:
                    # Vérifier si c'est un fichier ZIP
                    if att["filename"].lower().endswith('.zip'):
                        logger.info(f"⚠️  Fichier ZIP ignoré pour OCR: {att['filename']}")
                        ocr_text = None
                        ocr_confidence = None
                    else:
                        extractor = create_invoice_extractor()
                        # Sauvegarder temporairement le fichier pour l'extraction
                        temp_path = f"/tmp/{att['filename']}"
                        with open(temp_path, 'wb') as f:
                            f.write(content)
                        
                        # Extraire le texte
                        result = await extractor.extract(temp_path)
                        
                    # Extraire le texte et la confiance depuis le résultat
                    if result:
                        ocr_text = result.get_extracted_text()
                        ocr_confidence = result.get_confidence()
                    else:
                        ocr_text = None
                        ocr_confidence = None
                    
                    # Nettoyer le fichier temporaire
                    import os
                    os.remove(temp_path)
                except Exception as ocr_error:
                    logger.warning(f"OCR failed for {att['filename']}: {ocr_error}")
                    ocr_text = None
                    ocr_confidence = None
                
                # Insérer
                await email_db.create_attachment({
                    "org_id": str(routing.org_id),
                    "company_id": str(routing.company_id),
                    "email_id": email_id,
                    "filename": att["filename"],
                    "filename_clean": att["filename"],
                    "mime_type": att["mimeType"],
                    "file_size_bytes": att["size"],
                    "storage_path": storage_path,
                    "is_processed": ocr_text is not None,
                    "ocr_text": ocr_text,
                    "ocr_confidence": ocr_confidence
                })
                
                email_data["has_attachments"] = True
                email_data["attachments_count"] += 1
                
            except Exception as e:
                logger.error(f"Error processing attachment {att['filename']}: {e}")
        
        # Mettre à jour les infos d'attachments
        if email_data["has_attachments"]:
            await email_db.update_email(email_id, {
                "has_attachments": True,
                "attachments_count": email_data["attachments_count"]
            })
        
        # 8. Reconstruction du thread historique si nécessaire
        try:
            from app.services.thread_reconstruction_service import thread_reconstruction_service
            
            should_reconstruct, reason = thread_reconstruction_service.should_attempt_reconstruction(
                gmail_thread_id=message.get("threadId"),
                org_id=routing.org_id
            )
            
            if should_reconstruct:
                logger.info(f"🔍 Reconstruction thread nécessaire: {reason}")
                success, thread_data, status = await thread_reconstruction_service.reconstruct_thread(
                    gmail_thread_id=message.get("threadId"),
                    org_id=routing.org_id,
                    company_id=routing.company_id,
                    current_email_id=email_id
                )
                
                if success:
                    logger.info(f"✅ Thread reconstruit avec statut: {status}")
                else:
                    logger.warning("⚠️ Échec reconstruction thread, poursuite avec email unique")
            else:
                logger.debug(f"ℹ️ Pas de reconstruction nécessaire: {reason}")
                
        except Exception as recon_error:
            logger.warning(f"⚠️ Erreur reconstruction thread (non bloquant): {recon_error}")
        
        # 9. Lancer la vectorisation async (après reconstruction)
        asyncio.create_task(embedding_service.vectorize_email_async(email_id))
        
        logger.info(f"Message {message_id} processed successfully, email_id: {email_id}")
        
        return {
            "stored": True,
            "email_id": email_id
        }


# Instance singleton
sync_service = SyncService()
