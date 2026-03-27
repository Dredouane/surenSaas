"""
Service: Bot Manager

Gestion du cycle de vie des bots Telegram:
- Configuration webhook
- Activation/désactivation
- Monitoring status
- Maintenance
"""

import hashlib
import hmac
import secrets
from typing import Optional, Dict, Any
import httpx


class BotManagerService:
    """Service de gestion des bots Telegram."""
    
    def __init__(self, supabase_client, telegram_api_url: str = "https://api.telegram.org"):
        self.supabase = supabase_client
        self.telegram_api_url = telegram_api_url
    
    async def create_bot(
        self,
        org_id: str,
        company_id: Optional[str],
        bot_token: str,
        created_by: str,
        webhook_base_url: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée et configure un nouveau bot Telegram.
        
        Args:
            org_id: UUID de l'organisation
            company_id: UUID de l'entreprise (optionnel)
            bot_token: Token du bot (depuis @BotFather)
            created_by: UUID de l'utilisateur créateur
            webhook_base_url: URL de base pour les webhooks
            description: Description du bot
            
        Returns:
            Dict avec les infos du bot créé
        """
        # Vérifier que le token est valide en appelant l'API Telegram
        bot_info = await self._get_bot_info(bot_token)
        if not bot_info:
            raise ValueError("Token de bot invalide")
        
        # Générer le webhook URL et secret
        webhook_secret = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(bot_token.encode()).hexdigest()
        webhook_path = f"/api/v1/{org_id}/telegram/webhook/{token_hash[:16]}"
        webhook_url = f"{webhook_base_url.rstrip('/')}{webhook_path}"
        
        # Enregistrer en base (sans le token en clair!)
        bot_data = {
            'org_id': org_id,
            'company_id': company_id,
            'bot_token_hash': token_hash,
            'bot_username': bot_info.get('username'),
            'bot_id': bot_info.get('id'),
            'webhook_url': webhook_url,
            'webhook_secret': webhook_secret,
            'description': description,
            'created_by': created_by
        }
        
        result = self.supabase.table('telegram_bots').insert(bot_data).execute()
        bot_record = result.data[0]
        
        # Configurer le webhook Telegram
        webhook_configured = await self._set_webhook(bot_token, webhook_url, webhook_secret)
        
        if webhook_configured:
            # Mettre à jour le status
            self.supabase.table('telegram_bots') \
                .update({
                    'is_configured': True,
                    'configured_at': 'now()'
                }) \
                .eq('id', bot_record['id']) \
                .execute()
        
        return {
            'id': bot_record['id'],
            'bot_username': bot_info.get('username'),
            'webhook_url': webhook_url,
            'is_configured': webhook_configured,
            'welcome_message': 'Configuration terminée! Le bot est actif.'
        }
    
    async def _get_bot_info(self, token: str) -> Optional[Dict]:
        """Récupère les infos du bot via l'API Telegram."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.telegram_api_url}/bot{token}/getMe",
                    timeout=10.0
                )
                data = response.json()
                if data.get('ok'):
                    return data.get('result')
            except Exception:
                pass
        return None
    
    async def _set_webhook(self, token: str, webhook_url: str, secret: str) -> bool:
        """Configure le webhook Telegram."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.telegram_api_url}/bot{token}/setWebhook",
                    json={
                        'url': webhook_url,
                        'secret_token': secret,
                        'allowed_updates': ['message', 'callback_query']
                    },
                    timeout=10.0
                )
                data = response.json()
                return data.get('ok', False)
            except Exception:
                return False
    
    async def delete_bot(self, bot_id: str, org_id: str) -> bool:
        """
        Désactive un bot (ne supprime pas physiquement).
        
        Returns:
            True si succès
        """
        # Mettre à jour le status
        result = self.supabase.table('telegram_bots') \
            .update({'is_active': False}) \
            .eq('id', bot_id) \
            .eq('org_id', org_id) \
            .execute()
        
        return len(result.data) > 0
    
    async def get_bot_status(self, bot_id: str, org_id: str) -> Optional[Dict]:
        """
        Récupère le status d'un bot.
        
        Returns:
            Dict avec le status ou None si non trouvé
        """
        result = self.supabase.table('telegram_bots') \
            .select('*') \
            .eq('id', bot_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if not result.data:
            return None
        
        bot = result.data
        
        # Compter les interactions récentes
        recent_interactions = self.supabase.table('telegram_audit') \
            .select('*', count='exact') \
            .eq('bot_id', bot_id) \
            .gte('created_at', 'now() - interval ''24 hours''') \
            .execute()
        
        # Compter les erreurs récentes
        recent_errors = self.supabase.table('telegram_audit') \
            .select('*', count='exact') \
            .eq('bot_id', bot_id) \
            .eq('status', 'failed') \
            .gte('created_at', 'now() - interval ''24 hours''') \
            .execute()
        
        return {
            'id': bot['id'],
            'bot_username': bot['bot_username'],
            'is_active': bot['is_active'],
            'is_configured': bot['is_configured'],
            'created_at': bot['created_at'],
            'stats_24h': {
                'interactions': recent_interactions.count,
                'errors': recent_errors.count
            }
        }
    
    async def list_bots(self, org_id: str, include_inactive: bool = False) -> list:
        """Liste tous les bots d'une organisation."""
        query = self.supabase.table('telegram_bots') \
            .select('*, companies:company_id(name, slug)') \
            .eq('org_id', org_id)
        
        if not include_inactive:
            query = query.eq('is_active', True)
        
        result = query.execute()
        return result.data or []
    
    async def get_bot_by_webhook_token(self, token_hash: str, org_id: str) -> Optional[Dict]:
        """
        Récupère un bot par son hash de token (pour les webhooks).
        
        Args:
            token_hash: Hash du token webhook
            org_id: UUID de l'organisation
            
        Returns:
            Bot record ou None
        """
        # Chercher le bot où le hash commence par le token fourni
        result = self.supabase.table('telegram_bots') \
            .select('*') \
            .eq('org_id', org_id) \
            .like('bot_token_hash', f"{token_hash}%") \
            .eq('is_active', True) \
            .single() \
            .execute()
        
        return result.data if result.data else None
    
    def verify_webhook_signature(
        self,
        bot_secret: str,
        request_body: bytes,
        signature_header: Optional[str] = None
    ) -> bool:
        """
        Vérifie la signature d'une requête webhook Telegram.
        
        Telegram envoie un header X-Telegram-Bot-Api-Secret-Token
        qu'on peut vérifier.
        """
        if not signature_header:
            return True  # Si pas de vérification configurée
        
        # Telegram envoie le secret directement
        return hmac.compare_digest(signature_header, bot_secret)
