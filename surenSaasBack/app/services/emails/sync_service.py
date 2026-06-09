"""
Service de synchronisation des emails.

Orchestre le polling Gmail, le routing, l'extraction et la vectorisation.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

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
        max_emails: int = 10
    ) -> Dict[str, Any]:
        """
        Synchronise les emails d'un compte Gmail par lots de 10.

        Args:
            account_id: UUID du compte email
            sync_mode: "incremental" ou "historical"
            date_range: {start_date, end_date} si mode historical
            max_emails: Nombre max d'emails à traiter par lot (défaut: 10)

        Returns:
            Statistiques de synchro + flag has_more pour pagination
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
            "duration_seconds": 0,
            "has_more": False,
            "total_remaining": 0,
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
            await gmail_client.connect()
            
            # 3. Récupérer les messages (lot de max_emails, scan des derniers jours)
            if sync_mode == "historical" and date_range:
                from datetime import datetime as dt
                start = dt.strptime(date_range["start_date"], "%Y-%m-%d")
                end = dt.strptime(date_range["end_date"], "%Y-%m-%d")
                messages = await gmail_client.list_messages_by_date_range(start, end, max_emails)
            else:
                messages = await gmail_client.list_messages(
                    since_uid=last_sync_uid if last_sync_uid > 0 else None,
                    max_results=max_emails,
                    max_days=1,
                )
            
            # Extraire les métadonnées de pagination
            has_more = False
            total_remaining = 0
            batch_newest_uid = 0
            if messages:
                batch_info = messages[0].get("_batch_info", {})
                has_more = batch_info.get("has_more", False)
                total_remaining = batch_info.get("total_remaining", 0)
                batch_newest_uid = batch_info.get("newest_uid", 0)
                # Nettoyer les métadonnées des messages avant traitement
                for m in messages:
                    m.pop("_has_more", None)
                    m.pop("_total_remaining", None)
                    m.pop("_batch_info", None)
            
            logger.info(f"Found {len(messages)} messages to process (has_more={has_more}, remaining={total_remaining})")
            
            # 4. Traiter chaque message
            max_uid_in_batch = 0
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
                    else:
                        stats["ignored"] += 1
                        reason = result.get("ignore_reason", "unknown")
                        if reason in stats["ignored_breakdown"]:
                            stats["ignored_breakdown"][reason] += 1
                    
                    # Suivre le plus grand UID traité dans ce lot
                    uid_val = int(msg.get("id", 0))
                    if uid_val > max_uid_in_batch:
                        max_uid_in_batch = uid_val
                        
                except Exception as e:
                    logger.error(f"Error processing message {msg.get('id')}: {e}")
                    stats["errors"] += 1
            
            # 5. Mettre à jour le compte : ne sauvegarder QUE si on a traité des messages
            #    last_sync_uid = le plus grand UID de ce lot
            #    Si has_more est True, le prochain cron reprendra à cet UID
            new_last_uid = max(stats.get("last_uid", 0), max_uid_in_batch)
            if new_last_uid > 0:
                stats["last_uid"] = new_last_uid
                await email_db.update_email_account(account_id, {
                    "last_sync_uid": new_last_uid,
                    "last_sync_at": datetime.utcnow().isoformat()
                })
            
            stats["has_more"] = has_more
            stats["total_remaining"] = total_remaining
            
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
        
        # Log pour debug
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.debug(f"Processing message {message_id}, Delivered-To: {delivered_to}")
        logger.debug(f"All headers: {list(headers.keys())}")
        
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
            # Si l'email existe et est en erreur, on le retraite (repasse en pending)
            if existing.get("processing_status") == "error":
                logger.info(f"Message {message_id} en error, re-traitement...")
                # Repasser en pending pour forcer la re-vectorisation
                await email_db.update_email_status(existing["id"], "pending")
                # Lancer la vectorisation directement
                from app.services.emails.embedding_service import embedding_service
                asyncio.create_task(embedding_service.vectorize_email_async(existing["id"]))
                return {"stored": True, "email_id": existing["id"], "retried": True}
            
            logger.info(f"Message {message_id} already exists, skipping")
            return {"stored": True, "email_id": existing["id"]}
        
        # 5. Extraire le contenu
        raw_body = gmail_client.get_body_text(message)
        raw_subject = headers.get("Subject", "")
        
        logger.info(f"🔧 Extraction email - Sujet: {raw_subject[:50]}...")
        logger.info(f"🔧 Taille du corps: {len(raw_body)} caractères")
        
        # Debug: vérifier si c'est un forward
        from app.services.emails.content_cleaner import ContentCleaner
        cleaner = ContentCleaner()
        is_forward = cleaner.detect_forward(raw_body)
        logger.info(f"🔧 Détecté comme forward: {is_forward}")
        
        # Détecter si c'est une chaîne de forwards (plusieurs "De :" ou "From :")
        is_chain = False
        de_count = raw_body.count("De :") + raw_body.count("From :")
        if de_count > 1:
            is_chain = True
            logger.info(f"🔗 Détecté comme CHAÎNE de forwards: {de_count} blocs 'De :'/'From :'")
        
        # Debug: chercher des patterns spécifiques
        if "TR:" in raw_subject.upper():
            logger.info(f"🔧 Sujet contient 'TR:' (Transmis)")
        
        # Si c'est une chaîne, utiliser le parsing .eml
        if is_chain:
            logger.info(f"🔗 Utilisation du parsing .eml pour la chaîne {message_id}")
            from app.services.emails.email_chain_service import email_chain_service

            return await email_chain_service.process_chain(
                gmail_client=gmail_client,
                gmail_message_id=message_id,
                gmail_thread_id=message.get("threadId"),
                account_id=account_id,
                org_id=str(routing.org_id),
                company_id=str(routing.company_id) if routing.company_id else None,
                delivered_to=delivered_to,
                routing_status=routing.routing_status,
            )
        
        # Extraction du forward + nettoyage avec content_cleaner (regex)
        logger.info(f"🔧 Extraction avec content_cleaner (regex) pour message {message_id}")
        extracted = content_cleaner.extract_original(raw_body, raw_subject)
        
        logger.info(f"🔧 FIN extraction - Sujet extrait: {extracted.subject[:50]}...")
        logger.info(f"🔧 From: {extracted.from_email}, To: {extracted.to_emails}")
        
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
        
        # Types de fichiers à ignorer (images, Excel, etc.)
        IGNORE_EXTENSIONS = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',  # Images
            '.xlsx', '.xls', '.xlsm', '.xlsb', '.csv',  # Excel/CSV
            '.zip', '.rar', '.7z', '.tar', '.gz',  # Archives
            '.exe', '.dll', '.msi',  # Exécutables
            '.mp3', '.mp4', '.avi', '.mov', '.wav',  # Médias
        }
        
        # Types de fichiers à traiter (PDF, Word, etc.)
        PROCESS_EXTENSIONS = {
            '.pdf',  # PDF
            '.doc', '.docx', '.odt',  # Word
            '.txt', '.rtf',  # Texte
            '.ppt', '.pptx', '.odp',  # PowerPoint
        }
        
        for att in attachments:
            filename = att.get("filename", "").lower()
            file_extension = f".{filename.split('.')[-1]}" if '.' in filename else ''
            
            # Vérifier si on doit ignorer ce fichier
            if file_extension in IGNORE_EXTENSIONS:
                logger.info(f"⚠️  Fichier ignoré (type non supporté): {filename}")
                continue
                
            # Vérifier si on doit traiter ce fichier
            if file_extension not in PROCESS_EXTENSIONS:
                logger.info(f"⚠️  Fichier ignoré (type inconnu): {filename}")
                continue
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
            
            # Créer un thread minimal même en cas d'erreur
            try:
                from app.services.email_thread_service import thread_service
                thread_service.get_or_create_thread(
                    gmail_thread_id=message.get("threadId"),
                    org_id=routing.org_id,
                    company_id=routing.company_id,
                    subject=email_data.get("subject", "Sans sujet"),
                    participant_emails=[email_data.get("sender_email", "")],
                    first_email_at=email_data.get("sent_at"),
                    last_email_at=email_data.get("sent_at")
                )
                logger.info(f"✅ Thread minimal créé après erreur de reconstruction")
            except Exception as thread_error:
                logger.error(f"❌ Échec création thread minimal: {thread_error}")
        
        # 9. Lancer la vectorisation async (après reconstruction)
        asyncio.create_task(embedding_service.vectorize_email_async(email_id))
        
        # 10. Brancher le pipeline Hermès (ChantierRouter + HermesExtractor)
        asyncio.create_task(
            _run_hermes_pipeline(
                email_id=email_id,
                org_id=str(routing.org_id),
                subject=extracted.subject,
                body=extracted.body_cleaned or "",
                sender_email=extracted.from_email or "",
            )
        )
        
        logger.info(f"Message {message_id} processed successfully, email_id: {email_id}")
        
        return {
            "stored": True,
            "email_id": email_id
        }
    
    async def _process_email_chain(
        self,
        gmail_client,
        gmail_message: Dict[str, Any],
        account_id: str,
        org_id: str
    ) -> Dict[str, Any]:
        """
        Traite une chaîne d'emails via le parsing .eml.
        Délègue à EmailChainService.
        """
        from app.services.emails.email_chain_service import email_chain_service

        message = gmail_message
        if isinstance(gmail_message, dict) and "id" in gmail_message:
            message_id = gmail_message["id"]
        else:
            message_id = gmail_message

        headers = gmail_client.parse_headers(message) if isinstance(message, dict) else {}
        delivered_to = headers.get("Delivered-To", "")

        routing = await alias_router.route(delivered_to)
        if routing.routing_status != "routed":
            return {"stored": False, "ignore_reason": routing.routing_status.replace("ignored_", ""), "email_ids": [], "chain_length": 0}

        thread_id = message.get("threadId") if isinstance(message, dict) else None

        return await email_chain_service.process_chain(
            gmail_client=gmail_client,
            gmail_message_id=message_id,
            gmail_thread_id=thread_id or message_id,
            account_id=account_id,
            org_id=str(routing.org_id),
            company_id=str(routing.company_id) if routing.company_id else None,
            delivered_to=delivered_to,
            routing_status=routing.routing_status,
        )


