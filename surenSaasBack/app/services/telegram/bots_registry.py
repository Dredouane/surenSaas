"""
Configuration des bots Telegram pour l'organisation.

Cette configuration définit tous les bots Telegram disponibles pour l'entreprise.
Chaque bot a son propre token et fonctionnalités.

Les bots sont définis via les variables d'environnement avec le format:
{ENV}_{BOT_ID}_TELEGRAM_BOT_TOKEN
e.g., TEST_CONSTRUCTION_TELEGRAM_BOT_TOKEN
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TelegramBotConfig:
    """Configuration d'un bot Telegram."""
    bot_id: str  # Identifiant unique du bot (e.g., 'construction', 'audit', etc.)
    bot_name: str  # Nom affiché du bot
    description: str  # Description des fonctionnalités
    token: str  # Token Telegram (depuis env var)
    username: str  # Username Telegram (e.g., 'suren_construction_bot')
    webhook_secret: Optional[str] = None  # Secret pour webhook
    icon: str = "📱"  # Emoji pour l'interface


class TelegramBotsRegistry:
    """
    Registre de tous les bots Telegram disponibles.
    
    Les bots sont détectés automatiquement à partir des variables d'environnement
    avec le format: {ENV}_{BOT_ID}_TELEGRAM_BOT_TOKEN
    """
    
    # Bots prédéfinis avec leurs métadonnées
    # Les tokens sont lus depuis les variables d'environnement
    BOTS_METADATA = {
        'construction': {
            'name': 'Construction',
            'description': 'Envoi et traitement des factures de construction',
            'icon': '🏗️',
        },
        'audit': {
            'name': 'Audit Énergétique',
            'description': 'Gestion des audits énergétiques et rapports',
            'icon': '⚡',
        },
        'nettoyage': {
            'name': 'Nettoyage',
            'description': 'Planification et suivi des interventions de nettoyage',
            'icon': '🧹',
        },
        'general': {
            'name': 'Général',
            'description': 'Notifications et informations générales',
            'icon': '📢',
        },
    }
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "test").lower()
        self._bots: Dict[str, TelegramBotConfig] = {}
        self._load_bots()
    
    def _load_bots(self):
        """Charge tous les bots configurés depuis les variables d'environnement."""
        env_prefix = self.environment.upper()
        
        for bot_id, metadata in self.BOTS_METADATA.items():
            # Chercher le token avec le format: TEST_CONSTRUCTION_TELEGRAM_BOT_TOKEN
            token_var = f"{env_prefix}_{bot_id.upper()}_TELEGRAM_BOT_TOKEN"
            username_var = f"{env_prefix}_{bot_id.upper()}_TELEGRAM_BOT_USERNAME"
            # Format alternatif: TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN
            alt_token_var = f"{env_prefix}_TELEGRAM_{bot_id.upper()}_BOT_TOKEN"
            alt_username_var = f"{env_prefix}_TELEGRAM_{bot_id.upper()}_BOT_USERNAME"
            webhook_secret_var = f"TELEGRAM_WEBHOOK_SECRET_{env_prefix}_{bot_id.upper()}"
            
            # Essayer d'abord le format standard, puis l'alternatif
            token = os.getenv(token_var) or os.getenv(alt_token_var)
            username = os.getenv(username_var) or os.getenv(alt_username_var) or f"suren_{bot_id}_bot"
            webhook_secret = os.getenv(webhook_secret_var)
            
            if token:
                self._bots[bot_id] = TelegramBotConfig(
                    bot_id=bot_id,
                    bot_name=metadata['name'],
                    description=metadata['description'],
                    token=token,
                    username=username,
                    webhook_secret=webhook_secret,
                    icon=metadata['icon']
                )
                logger.info(f"✅ Bot '{bot_id}' chargé: @{username}")
            else:
                logger.debug(f"⚠️ Bot '{bot_id}' non configuré (variables {token_var} ou {alt_token_var} manquantes)")
    
    def get_bot(self, bot_id: str) -> Optional[TelegramBotConfig]:
        """Récupère la configuration d'un bot spécifique."""
        return self._bots.get(bot_id)
    
    def get_all_bots(self) -> List[TelegramBotConfig]:
        """Liste tous les bots configurés."""
        return list(self._bots.values())
    
    def get_bot_ids(self) -> List[str]:
        """Liste tous les IDs de bots configurés."""
        return list(self._bots.keys())
    
    def is_bot_configured(self, bot_id: str) -> bool:
        """Vérifie si un bot est configuré."""
        return bot_id in self._bots
    
    def get_available_bots_for_display(self) -> List[Dict]:
        """
        Retourne les infos des bots pour l'affichage frontend.
        
        Returns:
            Liste de dicts avec id, name, description, icon, username
        """
        return [
            {
                'bot_id': bot.bot_id,
                'bot_name': bot.bot_name,
                'description': bot.description,
                'icon': bot.icon,
                'username': bot.username,
                'configured': True
            }
            for bot in self._bots.values()
        ]


# Singleton
telegram_bots_registry = TelegramBotsRegistry()
