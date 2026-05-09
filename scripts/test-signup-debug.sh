#!/bin/bash
# Script pour lancer le test de debug signup

cd /home/redouane/dev/AI-ERA/surenSaas/surenSaasBack

# Charger les variables d'environnement
set -a
source ../.env.test 2>/dev/null || source .env.test 2>/dev/null || true
set +a

# Exporter les variables d'environnement
export SUPABASE_URL=${SUPABASE_URL}
export SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
export JWT_SECRET=${JWT_SECRET}

echo "🧪 Test de debugging signup"
echo "=========================="
echo ""

source venv/bin/activate
python tests/test_signup_debug.py