async def _run_hermes_pipeline(
    email_id: str,
    org_id: str,
    subject: str,
    body: str,
    sender_email: str,
):
    """
    Pipeline Hermès asynchrone déclenché après le stockage de l'email.
    
    1. ChantierRouter → identifie le chantier
    2. Met à jour email_threads avec chantier_id et métadonnées Hermès
    3. HermesExtractor → extrait tâches/dépenses/notifications et dispatche
    """
    try:
        from app.core.logging import get_logger
        from app.services.emails.chantier_router import chantier_router
        from app.services.emails.hermes_extractor import hermes_extractor
        from app.api.auth import get_supabase
    except ImportError as e:
        logger.error(f"Erreur d'importation dans _run_hermes_pipeline: {e}")
        return

    _logger = get_logger("hermes_pipeline")

    try:
        await asyncio.sleep(3)

        routing_result = await chantier_router.route(
            org_id=org_id, subject=subject, body=body, sender_email=sender_email,
        )

        chantier_id = routing_result.chantier_id

        try:
            sb = get_supabase()
            email_resp = sb.table("emails")\
                .select("gmail_thread_id")\
                .eq("id", email_id)\
                .maybe_single()\
                .execute()

            if email_resp and email_resp.data:
                gmail_thread_id = email_resp.data.get("gmail_thread_id")
                if gmail_thread_id:
                    update_data = {
                        "hermes_processed_at": datetime.utcnow().isoformat(),
                        "hermes_confidence": routing_result.confidence,
                    }
                    if chantier_id:
                        update_data["chantier_id"] = chantier_id
                    else:
                        update_data["hermes_ignore_reason"] = routing_result.reason
                        update_data["chantier_id"] = None

                    sb.table("email_threads")\
                        .update(update_data)\
                        .eq("gmail_thread_id", gmail_thread_id)\
                        .eq("org_id", org_id)\
                        .execute()
        except Exception as e:
            _logger.warning(f"[Hermès Pipeline] Erreur MAJ thread: {e}")

        if chantier_id:
            _logger.info(f"[Hermès] Email {email_id} → chantier {chantier_id} (méthode: {routing_result.method})")
            result = await hermes_extractor.extract_and_dispatch(
                email_id=email_id, chantier_id=chantier_id, org_id=org_id,
            )
            _logger.info(f"[Hermès] Dispatch terminé: {result}")
        else:
            _logger.info(f"[Hermès] Email {email_id} non rattaché — ignoré ({routing_result.reason})")

    except Exception as e:
        _logger.error(f"[Hermès Pipeline] Erreur générale: {e}", exc_info=True)


# Instance singleton
sync_service = SyncService()
