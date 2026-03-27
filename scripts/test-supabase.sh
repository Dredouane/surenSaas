#!/bin/bash
# Script pour tester la connexion Supabase

cd /home/redouane/dev/AI-ERA/surenSaas/surenSaasBack

echo "🧪 Test de connexion Supabase"
echo "=============================="
echo ""

# Charger les variables d'environnement
if [ -f ../.env.test ]; then
    echo "📋 Chargement de ../.env.test"
    set -a
    source ../.env.test
    set +a
elif [ -f .env.test ]; then
    echo "📋 Chargement de .env.test"
    set -a
    source .env.test
    set +a
elif [ -f .env ]; then
    echo "📋 Chargement de .env"
    set -a
    source .env
    set +a
else
    echo "⚠️  Aucun fichier .env trouvé"
fi

echo ""
echo "Variables d'environnement:"
echo "  SUPABASE_URL: ${SUPABASE_URL:0:40}..."
echo "  SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY:+✅ défini}"
echo ""

# Activer le venv
source venv/bin/activate

# Lancer le test
echo "🚀 Lancement du test..."
echo "=============================="
python tests/test_supabase_connection.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ Test réussi!"
else
    echo "❌ Test échoué (code: $exit_code)"
fi

exit $exit_code
