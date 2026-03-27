"""Bot Construction - Handlers pour factures et upload."""
from typing import Dict, Any, Optional
import os
import tempfile
from pathlib import Path
from datetime import datetime
import logging
import httpx

from app.api.auth import get_supabase
from app.services.telegram.upload_invoice.service import InvoiceUploadService
from app.services.telegram.notification_service import NotificationService
from app.services.telegram.audit_service import TelegramAuditService
from app.api.telegram_core import send_simple_message, get_bot_token, escape_markdown, send_message_safe

logger = logging.getLogger(__name__)


async def handle_construction_message(
    message: Dict[str, Any], 
    bot_config: Dict[str, Any], 
    supabase: Any,
    org_id: str
) -> Dict[str, Any]:
    """Traite un message pour le bot construction."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    logger.info(f"📩 Message construction reçu de {chat_id}: {text[:50] if text else '(no text)'}")
    
    if text and text.startswith('/start'):
        from app.api.bot_construction_commands import handle_start_command
        return await handle_start_command(message, bot_config, supabase, org_id)
    elif message.get('photo') or message.get('document'):
        return await handle_invoice_upload(message, bot_config, supabase, org_id)
    else:
        from app.api.bot_construction_commands import send_menu_message
        await send_menu_message(chat_id, bot_config)
        return {"ok": True}


async def handle_invoice_upload(
    message: Dict[str, Any],
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str
) -> Dict[str, Any]:
    """Gère l'upload d'une facture avec OCR Gemini."""
    chat_id = message.get('chat', {}).get('id')
    from_user = message.get('from', {})
    telegram_user_id = from_user.get('id')
    
    logger.info(f"📎 Upload de facture reçu de {chat_id}")
    
    await send_simple_message(chat_id, bot_config, "📄 *Facture reçue !*\n\nAnalyse en cours... ⏳")
    
    bot_token = get_bot_token(bot_config)
    if not bot_token:
        await send_simple_message(chat_id, bot_config, "❌ Erreur: Configuration du bot incomplète.")
        return {"ok": False, "error": "Bot token not found"}
    
    try:
        # Télécharger le fichier
        file_path = await _download_telegram_file(message, bot_token)
        if not file_path:
            await send_simple_message(chat_id, bot_config, "❌ Erreur lors du téléchargement du fichier.")
            return {"ok": False, "error": "File download failed"}
        
        logger.info(f"✅ Fichier téléchargé: {file_path}")
        
        file_type = _get_file_type(message)
        
        # Initialiser services
        audit_service = TelegramAuditService(supabase)
        notification_service = NotificationService(supabase, bot_token)
        
        # Créer log audit
        bot_id = bot_config.get('id')
        audit_log = await audit_service.create_log(
            bot_id=bot_id,
            telegram_user_id=telegram_user_id,
            interaction_type='file_received',
            payload={'chat_id': chat_id, 'file_type': file_type, 'file_path': file_path, 'workflow': 'invoice_upload'},
            org_id=org_id
        )
        audit_log_id = audit_log.get('id')
        
        # Service d'upload
        upload_service = InvoiceUploadService(
            supabase_client=supabase,
            audit_service=audit_service,
            notification_service=notification_service
        )
        
        # Récupérer entreprise construction
        company_result = supabase.table('companies') \
            .select('id') \
            .eq('org_id', org_id) \
            .eq('slug', 'construction') \
            .execute()
        
        if not company_result.data:
            logger.error(f"Entreprise construction non trouvée pour org {org_id}")
            await audit_service.log_error(audit_log_id, "Company not found", "configuration")
            await send_simple_message(chat_id, bot_config, "❌ Erreur: Configuration incomplète.")
            return {"ok": False, "error": "Company not found"}
        
        company_id = company_result.data[0]['id']
        
        # Démarrer workflow
        result = await upload_service.start_workflow(
            telegram_user_id=telegram_user_id,
            org_id=org_id,
            company_id=company_id,
            file_path=file_path,
            file_type=file_type,
            audit_log_id=audit_log_id
        )
        
        # Mettre à jour audit
        if result.success:
            await audit_service.complete_log(
                audit_log_id=audit_log_id,
                status='completed',
                result_data={'invoice_id': result.invoice_id}
            )
            await _send_extraction_result(chat_id, result, bot_config)
        else:
            await audit_service.complete_log(audit_log_id=audit_log_id, status='failed', error=result.message)
            await send_simple_message(chat_id, bot_config, f"❌ *Erreur*\n\n{result.message}")
        
        # Nettoyer fichier temporaire
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Fichier temporaire supprimé: {file_path}")
        except Exception as e:
            logger.warning(f"Impossible de supprimer fichier temporaire: {e}")
        
        return {"ok": result.success, "invoice_id": result.invoice_id}
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement facture: {e}", exc_info=True)
        await send_simple_message(chat_id, bot_config, "❌ Une erreur s'est produite.")
        return {"ok": False, "error": str(e)}


async def _download_telegram_file(message: Dict[str, Any], bot_token: str) -> Optional[str]:
    """Télécharge un fichier depuis Telegram vers /tmp."""
    try:
        file_id = None
        file_name = None
        
        if message.get('document'):
            document = message['document']
            file_id = document.get('file_id')
            file_name = document.get('file_name', f"doc_{file_id}")
        elif message.get('photo'):
            photos = message['photo']
            largest = photos[-1] if photos else None
            if largest:
                file_id = largest.get('file_id')
                file_name = f"photo_{file_id}.jpg"
        
        if not file_id:
            return None
        
        async with httpx.AsyncClient() as client:
            # Étape 1: getFile
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/getFile",
                json={"file_id": file_id},
                timeout=30.0
            )
            result = resp.json()
            
            if not result.get('ok'):
                logger.error(f"Erreur getFile: {result}")
                return None
            
            file_path_tg = result['result']['file_path']
            
            # Étape 2: Télécharger
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path_tg}"
            
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=Path(file_name).suffix if file_name else '.tmp',
                dir='/tmp'
            )
            temp_path = temp_file.name
            
            async with httpx.AsyncClient() as dl_client:
                dl_resp = await dl_client.get(download_url, timeout=60.0)
                dl_resp.raise_for_status()
                temp_file.write(dl_resp.content)
                temp_file.close()
                
                logger.info(f"✅ Fichier téléchargé: {len(dl_resp.content)} bytes → {temp_path}")
                return temp_path
                
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement: {e}")
        return None


def _get_file_type(message: Dict[str, Any]) -> str:
    """Détermine le type de fichier."""
    if message.get('document'):
        mime = message['document'].get('mime_type', '')
        if mime == 'application/pdf':
            return 'pdf'
        elif mime.startswith('image/'):
            return 'image'
    elif message.get('photo'):
        return 'image'
    return 'unknown'


async def _send_extraction_result(chat_id: int, result: Any, bot_config: Dict[str, Any]):
    """Affiche les données extraites avec boutons."""
    extracted = result.extracted_data
    
    # Vérifier si c'est une extraction par défaut (fallback)
    is_fallback = extracted.raw_data.get('fallback', False) if extracted.raw_data else False
    
    # Log des données extraites pour debug
    logger.info(f"📝 Données extraites par OCR:")
    logger.info(f"   - Fournisseur: {extracted.supplier_name}")
    logger.info(f"   - N° Facture: {extracted.invoice_number}")
    logger.info(f"   - Date: {extracted.invoice_date}")
    logger.info(f"   - Montant HT: {extracted.amount_ht}")
    logger.info(f"   - Montant TTC: {extracted.amount_ttc}")
    logger.info(f"   - TVA: {extracted.vat_amount} ({extracted.vat_rate}%)")
    logger.info(f"   - Description: {extracted.description}")
    logger.info(f"   - Score confiance: {extracted.confidence_score}")
    logger.info(f"   - Fallback: {is_fallback}")
    
    # Échapper les caractères Markdown dans les données extraites
    supplier_name = escape_markdown(extracted.supplier_name or 'Non détecté')
    invoice_number = escape_markdown(extracted.invoice_number or 'Non détecté')
    invoice_date = escape_markdown(extracted.invoice_date or 'Non détectée')
    description = escape_markdown(extracted.description or '')
    
    # Adapter le message selon si c'est un fallback ou non
    if is_fallback:
        text = (
            f"⚠️ *Facture reçue mais OCR indisponible*\n\n"
            f"📋 *Détails à compléter :*\n"
            f"• *Fournisseur:* {supplier_name}\n"
            f"• *N° Facture:* {invoice_number}\n"
            f"• *Date:* {invoice_date}\n"
            f"• *Montant HT:* {extracted.amount_ht or 0:.2f}€\n"
            f"• *Montant TTC:* {extracted.amount_ttc or 0:.2f}€\n"
            f"• *TVA:* {extracted.vat_amount or 0:.2f}€ ({extracted.vat_rate or 0}%)\n\n"
            f"_⚠️ L'analyse automatique a échoué. Les informations doivent être complétées manuellement dans l'application web._"
        )
    else:
        text = (
            f"✅ *Facture analysée avec succès !*\n\n"
            f"📋 *Détails extraits :*\n"
            f"• *Fournisseur:* {supplier_name}\n"
            f"• *N° Facture:* {invoice_number}\n"
            f"• *Date:* {invoice_date}\n"
            f"• *Montant HT:* {extracted.amount_ht or 0:.2f}€\n"
            f"• *Montant TTC:* {extracted.amount_ttc or 0:.2f}€\n"
            f"• *TVA:* {extracted.vat_amount or 0:.2f}€ ({extracted.vat_rate or 0}%)\n\n"
            f"_Veuillez vérifier ces informations._"
        )
    
    # Log du message formaté
    logger.info(f"📄 Message formaté (longueur: {len(text)} caractères)")
    logger.debug(f"   Contenu: {text[:200]}...")
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Valider", "callback_data": f"invoice:validate:{result.invoice_id}"},
                {"text": "✏️ Modifier", "callback_data": f"invoice:edit:{result.invoice_id}"}
            ],
            [{"text": "❌ Annuler", "callback_data": f"invoice:cancel:{result.invoice_id}"}]
        ]
    }
    
    # Envoi avec fallback Markdown → HTML → Texte brut
    send_result = await send_message_safe(
        chat_id, 
        bot_config, 
        text, 
        keyboard,
        log_prefix=f"[Invoice {result.invoice_id}] "
    )
    
    if send_result['success']:
        logger.info(f"✅ Message envoyé avec mode: {send_result['mode']}")
    else:
        logger.error(f"❌ Échec de l'envoi: {send_result.get('error')}")


async def handle_invoice_validation(
    chat_id: int,
    invoice_id: str,
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str
) -> Dict[str, Any]:
    """Valide une facture (bouton Valider)."""
    try:
        supabase.table('invoices') \
            .update({'status': 'en_attente_validation', 'updated_at': datetime.utcnow().isoformat()}) \
            .eq('id', invoice_id) \
            .eq('org_id', org_id) \
            .execute()
        
        # Notifier gérants
        bot_token = get_bot_token(bot_config)
        notification_service = NotificationService(supabase, bot_token)
        
        invoice_result = supabase.table('invoices') \
            .select('supplier_name, amount_ttc') \
            .eq('id', invoice_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if invoice_result.data:
            data = invoice_result.data
            await notification_service.notify_invoice_pending(
                org_id=org_id,
                invoice_id=invoice_id,
                supplier_name=data.get('supplier_name', 'Fournisseur inconnu'),
                amount_ttc=data.get('amount_ttc')
            )
        
        await send_simple_message(
            chat_id, bot_config,
            "✅ *Facture validée !*\n\nVotre facture est soumise aux gérants pour validation."
        )
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Erreur validation: {e}")
        await send_simple_message(chat_id, bot_config, "❌ Erreur lors de la validation.")
        return {"ok": False}


async def handle_invoice_cancellation(
    chat_id: int,
    invoice_id: str,
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str
) -> Dict[str, Any]:
    """Annule une facture (bouton Annuler)."""
    try:
        supabase.table('invoices') \
            .delete() \
            .eq('id', invoice_id) \
            .eq('org_id', org_id) \
            .eq('status', 'brouillon') \
            .execute()
        
        await send_simple_message(chat_id, bot_config, "❌ *Facture annulée*\n\nLa facture a été supprimée.")
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Erreur annulation: {e}")
        await send_simple_message(chat_id, bot_config, "❌ Erreur lors de l'annulation.")
        return {"ok": False}
