"""Service de gestion des invitations Telegram multi-bots."""
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from app.core.logging import get_logger
from app.services.telegram.bots_registry import telegram_bots_registry, TelegramBotConfig

logger = get_logger(__name__)


class TelegramInvitationService:
    """
    Service pour gérer les invitations aux bots Telegram.
    
    Supporte plusieurs bots (construction, audit, nettoyage, etc.)
    Chaque invitation est liée à un bot spécifique.
    
    Le lien généré est au format simplifié:
    https://t.me/{bot_username}?start={user_id}
    
    Format simplifié (respecte la limite de 64 caractères de Telegram):
    - user_id: UUID de l'utilisateur (36 caractères)
    - Le bot vérifie que l'utilisateur existe dans la DB
    """

    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "test").lower()
        self.invitation_secret = os.getenv("TELEGRAM_INVITATION_SECRET", "")
        
        if not self.invitation_secret:
            # Générer un secret par défaut si non défini (à changer en prod!)
            self.invitation_secret = secrets.token_urlsafe(32)
            logger.warning("TELEGRAM_INVITATION_SECRET non défini, utilisation d'un secret généré")
    
    def _generate_signature(self, user_id: str, org_id: str, bot_id: str, exp: int) -> str:
        """Génère une signature HMAC pour le payload."""
        message = f"{user_id}:{org_id}:{bot_id}:{exp}"
        signature = hashlib.sha256(
            f"{message}:{self.invitation_secret}".encode()
        ).hexdigest()[:16]
        return signature
    
    def _verify_signature(self, user_id: str, org_id: str, bot_id: str, exp: int, sig: str) -> bool:
        """Vérifie la signature du payload."""
        expected_sig = self._generate_signature(user_id, org_id, bot_id, exp)
        return secrets.compare_digest(sig, expected_sig)
    
    def generate_invitation_link(
        self, 
        user_id: str, 
        org_id: str,
        bot_id: str,
        expires_in_hours: int = 168,  # 7 jours par défaut
        bot_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Génère un lien d'invitation Telegram pour un utilisateur et un bot spécifique.
        
        Args:
            user_id: UUID de l'utilisateur
            org_id: UUID de l'organisation
            bot_id: ID du bot (e.g., 'construction', 'audit')
            expires_in_hours: Durée de validité du lien en heures
            bot_config: Config du bot (optionnel, sinon récupère depuis registry)
            
        Returns:
            Dict avec le lien et les métadonnées
            
        Raises:
            ValueError: Si le bot n'est pas configuré
        """
        # Vérifier que le bot existe et est configuré
        if bot_config is None:
            bot_config = self.get_bot_config(bot_id)
        if not bot_config:
            raise ValueError(f"Bot '{bot_id}' non configuré ou non trouvé")
        
        # VERSION SIMPLIFIÉE : Utiliser directement le user_id comme paramètre
        # Format: https://t.me/{bot_username}?start={user_uuid}
        # Respecte la limite de 64 caractères de Telegram
        
        # Construire le lien avec user_id direct
        # Gérer à la fois dict (depuis Supabase) et objet (depuis registry)
        if isinstance(bot_config, dict):
            bot_username = bot_config.get('bot_username', '')
            bot_id_str = str(bot_config.get('bot_id', 'Bot'))
            bot_name = bot_id_str.replace('_', ' ').title()
            bot_icon = '🤖'
            description = bot_config.get('description', 'Bot Telegram')
        else:
            bot_username = bot_config.username
            bot_name = bot_config.bot_name
            bot_icon = bot_config.icon
            description = bot_config.description
        
        telegram_link = f"https://t.me/{bot_username}?start={user_id}"
        
        logger.info(f"Lien d'invitation généré pour user {user_id} vers bot '{bot_id}'")
        
        return {
            "telegram_link": telegram_link,
            "bot_id": bot_id,
            "bot_name": bot_name,
            "bot_username": bot_username,
            "bot_icon": bot_icon,
            "description": description,
            "expires_at": (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat(),
            "user_id": user_id,
            "org_id": org_id
        }
    
    def decode_invitation_payload(self, payload_b64: str) -> Optional[Dict[str, Any]]:
        """
        Décode et vérifie un payload d'invitation.
        
        Args:
            payload_b64: Payload encodé en base64
            
        Returns:
            Dict avec user_id, org_id, bot_id si valide, None sinon
        """
        try:
            import base64
            import json
            
            # Décoder le base64
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
            
            payload_json = base64.urlsafe_b64decode(payload_b64).decode()
            payload = json.loads(payload_json)
            
            user_id = payload.get("u")
            org_id = payload.get("o")
            bot_id = payload.get("b")
            exp = payload.get("e")
            sig = payload.get("s")
            
            if not all([user_id, org_id, bot_id, exp, sig]):
                logger.warning("Payload incomplet")
                return None
            
            # Vérifier l'expiration
            if datetime.utcnow().timestamp() > exp:
                logger.warning(f"Lien expiré pour user {user_id}")
                return None
            
            # Vérifier la signature
            if not self._verify_signature(user_id, org_id, bot_id, exp, sig):
                logger.warning(f"Signature invalide pour user {user_id}")
                return None
            
            return {
                "user_id": user_id,
                "org_id": org_id,
                "bot_id": bot_id,
                "expires_at": datetime.fromtimestamp(exp).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur décodage payload: {e}")
            return None
    
    def get_available_bots(self) -> list:
        """Retourne la liste des bots disponibles pour l'affichage."""
        return telegram_bots_registry.get_available_bots_for_display()
    
    def get_bot_config(self, bot_id: str) -> Optional[TelegramBotConfig]:
        """Retourne la configuration d'un bot spécifique."""
        return telegram_bots_registry.get_bot(bot_id)


# Singleton
telegram_invitation_service = TelegramInvitationService()
