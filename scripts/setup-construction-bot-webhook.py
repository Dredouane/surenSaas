#!/usr/bin/env python3
"""
Script pour configurer le webhook du bot Telegram Construction.

Usage:
    python scripts/setup-construction-bot-webhook.py --env test
    python scripts/setup-construction-bot-webhook.py --env prod
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ajouter le dossier backend au path
sys.path.insert(0, str(Path(__file__).parent.parent / "surenSaasBack"))

import httpx
from dotenv import load_dotenv


def load_env_file(environment: str):
    """Charge le fichier .env appropriÃ©."""
    env_file = Path(__file__).parent.parent / f".env.{environment}"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"âœ… Fichier chargÃ©: {env_file}")
    else:
        print(f"âš ï¸� Fichier non trouvÃ©: {env_file}")
        # Essayer .env
        load_dotenv()


async def setup_webhook(environment: str):
    """Configure le webhook Telegram."""
    
    # Charger les variables
    load_env_file(environment)
    
    # RÃ©cupÃ©rer les variables
    token = os.getenv(f"{environment.upper()}_TELEGRAM_CONSTRUCTION_BOT_TOKEN")
    api_url = os.getenv("API_URL", "")
    
    if not token:
        print(f"â�Œ Erreur: Token non trouvÃ© ({environment.upper()}_TELEGRAM_CONSTRUCTION_BOT_TOKEN)")
        print("Assurez-vous que le fichier .env est configurÃ© correctement.")
        return False
    
    if not api_url:
        print("â�Œ Erreur: API_URL non dÃ©fini")
        return False
    
    # Construire l'URL du webhook
    webhook_url = f"{api_url.rstrip('/')}/api/v1/webhook/construction"
    
    print(f"\nðŸ”§ Configuration webhook pour environnement: {environment}")
    print(f"   Webhook URL: {webhook_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. VÃ©rifier le bot
            me_response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10.0
            )
            me_data = me_response.json()
            
            if not me_data.get('ok'):
                print(f"â�Œ Erreur: Token invalide")
                print(f"   DÃ©tail: {me_data.get('description', 'Unknown')}")
                return False
            
            bot_info = me_data['result']
            print(f"   Bot: @{bot_info['username']} (ID: {bot_info['id']})")
            
            # 2. Configurer le webhook
            webhook_response = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={
                    'url': webhook_url,
                    'allowed_updates': ['message', 'callback_query']
                },
                timeout=10.0
            )
            webhook_data = webhook_response.json()
            
            if webhook_data.get('ok'):
                print(f"âœ… Webhook configurÃ© avec succÃ¨s!")
                
                # 3. VÃ©rifier le status
                info_response = await client.get(
                    f"https://api.telegram.org/bot{token}/getWebhookInfo",
                    timeout=10.0
                )
                info_data = info_response.json()
                
                if info_data.get('ok'):
                    info = info_data['result']
                    print(f"\nðŸ“Š Informations webhook:")
                    print(f"   URL: {info.get('url', 'N/A')}")
                    print(f"   Has custom cert: {info.get('has_custom_certificate', False)}")
                    print(f"   Pending updates: {info.get('pending_update_count', 0)}")
                    if info.get('last_error_date'):
                        print(f"   âš ï¸� Last error: {info.get('last_error_message', 'Unknown')}")
                
                return True
            else:
                print(f"â�Œ Erreur configuration webhook:")
                print(f"   {webhook_data.get('description', 'Unknown error')}")
                return False
                
    except Exception as e:
        print(f"â�Œ Erreur: {e}")
        return False


async def delete_webhook(environment: str):
    """Supprime le webhook Telegram."""
    
    load_env_file(environment)
    token = os.getenv(f"{environment.upper()}_TELEGRAM_CONSTRUCTION_BOT_TOKEN")
    
    if not token:
        print(f"â�Œ Token non trouvÃ©")
        return False
    
    print(f"\nðŸ—‘ï¸� Suppression webhook pour environnement: {environment}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook",
                timeout=10.0
            )
            data = response.json()
            
            if data.get('ok'):
                print("âœ… Webhook supprimÃ© avec succÃ¨s!")
                return True
            else:
                print(f"â�Œ Erreur: {data.get('description', 'Unknown')}")
                return False
                
    except Exception as e:
        print(f"â�Œ Erreur: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Configure le webhook du bot Telegram Construction"
    )
    parser.add_argument(
        '--env',
        choices=['test', 'prod'],
        required=True,
        help='Environnement (test ou prod)'
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Supprimer le webhook au lieu de le configurer'
    )
    
    args = parser.parse_args()
    
    if args.delete:
        success = asyncio.run(delete_webhook(args.env))
    else:
        success = asyncio.run(setup_webhook(args.env))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
