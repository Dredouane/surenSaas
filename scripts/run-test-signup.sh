#!/bin/bash
# Script pour lancer UNIQUEMENT le test de signup workflow
# Utile pour debugger le signup sans attendre tous les autres tests

cd /home/redouane/dev/AI-ERA/surenSaas/surenSaasBack

echo "🧪 Test WORKFLOW SIGNUP UNIQUEMENT"
echo "==================================="
echo ""

# Charger les variables d'environnement
if [ -f ../.env.test ]; then
    echo "📋 Chargement de ../.env.test..."
    set -a
    source ../.env.test
    set +a
elif [ -f .env.test ]; then
    echo "📋 Chargement de .env.test..."
    set -a
    source .env.test
    set +a
fi

# Exporter les variables d'environnement pour que config.py les lise
export ENVIRONMENT=test
export SUPABASE_URL=${SUPABASE_URL}
export SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
export JWT_SECRET=${JWT_SECRET}
export ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:3000}

echo "✅ Variables d'environnement exportées"
echo ""

# Activer le venv
source venv/bin/activate

# Lancer SEULEMENT le test de signup
echo "🚀 Lancement du test signup workflow..."
echo ""
python3 -c "
import sys
sys.path.insert(0, '.')

from tests.test_full_scenarios import TestRunner, test_signup_workflow, Colors

runner = TestRunner()
if not runner.setup_db():
    print('❌ Impossible de se connecter à la DB')
    sys.exit(1)

result = test_signup_workflow(runner)

if result:
    print(f'\n{Colors.GREEN}✅ TEST SIGNUP PASSÉ!{Colors.RESET}\n')
    sys.exit(0)
else:
    print(f'\n{Colors.RED}❌ TEST SIGNUP ÉCHOUÉ{Colors.RESET}\n')
    sys.exit(1)
"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ Test signup réussi!"
else
    echo "❌ Test signup échoué"
fi

exit $exit_code
