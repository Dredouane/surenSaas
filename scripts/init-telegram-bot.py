#!/usr/bin/env python3
"""
Script d'initialisation d'un bot Telegram pour SurenSaaS

Ce script automatise la configuration d'un bot Telegram:
1. Vérifie les variables d'environnement
2. Configure le webhook via l'API Telegram
3. Crée l'entrée en base de données
4. Affiche les informations de configuration

Configuration requise dans ~/.bashrc:
    # Pour l'environnement TEST
    export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN="votre_token"
    export SUREN_TEST_API_BASE_URL="https://test-api.run.app"
    
    # Pour l'environnement PROD
    export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN="votre_token"
    export SUREN_PROD_API_BASE_URL="https://prod-api.run.app"
    
    # Supabase (commun ou spécifique)
    export SUPABASE_URL="https://xxxxx.supabase.co"
    export SUPABASE_SERVICE_KEY="votre_clé_service"

Usage:
    # Environnement TEST (utilise SUREN_TEST_* variables)
    python scripts/init-telegram-bot.py --env test --org-id <uuid> --company-id <uuid>
    
    # Environnement PROD (utilise SUREN_PROD_* variables)
    python scripts/init-telegram-bot.py --env prod --org-id <uuid> --company-id <uuid>
    
    # Avec token direct (override les variables d'env)
    python scripts/init-telegram-bot.py --env test --token "123:ABC" --org-id <uuid>
"""

import os
import sys
import argparse
import asyncio
import hashlib
import secrets
from typing import Optional, Dict, Any

try:
    import httpx
    from supabase import create_client, Client
except ImportError:
    print("❌ Erreur: Dépendances manquantes.")
    print("   Installez-les avec: pip install httpx supabase")
    sys.exit(1)


def get_env_variable(env: str, suffix: str) -> Optional[str]:
    """Récupère une variable d'environnement avec le bon préfixe."""
    prefix = f"SUREN_{env.upper()}_"
    var_name = f"{prefix}{suffix}"
    return os.getenv(var_name)


def check_environment(args) -> Dict[str, str]:
    """Vérifie que les variables d'environnement sont configurées."""
    env = args.env.upper()
    errors = []
    config = {}
    
    # Token Telegram (depuis --token ou variable d'env)
    if args.token:
        config['token'] = args.token
    else:
        token = get_env_variable(args.env, 'TELEGRAM_CONSTRUCTION_BOT_TOKEN')
        if not token:
            errors.append(f"  - SUREN_{env}_TELEGRAM_CONSTRUCTION_BOT_TOKEN: Token du bot (depuis @BotFather)")
        else:
            config['token'] = token
    
    # API Base URL
    api_url = get_env_variable(args.env, 'API_BASE_URL')
    if not api_url:
        errors.append(f"  - SUREN_{env}_API_BASE_URL: URL de base de votre API")
    else:
        config['api_url'] = api_url
    
    # Supabase (commun aux deux env ou avec préfixe)
    supabase_url = os.getenv('SUPABASE_URL')
    if not supabase_url:
        # Essayer avec préfixe
        supabase_url = get_env_variable(args.env, 'SUPABASE_URL')
    if not supabase_url:
        errors.append("  - SUPABASE_URL: URL Supabase")
    else:
        config['supabase_url'] = supabase_url
    
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    if not supabase_key:
        supabase_key = get_env_variable(args.env, 'SUPABASE_SERVICE_KEY')
    if not supabase_key:
        errors.append("  - SUPABASE_SERVICE_KEY: Clé service Supabase")
    else:
        config['supabase_key'] = supabase_key
    
    if errors:
        print(f"❌ Variables d'environnement manquantes pour l'environnement {env}:")
        for e in errors:
            print(e)
        print(f"\n📋 Pour les configurer, ajoutez dans votre ~/.bashrc:")
        print(f"    # Pour TEST:")
        print(f"    export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN='votre_token_ici'")
        print(f"    export SUREN_TEST_API_BASE_URL='https://test-api.run.app'")
        print(f"    \n    # Pour PROD:")
        print(f"    export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN='votre_token_ici'")
        print(f"    export SUREN_PROD_API_BASE_URL='https://prod-api.run.app'")
        print(f"    \n    # Supabase (commun):")
        print(f"    export SUPABASE_URL='https://xxxxx.supabase.co'")
        print(f"    export SUPABASE_SERVICE_KEY='votre_clé_service'")
        print(f"\n💡 Redémarrez votre terminal ou exécutez: source ~/.bashrc")
        print(f"\n💡 Alternative: Passez le token directement avec --token")
        sys.exit(1)
    
    return config


async def verify_bot_token(token: str) -> Optional[dict]:
    """Vérifie que le token est valide en appelant l'API Telegram."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10.0
            )
            data = response.json()
            
            if data.get('ok'):
                return data['result']
            else:
                print(f"❌ Token invalide: {data.get('description', 'Erreur inconnue')}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification du token: {e}")
            return None


async def configure_webhook(token: str, webhook_url: str, secret: str) -> bool:
    """Configure le webhook Telegram."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={
                    'url': webhook_url,
                    'secret_token': secret,
                    'allowed_updates': ['message', 'callback_query'],
                    'drop_pending_updates': True
                },
                timeout=10.0
            )
            data = response.json()
            
            if data.get('ok'):
                print("✅ Webhook configuré avec succès")
                return True
            else:
                print(f"⚠️  Erreur configuration webhook: {data.get('description')}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors de la configuration du webhook: {e}")
            return False


