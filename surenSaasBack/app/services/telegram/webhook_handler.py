"""
Service: Webhook Handler

Gestion des webhooks entrants de Telegram.
Dispatche les requêtes vers les services appropriés.
"""

from typing import Dict, Any, Optional
from datetime import datetime


class WebhookHandlerService:
    """Handler pour les webhooks Telegram entrants."""
    
    def __init__(self, supabase_client, audit_service, bot_manager, upload_invoice_service):
        self.supabase = supabase_client
        self.audit = audit_service
        self.bot_manager = bot_manager
        self.upload_invoice = upload_invoice_service
    
    async def handle_update(self, bot_id: str, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une update webhook Telegram.
        
        Args:
            bot_id: UUID du bot
            update: Update Telegram (message, callback_query, etc.)
            
        Returns:
            Réponse à renvoyer (généralement vide pour 200 OK)
        """
        # Créer l'entrée d'audit
        audit_log = await self.audit.create_log(
            bot_id=bot_id,
            telegram_user_id=self._extract_user_id(update),
            interaction_type=self._determine_interaction_type(update),
            payload=update
        )
        
        try:
            # Dispatcher vers le bon handler
            if 'message' in update:
                result = await self._handle_message(bot_id, update['message'], audit_log['id'])
            elif 'callback_query' in update:
                result = await self._handle_callback_query(bot_id, update['callback_query'], audit_log['id'])
            else:
                result = {'status': 'ignored', 'reason': 'unknown_update_type'}
            
            # Mettre à jour l'audit
            await self.audit.complete_log(
                audit_log_id=audit_log['id'],
                status='completed',
                result=result
            )
            
            return {'status': 'ok'}
            
        except Exception as e:
            await self.audit.complete_log(
                audit_log_id=audit_log['id'],
                status='failed',
                error=str(e)
            )
            raise
    
    def _extract_user_id(self, update: Dict[str, Any]) -> Optional[int]:
        """Extrait l'ID utilisateur Telegram d'une update."""
        if 'message' in update:
            return update['message'].get('from', {}).get('id')
        elif 'callback_query' in update:
            return update['callback_query'].get('from', {}).get('id')
        return None
    
    def _determine_interaction_type(self, update: Dict[str, Any]) -> str:
        """Détermine le type d'interaction."""
        if 'message' in update:
            message = update['message']
            if message.get('text', '').startswith('/'):
                return 'command_received'
            elif 'document' in message or 'photo' in message:
                return 'file_received'
            else:
                return 'message_received'
        elif 'callback_query' in update:
            return 'button_clicked'
        return 'message_received'
    
    async def _handle_message(
        self,
        bot_id: str,
        message: Dict[str, Any],
        audit_log_id: str
    ) -> Dict[str, Any]:
        """Traite un message entrant."""
        text = message.get('text', '')
        
        # Commande /start
        if text == '/start':
            return await self._handle_start_command(bot_id, message)
        
        # Réception de fichier (photo ou document)
        if 'photo' in message or 'document' in message:
            return await self._handle_file_received(bot_id, message, audit_log_id)
        
        # Message texte simple
        return await self._handle_text_message(bot_id, message)
    
    async def _handle_start_command(self, bot_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Gère la commande /start."""
        telegram_user = message.get('from', {})
        
        # TODO: Vérifier si l'utilisateur est lié à un compte app
        # Pour l'instant, on envoie un message de bienvenue
        return {
            'action': 'send_welcome',
            'telegram_user_id': telegram_user.get('id'),
            'message': 'Bienvenue! Envoyez une photo ou PDF de facture pour la traiter.'
        }
    
    async def _handle_file_received(
        self,
        bot_id: str,
        message: Dict[str, Any],
        audit_log_id: str
    ) -> Dict[str, Any]:
        """Gère la réception d'un fichier (photo ou PDF)."""
        # Récupérer les infos du bot
        bot_result = self.supabase.table('telegram_bots') \
            .select('org_id, company_id') \
            .eq('id', bot_id) \
            .single() \
            .execute()
        
        if not bot_result.data:
            return {'error': 'bot_not_found'}
        
        bot_data = bot_result.data
        org_id = bot_data['org_id']
        company_id = bot_data.get('company_id')
        
        # Déterminer le type de fichier et récupérer le file_id
        if 'photo' in message:
            # Prendre la plus grande photo
            photos = message['photo']
            file_id = photos[-1]['file_id']  # Dernière = plus grande
            file_type = 'photo'
        elif 'document' in message:
            file_id = message['document']['file_id']
            file_type = 'pdf' if message['document'].get('mime_type') == 'application/pdf' else 'document'
        else:
            return {'error': 'unsupported_file_type'}
        
        # TODO: Télécharger le fichier depuis Telegram et le stocker
        # Pour l'instant, on simule l'URL
        file_url = f"https://storage.example.com/telegram/{file_id}"
        
        # Démarrer le workflow d'upload
        result = await self.upload_invoice.start_workflow(
            telegram_user_id=message['from']['id'],
            org_id=org_id,
            company_id=company_id,
            file_url=file_url,
            file_type=file_type,
            audit_log_id=audit_log_id
        )
        
        return {
            'action': 'process_invoice',
            'success': result.success,
            'invoice_id': result.invoice_id,
            'message': result.message
        }
    
    async def _handle_text_message(self, bot_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Gère un message texte simple."""
        return {
            'action': 'send_help',
            'message': 'Envoyez une photo ou PDF de facture, ou utilisez /start pour commencer.'
        }
    
    async def _handle_callback_query(
        self,
        bot_id: str,
        callback_query: Dict[str, Any],
        audit_log_id: str
    ) -> Dict[str, Any]:
        """Gère un clic sur bouton inline."""
        data = callback_query.get('data', '')
        
        # Dispatcher selon le callback data
        if data.startswith('validate_invoice:'):
            # TODO: Gérer validation facture
            pass
        elif data.startswith('reject_invoice:'):
            # TODO: Gérer rejet facture
            pass
        
        return {'action': 'callback_handled', 'data': data}
