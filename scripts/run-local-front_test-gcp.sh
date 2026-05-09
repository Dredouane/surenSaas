#!/bin/bash
# Lancer le frontend TEST en local avec backend GCP (déployé)
# Tue les processus existants et crée .env.local dynamiquement depuis ~/.bashrc

cd /home/redouane/dev/AI-ERA/surenSaas

echo "=========================================="
echo "🧹 Nettoyage des processus existants..."
echo "=========================================="

# Tuer Next.js sur le port 3000
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "  → Arrêt du frontend sur port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo "✅ Ports nettoyés"
echo ""

echo "📋 Chargement de la configuration..."

# Charger .env.test (pour les variables d'organisation)
if [ ! -f .env.test ]; then
    echo "❌ Fichier .env.test non trouvé!"
    exit 1
fi

# Lire les variables depuis .env.test
while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    key=$(echo "$key" | xargs)
    export "$key=$value"
done < .env.test

# Charger les URLs GCP depuis ~/.bashrc
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Vérifier que SUREN_TEST_API_BASE_URL est défini
if [ -z "$SUREN_TEST_API_BASE_URL" ]; then
    echo "❌ SUREN_TEST_API_BASE_URL non défini dans ~/.bashrc!"
    echo "   Ajoutez dans ~/.bashrc:"
    echo "   export SUREN_TEST_API_BASE_URL=\"https://test-surensaas-back-xxx.run.app\""
    exit 1
fi

echo "✅ Configuration chargée"
echo "   Backend GCP: $SUREN_TEST_API_BASE_URL"
echo ""

# Créer .env.local pour le backend GCP
cd surenSaasFront

echo "📝 Création de .env.local pour backend GCP..."

cat > .env.local << EOF
# Auto-généré par run-local-front_test-gcp.sh
# Backend GCP (déployé)
API_URL=${SUREN_TEST_API_BASE_URL}
NEXT_PUBLIC_API_URL=${SUREN_TEST_API_BASE_URL}

# Organisation (depuis .env.test)
NEXT_PUBLIC_ORG_ID=${NEXT_PUBLIC_ORG_ID}
NEXT_PUBLIC_ORG_SLUG=${NEXT_PUBLIC_ORG_SLUG}


# Mode développement
NODE_ENV=development
EOF

echo "✅ .env.local créé avec backend GCP"
echo ""

# Nettoyer le cache Next.js
echo "🧹 Nettoyage du cache Next.js..."
rm -rf .next

echo ""
echo "=========================================="
echo "🌐 FRONTEND TEST - Mode GCP Connecté"
echo "=========================================="
echo ""
echo "URLs:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  ${SUREN_TEST_API_BASE_URL} (GCP)"
echo ""
echo "Configuration:"
echo "  NEXT_PUBLIC_ORG_SLUG: ${NEXT_PUBLIC_ORG_SLUG}"
echo "  NEXT_PUBLIC_ORG_ID: ${NEXT_PUBLIC_ORG_ID}"
echo ""
echo "Page de login:"
echo "  http://localhost:3000/${NEXT_PUBLIC_ORG_SLUG}/login"
echo ""
echo "⚠️  Attention: Les cookies cross-origin peuvent ne pas fonctionner"
echo "   entre localhost et GCP. Pour un test complet, utilisez:"
echo "   ./scripts/run-local_test.sh (local complet)"
echo ""
echo "💡 Appuyez sur Ctrl+C pour arrêter"
echo ""

# Lancer Next.js
exec npm run dev
