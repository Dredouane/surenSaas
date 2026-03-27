#!/bin/bash
# Script pour lancer la suite de tests complète

cd /home/redouane/dev/AI-ERA/surenSaas/surenSaasBack

echo "🧪 Lancement de la suite de tests complète SurenSaaS"
echo "===================================================="
echo ""

# 1. Variables d'environnement système (priorité maximale - pour les secrets)
# Ces variables sont définies directement sur la machine avec export
if [ -n "$SUREN_TEST_LOGIN" ] || [ -n "$SUREN_TEST_PASSWORD" ]; then
    echo "📋 Variables d'environnement système détectées"
fi

# 2. Charger le fichier .env.test.local (secrets locaux, non versionné)
if [ -f ../.env.test.local ]; then
    echo "📋 Chargement de ../.env.test.local..."
    set -a
    source ../.env.test.local
    set +a
elif [ -f .env.test.local ]; then
    echo "📋 Chargement de .env.test.local..."
    set -a
    source .env.test.local
    set +a
fi

# 3. Charger le fichier .env.test (configuration partagée)
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
else
    echo "⚠️  Aucun fichier .env.test trouvé"
fi

# Créer le fichier .env pour pydantic avec TOUTES les variables
cat > .env << EOF
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_SERVICE_KEY=${TEST_SUPABASE_SERVICE_KEY}
JWT_SECRET=${JWT_SECRET}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:3000}
ENVIRONMENT=test
SUREN_TEST_LOGIN=${SUREN_TEST_LOGIN}
SUREN_TEST_PASSWORD=${SUREN_TEST_PASSWORD}
EOF

# Vérifier les credentials de test
if [ -n "$SUREN_TEST_LOGIN" ] && [ -n "$SUREN_TEST_PASSWORD" ]; then
    echo "✅ Credentials de test configurés: $SUREN_TEST_LOGIN"
else
    echo "⚠️  Credentials de test non définis (SUREN_TEST_LOGIN / SUREN_TEST_PASSWORD)"
    echo ""
    echo "Pour configurer les credentials de test, utilisez l'une des méthodes :"
    echo ""
    echo "1. Variables d'environnement (recommandé pour CI/CD) :"
    echo "   export SUREN_TEST_LOGIN='votre-email@test.com'"
    echo "   export SUREN_TEST_PASSWORD='votre-mot-de-passe'"
    echo ""
    echo "2. Fichier .env.test.local (recommandé pour le développement local) :"
    echo "   Créez un fichier .env.test.local à la racine avec :"
    echo "   SUREN_TEST_LOGIN=votre-email@test.com"
    echo "   SUREN_TEST_PASSWORD=votre-mot-de-passe"
    echo ""
    echo "   Les tests API nécessitant l'authentification seront ignorés"
fi

echo "✅ Configuration chargée"
echo ""

# Activer le venv
source venv/bin/activate

# Lancer les tests existants
echo "🧪 Tests scénarios complets..."
python tests/test_full_scenarios.py
exit_code=$?

# Lancer les tests des nouvelles routes API
echo ""
echo "🧪 Tests nouvelles routes API..."
python tests/test_api_routes.py
api_exit_code=$?

if [ $api_exit_code -ne 0 ]; then
    exit_code=$api_exit_code
fi

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ Suite de tests terminée avec succès"
else
    echo "❌ Certains tests ont échoué"
fi

exit $exit_code
