"""
Service: Notification

Envoi de notifications aux utilisateurs (web push, email, Telegram).
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx


class NotificationService:
    """Service d'envoi de notifications multi-canal."""
    
    def __init__(self, supabase_client, telegram_token: Optional[str] = None):
        self.supabase = supabase_client
        self.telegram_token = telegram_token
        self.telegram_api_url = "https://api.telegram.org"
    
    async def send_to_user(
        self,
        user_id: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        notification_type: str = 'general',
        channels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Envoie une notification à un utilisateur.
        
        Args:
            user_id: UUID de l'utilisateur
            title: Titre de la notification
            message: Corps du message
            action_url: URL d'action (optionnel)
            notification_type: Type de notification
            channels: Canaux à utiliser ['telegram', 'email', 'push']
            
        Returns:
            Résultat de l'envoi par canal
        """
        if channels is None:
            channels = ['telegram']  # Par défaut Telegram
        
        results = {}
        
        if 'telegram' in channels:
            results['telegram'] = await self._send_telegram_notification(
                user_id, title, message, action_url, action_label
            )
        
        if 'email' in channels:
            results['email'] = await self._send_email_notification(
                user_id, title, message, action_url
            )
        
        if 'push' in channels:
            results['push'] = await self._send_push_notification(
                user_id, title, message, action_url
            )
        
        return results
    
    async def _send_telegram_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envoie une notification Telegram."""
        telegram_user = self.supabase.table('telegram_users') \
            .select('telegram_id') \
            .eq('user_id', user_id) \
            .eq('notification_enabled', True) \
            .execute()
        
        if not telegram_user.data or len(telegram_user.data) == 0:
            return {'sent': False, 'reason': 'user_not_linked_to_telegram'}
        
        telegram_id = telegram_user.data[0]['telegram_id']
        
        full_message = f"📋 *{title}*\n\n{message}"
        
        if action_url:
            label = action_label or "Voir dans l'application"
            full_message += f"\n\n[{label}]({action_url})"
        
        # Envoyer via API Telegram
        if not self.telegram_token:
            return {'sent': False, 'reason': 'no_telegram_token_configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.telegram_api_url}/bot{self.telegram_token}/sendMessage",
                    json={
                        'chat_id': telegram_id,
                        'text': full_message,
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True
                    },
                    timeout=10.0
                )
                
                data = response.json()
                
                if data.get('ok'):
                    return {'sent': True, 'message_id': data['result']['message_id']}
                else:
                    return {'sent': False, 'reason': data.get('description', 'unknown_error')}
                    
        except Exception as e:
            return {'sent': False, 'reason': str(e)}
    
    async def _send_email_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        action_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envoie une notification email."""
        # TODO: Implémenter l'envoi d'emails
        return {'sent': False, 'reason': 'not_implemented'}
    
    async def _send_push_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        action_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envoie une notification push navigateur."""
        # TODO: Implémenter les push notifications
        return {'sent': False, 'reason': 'not_implemented'}
    
    async def notify_admins(
        self,
        org_id: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_label: str = "Voir dans l'application",
        notification_type: str = 'general'
    ) -> Dict[str, Any]:
        """Notifie tous les admins d'une organisation via Telegram."""
        managers = self.supabase.table('users') \
            .select('id') \
            .eq('org_id', org_id) \
            .eq('role', 'admin') \
            .execute()

        if not managers.data:
            return {'sent': 0, 'reason': 'no_managers_found'}

        sent_count = 0
        for manager in managers.data:
            result = await self.send_to_user(
                user_id=manager['id'],
                title=title,
                message=message,
                action_url=action_url,
                notification_type=notification_type
            )
            if result.get('telegram', {}).get('sent'):
                sent_count += 1

        return {
            'sent': sent_count,
            'total_admins': len(managers.data),
        }

    async def notify_invoice_pending(
        self,
        org_id: str,
        invoice_id: str,
        supplier_name: str,
        amount_ttc: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Notifie tous les gérants qu'une facture est en attente.
        
        Returns:
            Résumé des notifications envoyées
        """
        # Récupérer les gérants (admins) de l'org
        # Changement: sélectionne 'id' au lieu de 'user_id' pour correspondre à la table 'users'
        managers = self.supabase.table('users') \
            .select('id') \
            .eq('org_id', org_id) \
            .eq('role', 'admin') \
            .execute()
        
        if not managers.data:
            return {'sent': 0, 'reason': 'no_managers_found'}
        
        # Construire le message
        amount_str = f"{amount_ttc:.2f}€" if amount_ttc else "montant non précisé"
        title = "Nouvelle facture en attente"
        message = (
            f"Une facture de *{supplier_name}* pour *{amount_ttc:.2f}*€ "
            f"est en attente de validation."
        )
        
        # Envoyer à chaque gérant
        sent_count = 0
        for manager in managers.data:
            result = await self.send_to_user(
                user_id=manager['id'],
                title=title,
                message=message,
                action_url=f"/{org_id}/construction/invoices/{invoice_id}",
                notification_type='invoice_pending_validation'
            )
            
            if result.get('telegram', {}).get('sent'):
                sent_count += 1
        
        return {
            'sent': sent_count,
            'total_managers': len(managers.data),
            'invoice_id': invoice_id
        }
    
    async def notify_invoice_validated(
        self,
        user_id: str,
        invoice_id: str,
        org_id: str,
        supplier_name: str
    ) -> Dict[str, Any]:
        """Notifie un conducteur que sa facture a été validée."""
        return await self.send_to_user(
            user_id=user_id,
            title="Facture validée",
            message=f"Votre facture de *{supplier_name}* a été validée par un gérant.",
            action_url=f"/{org_id}/construction/invoices/{invoice_id}",
            notification_type='invoice_validated'
        )
    
    async def notify_invoice_rejected(
        self,
        user_id: str,
        invoice_id: str,
        org_id: str,
        supplier_name: str,
        rejection_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Notifie un conducteur que sa facture a été rejetée."""
        message = f"Votre facture de *{supplier_name}* a été rejetée."
        
        if rejection_reason:
            message += f"\n\n*Raison:* {rejection_reason}"
        
        return await self.send_to_user(
            user_id=user_id,
            title="Facture rejetée",
            message=message,
            action_url=f"/{org_id}/construction/invoices/{invoice_id}",
            notification_type='invoice_rejected'
        )
