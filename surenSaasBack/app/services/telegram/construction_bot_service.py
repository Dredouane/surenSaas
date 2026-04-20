"""
Service: Construction Bot

Gestion du bot Telegram dÃ©diÃ© Ã  la construction.
GÃ¨re:
- Lien d'invitation (/start avec payload)
- Upload de factures (photos/PDF)
- Validation des donnÃ©es extraites
- Notifications aux admins
"""

from typing import Dict, Any, Optional
import os
import httpx

from app.core.logging import get_logger
from app.services.telegram_invitation_service import telegram_invitation_service
from app.services.telegram.bots_registry import telegram_bots_registry
from app.services.file_storage_service import file_storage_service
from app.api.auth import get_supabase
from app.agents.construction_invoice_agent import ConstructionInvoiceAgent

logger = get_logger(__name__)


class ConstructionBotService:
    """Service principal du bot Telegram Construction."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "test").lower()
        self.bot_token = os.getenv(f"{self.environment.upper()}_TELEGRAM_CONSTRUCTION_BOT_TOKEN")
        
        # Récupérer la config du bot depuis le registry
        bot_config = telegram_bots_registry.get_bot('construction')
        self.bot_username = bot_config.username if bot_config else None
        self.telegram_api_url = "https://api.telegram.org"
        self.invitation_service = telegram_invitation_service
        self.ocr_agent = ConstructionInvoiceAgent()
    
    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une update webhook Telegram.
        
        Args:
            update: Update Telegram (message, callback_query, etc.)
            
        Returns:
            RÃ©sultat du traitement
        """
        logger.info(f"Update reÃ§ue: {update}")
        
        # Dispatcher selon le type d'update
        if 'message' in update:
            return await self._handle_message(update['message'])
        elif 'callback_query' in update:
            return await self._handle_callback_query(update['callback_query'])
        else:
            logger.info(f"Update type non supportÃ©: {update.keys()}")
            return {'status': 'ignored', 'reason': 'unsupported_update_type'}
    
    async def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Traite un message entrant."""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        # Commande /start avec payload d'invitation
        if text.startswith('/start'):
            return await self._handle_start_command(message)
        
        # Commande simple /start sans payload
        if text == '/start':
            await self._send_message(
                chat_id,
                "Bienvenue sur Suren Construction Bot!\n\n"
                "Envoyez une photo ou un PDF de facture pour la traiter."
            )
            return {'status': 'welcome_sent'}
        
        # RÃ©ception de fichier (photo ou document)
        if 'photo' in message or 'document' in message:
            return await self._handle_file_received(message)
        
        # Message texte simple
        await self._send_message(
            chat_id,
            "Envoyez une photo ou un PDF de facture pour la traiter.\n"
            "Utilisez /start pour commencer."
        )
        return {'status': 'help_sent'}
    
    async def _handle_start_command(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """GÃ¨re la commande /start avec payload d'invitation."""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        telegram_user = message['from']
        
        # Extraire le payload (format: /start XXX)
        parts = text.split(' ', 1)
        if len(parts) < 2:
            # Pas de payload, message de bienvenue standard
            await self._send_message(
                chat_id,
                "Bienvenue sur Suren Construction Bot!\n\n"
                "Pour lier votre compte, demandez une invitation Ã  votre administrateur."
            )
            return {'status': 'welcome_no_payload'}
        
        # VERSION SIMPLIFIÉE : Le paramètre est directement le user_id
        user_id = parts[1].strip()
        
        # Vérifier que c'est un UUID valide
        import re
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', user_id.lower()):
            await self._send_message(
                chat_id,
                "❌ Lien d'invitation invalide.\n\n"
                "Le format de l'identifiant est incorrect."
            )
            return {'status': 'invalid_user_id'}
        
        # Utiliser l'org_id du bot (déjà connu)
        org_id = self.org_id
        
        # Lier le compte Telegram Ã  l'utilisateur
        try:
            supabase = get_supabase()
            
            # VÃ©rifier si dÃ©jÃ  liÃ©
            existing = supabase.table('telegram_users') \
                .select('id') \
                .eq('id', user_id) \
                .eq('org_id', org_id) \
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Mettre Ã  jour les infos
                supabase.table('telegram_users') \
                    .update({
                        'telegram_id': telegram_user['id'],
                        'telegram_username': telegram_user.get('username'),
                        'telegram_first_name': telegram_user.get('first_name'),
                        'telegram_last_name': telegram_user.get('last_name'),
                        'is_verified': True,
                        'notification_enabled': True
                    }) \
                    .eq('id', user_id) \
                    .eq('org_id', org_id) \
                    .execute()
            else:
                # CrÃ©er le lien
                supabase.table('telegram_users').insert({
                    'user_id': user_id,
                    'org_id': org_id,
                    'telegram_id': telegram_user['id'],
                    'telegram_username': telegram_user.get('username'),
                    'telegram_first_name': telegram_user.get('first_name'),
                    'telegram_last_name': telegram_user.get('last_name'),
                    'is_verified': True,
                    'notification_enabled': True
                }).execute()
            
            await self._send_message(
                chat_id,
                f"âœ… Compte liÃ© avec succÃ¨s!\n\n"
                f"Bienvenue {telegram_user.get('first_name', '')}!\n\n"
                f"Vous pouvez maintenant envoyer des photos ou PDF de factures "
                f"pour les traiter automatiquement."
            )
            
            logger.info(f"Compte Telegram liÃ© pour user {user_id}")
            return {'status': 'account_linked', 'user_id': user_id}
            
        except Exception as e:
            logger.error(f"Erreur liaison compte Telegram: {e}")
            await self._send_message(
                chat_id,
                "â�¯ Erreur lors de la liaison du compte.\n"
                "Veuillez rÃ©essayer ou contacter votre administrateur."
            )
            return {'status': 'link_error', 'error': str(e)}
    
    async def _handle_file_received(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """GÃ¨re la rÃ©ception d'un fichier (photo ou PDF)."""
        chat_id = message['chat']['id']
        telegram_user = message['from']
        telegram_id = telegram_user['id']
        
        # VÃ©rifier que l'utilisateur est liÃ© Ã  un compte
        supabase = get_supabase()
        user_link = supabase.table('telegram_users') \
            .select('user_id, org_id') \
            .eq('telegram_id', telegram_id) \
            .eq('is_verified', True) \
            .single() \
            .execute()
        
        if not user_link.data:
            await self._send_message(
                chat_id,
                "âš ï¸� Votre compte Telegram n'est pas liÃ©.\n\n"
                "Demandez une invitation Ã  votre administrateur via l'application web."
            )
            return {'status': 'user_not_linked'}
        
        user_data = user_link.data
        user_id = user_data['user_id']
        org_id = user_data['org_id']
        
        # DÃ©terminer le type de fichier et rÃ©cupÃ©rer le file_id
        if 'photo' in message:
            # Prendre la plus grande photo
            photos = message['photo']
            file_id = photos[-1]['file_id']
            file_type = 'photo'
            file_name = f"photo_{message['message_id']}.jpg"
        elif 'document' in message:
            document = message['document']
            file_id = document['file_id']
            file_type = 'pdf' if document.get('mime_type') == 'application/pdf' else 'document'
            file_name = document.get('file_name', f"document_{message['message_id']}")
        else:
            await self._send_message(chat_id, "âš ï¸� Type de fichier non supportÃ©.")
            return {'status': 'unsupported_file_type'}
        
        # Envoyer un message de traitement
        processing_msg = await self._send_message(
            chat_id,
            "📄 Traitement de la facture en cours...\n\n"
            "⏳ Téléchargement du fichier..."
        )
        
        temp_file_path = None
        
        try:
            # Ã‰tape 1: TÃ©lÃ©charger le fichier depuis Telegram
            logger.info(f"â¬‡ï¸� TÃ©lÃ©chargement fichier Telegram: {file_id}")
            file_data, original_filename = await self._download_telegram_file(file_id)
            
            # Étape 2: Stocker temporairement
            await self._edit_message(
                chat_id,
                processing_msg['message_id'] if processing_msg else None,
                "📄 Traitement de la facture en cours...\n\n"
                "🖼️ Extraction des données avec IA..."
            )
            
            temp_file_path = await file_storage_service.store_file(
                file_data=file_data,
                filename=original_filename,
                org_id=org_id,
                folder="telegram"
            )
            
            # Ã‰tape 3: Appeler l'agent OCR avec le fichier local
            logger.info(f"ðŸ–¼ï¸� Extraction IA du fichier: {temp_file_path}")
            extracted_data = await self.ocr_agent.extract_from_document(temp_file_path, file_type)
            
            # Ã‰tape 4: Valider les donnÃ©es extraites
            validation = await self.ocr_agent.validate_extraction(extracted_data)
            if not validation['valid']:
                logger.warning(f"âš ï¸� DonnÃ©es extraites invalides: {validation['errors']}")
                # On continue quand mÃªme, l'utilisateur pourra corriger dans l'app web
            
            # Ã‰tape 5: CrÃ©er la facture en base de donnÃ©es
            logger.info(f"ðŸ’¾ CrÃ©ation facture en base de donnÃ©es")
            invoice_id = await self._create_invoice_from_extraction(
                extracted_data, user_id, org_id, temp_file_path
            )
            
            # Ã‰tape 6: Supprimer le fichier temporaire (on garde uniquement le chemin en DB)
            # Note: Le fichier sera nettoyÃ© automatiquement aprÃ¨s 24h par le service
            
            # Ã‰tape 7: PrÃ©senter les donnÃ©es Ã  l'utilisateur avec les vrais IDs
            message_text = (
                "📄 *Données extraites de la facture*\n\n"
                f"ðŸ�ª *Fournisseur:* {extracted_data.supplier_name or 'Non dÃ©tectÃ©'}\n"
                f"ðŸ“… *Date:* {extracted_data.invoice_date or 'Non dÃ©tectÃ©e'}\n"
                f"ðŸ“‹ *NumÃ©ro:* {extracted_data.invoice_number or 'Non dÃ©tectÃ©'}\n"
                f"ðŸ’° *Montant TTC:* {extracted_data.amount_ttc or 'Non dÃ©tectÃ©'}â‚¬\n"
                f"ðŸ“� *Description:* {extracted_data.description or 'Non dÃ©tectÃ©e'}\n\n"
                f"_Confiance: {extracted_data.confidence_score:.0%}_\n\n"
                "Les donnÃ©es sont correctes ?"
            )
            
            # Boutons inline avec vrai ID de facture
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "âœ… Valider", "callback_data": f"validate_invoice:{invoice_id}"},
                        {"text": "â�Œ Annuler", "callback_data": f"cancel_invoice:{invoice_id}"}
                    ]
                ]
            }
            
            await self._send_message(chat_id, message_text, reply_markup=keyboard)
            
            # Supprimer le message de traitement
            if processing_msg and 'message_id' in processing_msg:
                await self._delete_message(chat_id, processing_msg['message_id'])
            
            logger.info(f"âœ… Facture {invoice_id} prÃ©sentÃ©e Ã  l'utilisateur pour validation")
            return {'status': 'invoice_extracted', 'user_id': user_id, 'invoice_id': invoice_id}
            
        except Exception as e:
            logger.error(f"â�Œ Erreur traitement facture: {e}")
            
            # Nettoyer le fichier temporaire en cas d'erreur
            if temp_file_path:
                file_storage_service.delete_file(temp_file_path)
            
            await self._edit_message(
                chat_id,
                processing_msg['message_id'] if processing_msg else None,
                "â�¯ Erreur lors du traitement de la facture.\n"
                "Veuillez rÃ©essayer avec une image plus claire."
            )
            return {'status': 'extraction_error', 'error': str(e)}
    
    async def _notify_admins_new_invoice(self, invoice_id: str, sender_chat_id: int):
        """
        Envoie une notification aux admins quand une nouvelle facture est soumise.
        
        Args:
            invoice_id: ID de la facture
            sender_chat_id: Chat ID de l'expÃ©diteur (pour ne pas le notifier lui-mÃªme si admin)
        """
        try:
            supabase = get_supabase()
            
            # RÃ©cupÃ©rer la facture
            invoice_result = supabase.table('invoices') \
                .select('*, users:created_by(email, full_name), companies:company_id(name)') \
                .eq('id', invoice_id) \
                .single() \
                .execute()
            
            if not invoice_result.data:
                logger.warning(f"Facture {invoice_id} non trouvÃ©e pour notification")
                return
            
            invoice = invoice_result.data
            org_id = invoice['org_id']
            
            # Construire le message
            supplier = invoice.get('supplier_name', 'Fournisseur inconnu')
            amount = invoice.get('amount_ttc', 'N/A')
            creator = invoice.get('users', {}).get('full_name', 'Utilisateur')
            
            message_text = (
                "📄 *Nouvelle facture soumise*\n\n"
                f"🏢 *Fournisseur:* {supplier}\n"
                f"💰 *Montant:* {amount}€\n"
                f"👤 *Par:* {creator}\n\n"
                "Cliquez sur le bouton ci-dessous pour voir les détails."
            )
            
            # Bouton lien vers la page détail
            org_result = supabase.table('organizations') \
                .select('slug') \
                .eq('id', org_id) \
                .single() \
                .execute()
            
            org_slug = org_result.data.get('slug', org_id) if org_result.data else org_id
            
            # Récupérer l'URL frontend depuis les settings
            # Essayer FRONT_URL (par défaut dans .env.test) sinon FRONTEND_URL
            frontend_url = os.getenv("FRONT_URL") or os.getenv("FRONTEND_URL", "https://app.surensaas.com")
            invoice_url = f"{frontend_url}/{org_slug}/invoices/{invoice_id}"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📄 Voir la facture", "url": invoice_url}
                    ]
                ]
            }
            
            # RÃ©cupÃ©rer les admins avec Telegram liÃ©
            admins = supabase.table('users') \
                .select('user_id, telegram_users!inner(telegram_id)') \
                .eq('org_id', org_id) \
                .eq('role', 'admin') \
                .execute()
            
            if not admins.data:
                logger.info(f"Aucun admin avec Telegram trouvÃ© pour org {org_id}")
                return
            
            # Envoyer Ã  chaque admin
            sent_count = 0
            for admin in admins.data:
                telegram_id = admin.get('telegram_users', {}).get('telegram_id')
                
                if telegram_id and telegram_id != sender_chat_id:
                    try:
                        await self._send_message(
                            telegram_id,
                            message_text,
                            reply_markup=keyboard
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Erreur envoi notification Ã  admin {admin['user_id']}: {e}")
            
            logger.info(f"Notification envoyÃ©e Ã  {sent_count} admins pour facture {invoice_id}")
            
        except Exception as e:
            logger.error(f"Erreur notification admins: {e}")

    async def _handle_callback_query(self, callback_query: Dict[str, Any]) -> Dict[str, Any]:
        """GÃ¨re un clic sur bouton inline."""
        query_id = callback_query['id']
        chat_id = callback_query['message']['chat']['id']
        data = callback_query.get('data', '')
        
        # Accuser rÃ©ception du callback
        await self._answer_callback_query(query_id)
        
        if data.startswith('validate_invoice:'):
            invoice_id = data.split(':', 1)[1]
            
            # Mettre à jour le statut de la facture
            success = await self._update_invoice_status(invoice_id, 'en_attente_validation')
            
            if success:
                await self._send_message(
                    chat_id,
                    "✅ Facture validée!\n\n"
                    "Elle a été soumise pour validation par un administrateur."
                )
                
                # Notifier les admins
                await self._notify_admins_new_invoice(invoice_id, chat_id)
                
                return {'status': 'invoice_validated', 'invoice_id': invoice_id}
            else:
                await self._send_message(
                    chat_id,
                    "❌ Erreur lors de la validation. Veuillez réessayer."
                )
                return {'status': 'validation_error', 'invoice_id': invoice_id}
        
        elif data.startswith('cancel_invoice:'):
            invoice_id = data.split(':', 1)[1]
            
            # Supprimer la facture brouillon
            success = await self._delete_invoice(invoice_id)
            
            if success:
                await self._send_message(
                    chat_id,
                    "❌ Facture annulée.\n\n"
                    "Envoyez une nouvelle photo si nécessaire."
                )
                return {'status': 'invoice_cancelled', 'invoice_id': invoice_id}
            else:
                await self._send_message(
                    chat_id,
                    "❌ Erreur lors de l'annulation."
                )
                return {'status': 'cancellation_error', 'invoice_id': invoice_id}
        
        return {'status': 'callback_handled', 'data': data}
    
    # ==================== MÃ‰THODES MÃ‰TIERS ====================
    
    async def _download_telegram_file(self, file_id: str) -> tuple:
        """
        TÃ©lÃ©charge un fichier depuis Telegram.
        
        Args:
            file_id: ID du fichier Telegram
            
        Returns:
            tuple: (donnÃ©es binaires, nom de fichier)
        """
        try:
            # Ã‰tape 1: RÃ©cupÃ©rer le file_path
            get_file_url = f"{self.telegram_api_url}/bot{self.bot_token}/getFile"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(get_file_url, params={"file_id": file_id}, timeout=30.0)
                result = response.json()
                
                if not result.get('ok'):
                    raise Exception(f"Erreur getFile: {result}")
                
                file_path = result['result']['file_path']
                file_name = file_path.split('/')[-1]
            
            # Ã‰tape 2: TÃ©lÃ©charger le fichier
            download_url = f"{self.telegram_api_url}/file/bot{self.bot_token}/{file_path}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(download_url, timeout=60.0)
                file_data = response.content
            
            logger.info(f"âœ… Fichier tÃ©lÃ©chargÃ© depuis Telegram: {file_name} ({len(file_data)} bytes)")
            return file_data, file_name
            
        except Exception as e:
            logger.error(f"â�Œ Erreur tÃ©lÃ©chargement fichier Telegram: {e}")
            raise
    
    async def _create_invoice_from_extraction(
        self, 
        extracted_data, 
        user_id: str, 
        org_id: str,
        file_path: str
    ) -> str:
        """
        CrÃ©e une facture en base de donnÃ©es Ã  partir des donnÃ©es extraites.
        
        Args:
            extracted_data: DonnÃ©es extraites par l'agent
            user_id: ID de l'utilisateur
            org_id: ID de l'organisation
            file_path: Chemin du fichier stockÃ© temporairement
            
        Returns:
            ID de la facture crÃ©Ã©e
        """
        try:
            supabase = get_supabase()
            
            # PrÃ©parer les donnÃ©es de la facture
            invoice_data = {
                'org_id': org_id,
                'created_by': user_id,
                'supplier_name': extracted_data.supplier_name,
                'supplier_address': extracted_data.supplier_address,
                'supplier_siret': extracted_data.supplier_siret,
                'invoice_number': extracted_data.invoice_number,
                'invoice_date': extracted_data.invoice_date,
                'due_date': extracted_data.due_date,
                'amount_ht': extracted_data.amount_ht,
                'amount_ttc': extracted_data.amount_ttc,
                'vat_amount': extracted_data.vat_amount,
                'vat_rate': extracted_data.vat_rate,
                'description': extracted_data.description,
                'status': 'brouillon',
                'source': 'telegram',
                'file_path': file_path,  # Chemin temporaire
                'extraction_confidence': extracted_data.confidence_score,
                'raw_extraction_data': extracted_data.raw_ocr_data
            }
            
            # InsÃ©rer la facture
            result = supabase.table('invoices').insert(invoice_data).execute()
            
            if not result.data:
                raise Exception("Ã‰chec crÃ©ation facture: pas de donnÃ©es retournÃ©es")
            
            invoice_id = result.data[0]['id']
            logger.info(f"âœ… Facture crÃ©Ã©e: {invoice_id}")
            
            # InsÃ©rer les lignes de dÃ©tail si prÃ©sentes
            if extracted_data.line_items:
                line_items_data = []
                for item in extracted_data.line_items:
                    line_items_data.append({
                        'invoice_id': invoice_id,
                        'description': item.description,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'total_ht': item.total_ht,
                        'vat_rate': item.vat_rate
                    })
                
                if line_items_data:
                    supabase.table('invoice_line_items').insert(line_items_data).execute()
                    logger.info(f"âœ… {len(line_items_data)} lignes de dÃ©tail insÃ©rÃ©es")
            
            return invoice_id
            
        except Exception as e:
            logger.error(f"â�Œ Erreur crÃ©ation facture: {e}")
            raise
    
    async def _update_invoice_status(self, invoice_id: str, status: str) -> bool:
        """
        Met Ã  jour le statut d'une facture.
        
        Args:
            invoice_id: ID de la facture
            status: Nouveau statut
            
        Returns:
            True si succÃ¨s, False sinon
        """
        try:
            supabase = get_supabase()
            supabase.table('invoices').update({'status': status}).eq('id', invoice_id).execute()
            logger.info(f"âœ… Statut facture {invoice_id} mis Ã  jour: {status}")
            return True
        except Exception as e:
            logger.error(f"â�Œ Erreur mise Ã  jour statut facture: {e}")
            return False
    
    async def _delete_invoice(self, invoice_id: str) -> bool:
        """
        Supprime une facture (utilisÃ© pour les brouillons annulÃ©s).
        
        Args:
            invoice_id: ID de la facture
            
        Returns:
            True si supprimÃ©e, False sinon
        """
        try:
            supabase = get_supabase()
            
            # RÃ©cupÃ©rer le chemin du fichier pour le supprimer aussi
            result = supabase.table('invoices').select('file_path').eq('id', invoice_id).execute()
            
            if result.data and result.data[0].get('file_path'):
                file_path = result.data[0]['file_path']
                file_storage_service.delete_file(file_path)
            
            # Supprimer la facture
            supabase.table('invoices').delete().eq('id', invoice_id).execute()
            logger.info(f"âœ… Facture supprimÃ©e: {invoice_id}")
            return True
            
        except Exception as e:
            logger.error(f"â�Œ Erreur suppression facture: {e}")
            return False
    
    # ==================== MÃ‰THODES HELPER API TELEGRAM ====================
    
    async def _send_message(
        self, 
        chat_id: int, 
        text: str, 
        reply_markup: Optional[Dict] = None,
        parse_mode: str = "Markdown"
    ) -> Dict:
        """Envoie un message via l'API Telegram."""
        url = f"{self.telegram_api_url}/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            return response.json().get('result', {})
    
    async def _edit_message(
        self, 
        chat_id: int, 
        message_id: Optional[int], 
        text: str,
        parse_mode: str = "Markdown"
    ) -> Dict:
        """Modifie un message existant."""
        if not message_id:
            return {}
        
        url = f"{self.telegram_api_url}/bot{self.bot_token}/editMessageText"
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            return response.json().get('result', {})
    
    async def _delete_message(self, chat_id: int, message_id: int) -> bool:
        """Supprime un message."""
        url = f"{self.telegram_api_url}/bot{self.bot_token}/deleteMessage"
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            return response.json().get('ok', False)
    
    async def _answer_callback_query(self, query_id: str, text: Optional[str] = None) -> bool:
        """RÃ©pond Ã  un callback query."""
        url = f"{self.telegram_api_url}/bot{self.bot_token}/answerCallbackQuery"
        
        payload = {"callback_query_id": query_id}
        if text:
            payload["text"] = text
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            return response.json().get('ok', False)
    
