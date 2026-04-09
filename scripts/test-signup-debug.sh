#!/bin/bash
# Script pour lancer le test de debug signup

cd /home/redouane/dev/AI-ERA/surenSaas/surenSaasBack

# Charger les variables d'environnement
set -a
source ../.env.test 2>/dev/null || source .env.test 2>/dev/null || true
set +a

# Créer le fichier .env pour pydantic
cat > .env << EOF
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
JWT_SECRET=${JWT_SECRET}
EOF

echo "🧪 Test de debugging signup"
echo "=========================="
echo ""

source venv/bin/activate
python tests/test_signup_debug.py