def create_bot_in_database(
    supabase: Client,
    org_id: str,
    company_id: Optional[str],
    token_hash: str,
    bot_info: dict,
    webhook_url: str,
    webhook_secret: str,
    description: Optional[str]
) -> Optional[dict]:
    """Crée l'entrée du bot en base de données."""
    try:
        bot_data = {
            'org_id': org_id,
            'company_id': company_id,
            'bot_token_hash': token_hash,
            'bot_username': bot_info['username'],
            'bot_id': bot_info['id'],
            'webhook_url': webhook_url,
            'webhook_secret': webhook_secret,
            'is_active': True,
            'is_configured': True,
            'configured_at': 'now()',
            'description': description,
            'welcome_message': 'Bienvenue! Envoyez une photo ou PDF de facture pour la traiter.'
        }
        
        result = supabase.table('telegram_bots').insert(bot_data).execute()
        
        if result.data:
            return result.data[0]
        else:
            print("❌ Erreur lors de la création en base de données")
            return None
            
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(
        description="Initialise un bot Telegram pour SurenSaaS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Test avec variables d'environnement
  python scripts/init-telegram-bot.py --env test --org-id <uuid> --company-id <uuid>
  
  # Prod avec token direct
  python scripts/init-telegram-bot.py --env prod --token "123:ABC" --org-id <uuid>
  
  # Mode test sans base de données
  python scripts/init-telegram-bot.py --env test --token "123:ABC" --org-id <uuid> --skip-db
        """
    )
    parser.add_argument(
        '--env',
        required=True,
        choices=['test', 'prod'],
        help='Environnement (test ou prod) - détermine les variables SUREN_TEST_* ou SUREN_PROD_*'
    )
    parser.add_argument(
        '--token',
        help='Token du bot Telegram (depuis @BotFather) - override la variable d\'env'
    )
    parser.add_argument(
        '--org-id',
        required=True,
        help='UUID de l\'organisation'
    )
    parser.add_argument(
        '--company-id',
        help='UUID de l\'entreprise (optionnel, pour bot spécifique)'
    )
    parser.add_argument(
        '--description',
        default='Bot facturation chantiers',
        help='Description du bot'
    )
    parser.add_argument(
        '--skip-db',
        action='store_true',
        help='Ne pas créer d\'entrée en base (mode test)'
    )
    
    args = parser.parse_args()
    
    env_label = "🧪 TEST" if args.env == 'test' else "🚀 PRODUCTION"
    print(f"\n{env_label} - Initialisation du bot Telegram\n")
    
    # 1. Vérifier l'environnement
    print("1️⃣  Vérification de la configuration...")
    config = check_environment(args)
    
    token = config['token']
    base_url = config['api_url']
    supabase_url = config['supabase_url']
    supabase_key = config['supabase_key']
    
    print(f"✅ Configuration OK ({args.env.upper()})")
    print(f"   API URL: {base_url}")
    print(f"   Supabase: {supabase_url[:30]}...\n")
    
    # 2. Vérifier le token
    print("2️⃣  Vérification du token Telegram...")
    bot_info = await verify_bot_token(token)
    if not bot_info:
        sys.exit(1)
    
    print(f"✅ Bot trouvé: @{bot_info['username']} (ID: {bot_info['id']})\n")
    
    # 3. Générer les secrets
    print("3️⃣  Génération des secrets...")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    webhook_secret = secrets.token_urlsafe(32)
    webhook_path = f"/api/v1/{args.org_id}/telegram/webhook/{token_hash[:16]}"
    webhook_url = f"{base_url.rstrip('/')}{webhook_path}"
    
    print("✅ Secrets générés\n")
    
    # 4. Configurer le webhook Telegram
    print("4️⃣  Configuration du webhook Telegram...")
    webhook_configured = await configure_webhook(token, webhook_url, webhook_secret)
    if not webhook_configured:
        print("\n⚠️  La configuration du webhook a échoué.")
        response = input("Voulez-vous continuer quand même? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print()
    
    # 5. Créer en base de données
    if not args.skip_db:
        print("5️⃣  Création en base de données...")
        supabase = create_client(supabase_url, supabase_key)
        
        bot_record = create_bot_in_database(
            supabase=supabase,
            org_id=args.org_id,
            company_id=args.company_id,
            token_hash=token_hash,
            bot_info=bot_info,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            description=args.description
        )
        
        if not bot_record:
            sys.exit(1)
        
        print(f"✅ Bot créé en base (ID: {bot_record['id']})\n")
    else:
        print("5️⃣  Mode test: Pas de création en base\n")
        bot_record = {'id': 'TEST-MODE'}
    
    # 6. Afficher le résumé
    print("=" * 60)
    print(f"✨ Configuration terminée! ({args.env.upper()})")
    print("=" * 60)
    print(f"\n🤖 Bot: @{bot_info['username']}")
    print(f"🆔 ID: {bot_info['id']}")
    print(f"📁 Organisation: {args.org_id}")
    if args.company_id:
        print(f"🏢 Entreprise: {args.company_id}")
    print(f"\n🔗 Webhook URL:")
    print(f"   {webhook_url}")
    print(f"\n📋 Pour utiliser le bot:")
    print(f"   1. Envoyez un message à @{bot_info['username']} sur Telegram")
    print(f"   2. Ou cliquez: https://t.me/{bot_info['username']}")
    print(f"\n💡 Commandes disponibles:")
    print(f"   /start - Démarrer le bot")
    print(f"   Envoyer photo/PDF - Créer une facture")
    print("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
