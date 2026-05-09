#!/bin/bash
# Setup pour les tests E2E
# 
# Ce script prépare la base de données pour les tests:
# 1. Crée les emails de test dans pre_authorized_emails
# 2. Nettoie les anciens users de test
#
# Usage:
#   ./scripts/setup-e2e-tests.sh [local|test|prod]

set -e

ENV=${1:-local}
echo "🧪 Setup E2E Tests - Environment: $ENV"
echo "======================================"

# Charger les variables d'environnement
cd /home/redouane/dev/AI-ERA/surenSaas

if [ "$ENV" = "local" ]; then
    set -a
    source .env.test
    set +a
elif [ "$ENV" = "test" ]; then
    # Charger les variables de test GCP
    set -a
    source .env.test 2>/dev/null || true
    set +a
fi

echo ""
echo "📋 Préparation de la base de données..."
echo ""

cd surenSaasBack
source venv/bin/activate

# Exporter les variables d'environnement
export SUPABASE_URL=${SUPABASE_URL}
export SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
export JWT_SECRET=${JWT_SECRET}

python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '.')

from app.api.auth import get_supabase
from datetime import datetime

supabase = get_supabase()
org_id = "REDACTEDORG"

print("🔧 Configuration des données de test...")
print("")

# 1. Nettoyer les anciens tests (plus de 24h)
print("1️⃣  Nettoyage des anciens tests...")
try:
    old_tests = supabase.table('pre_authorized_emails').select('id, email').like('email', 'test-e2e%').execute()
    if old_tests.data:
        for item in old_tests.data:
            email = item['email']
            # Supprimer de users
            supabase.table('users').delete().eq('email', email).execute()
            # Supprimer de pre_authorized
            supabase.table('pre_authorized_emails').delete().eq('email', email).execute()
            print(f"   🗑️  Nettoyé: {email}")
    print("   ✅ Cleanup terminé")
except Exception as e:
    print(f"   ⚠️  Erreur cleanup: {e}")

print("")

# 2. Créer l'email de test admin
print("2️⃣  Vérification email admin...")
admin_email = "test-e2e-admin@suren.com"
admin_exists = supabase.table('pre_authorized_emails').select('*').eq('email', admin_email).execute()

if not admin_exists.data:
    supabase.table('pre_authorized_emails').insert({
        'email': admin_email,
        'org_id': org_id,
        'role': 'admin',
        'is_active': True
    }).execute()
    print(f"   ✅ Admin créé: {admin_email}")
else:
    print(f"   ✅ Admin existe déjà: {admin_email}")

print("")

# 3. Créer l'email de test user
print("3️⃣  Vérification email user...")
user_email = "test-e2e-user@suren.com"
user_exists = supabase.table('pre_authorized_emails').select('*').eq('email', user_email).execute()

if not user_exists.data:
    supabase.table('pre_authorized_emails').insert({
        'email': user_email,
        'org_id': org_id,
        'role': 'user',
        'is_active': True
    }).execute()
    print(f"   ✅ User créé: {user_email}")
else:
    print(f"   ✅ User existe déjà: {user_email}")

print("")
print("✅ Setup E2E terminé!")
print("")
print("Emails de test disponibles:")
print(f"   Admin: {admin_email}")
print(f"   User:  {user_email}")
PYTHON_SCRIPT

echo ""
echo "🚀 Vous pouvez maintenant lancer les tests:"
echo "   npm run test:e2e:local"
echo ""
