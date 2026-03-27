#!/bin/bash
# Script pour configurer le bot Telegram

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Charger l'environnement
if [ -f .env.test ]; then
    source .env.test
fi

if [ -z "$TEST_SUPABASE_SERVICE_KEY" ]; then
    echo "❌ TEST_SUPABASE_SERVICE_KEY non définie"
    echo "export TEST_SUPABASE_SERVICE_KEY='eyJ...'"
    exit 1
fi

# Demander le token du bot
echo "🤖 Configuration du Bot Telegram"
echo "================================"
echo ""
echo "1. Créez un bot avec @BotFather sur Telegram"
echo "2. Récupérez le token (format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)"
echo ""
read -p "Entrez le token du bot Telegram: " BOT_TOKEN
read -p "Nom du bot (ex: Suren Construction): " BOT_NAME
read -p "Slug de l'organisation (default: REDACTED_ORG_SLUG): " ORG_SLUG

ORG_SLUG=${ORG_SLUG:-REDACTED_ORG_SLUG}

# Vérifier que org_id existe
echo ""
echo "📋 Vérification de l'organisation..."

python3 << EOF
import os
from supabase import create_client

SUPABASE_URL = "https://REDACTED.supabase.co"
SUPABASE_KEY = os.getenv("TEST_SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Récupérer l'org_id
result = supabase.table('organizations') \
    .select('id') \
    .eq('slug', '$ORG_SLUG') \
    .single() \
    .execute()

if result.data:
    org_id = result.data['id']
    print(f"✅ Organisation trouvée: {org_id}")
    
    # Créer le bot
    bot_data = {
        'bot_name': '$BOT_NAME',
        'bot_token': '$BOT_TOKEN',
        'org_id': org_id,
        'is_active': True,
        'welcome_message': 'Bienvenue sur SurenSaaS ! Envoyez vos factures ici.',
        'allowed_roles': ['conducteur', 'gerant']
    }
    
    # Vérifier si un bot existe déjà
    existing = supabase.table('telegram_bots') \
        .select('bot_id') \
        .eq('org_id', org_id) \
        .execute()
    
    if existing.data:
        print(f"⚠️  Bot existe déjà, mise à jour...")
        supabase.table('telegram_bots') \
            .update(bot_data) \
            .eq('org_id', org_id) \
            .execute()
    else:
        print(f"📝 Création du bot...")
        supabase.table('telegram_bots') \
            .insert(bot_data) \
            .execute()
    
    print(f"✅ Bot configuré avec succès!")
else:
    print(f"❌ Organisation '$ORG_SLUG' non trouvée")
    exit(1)
EOF

echo ""
echo "🎉 Configuration terminée!"
echo ""
echo "Le bot est maintenant disponible dans l'administration."
