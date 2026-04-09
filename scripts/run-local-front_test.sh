#!/bin/bash
# Lancer le frontend TEST en local avec backend LOCAL (localhost:8080)
# Tue les processus existants et crée .env.local dynamiquement

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

echo "📋 Chargement de la configuration depuis .env.test..."

# Charger .env.test
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

echo "✅ Configuration chargée"
echo ""

# Créer .env.local pour le backend local
cd surenSaasFront

echo "📝 Création de .env.local pour backend LOCAL..."

cat > .env.local << EOF
# Auto-généré par run-local-front_test.sh
# Backend LOCAL (localhost:8080)
API_URL=http://localhost:8080
NEXT_PUBLIC_API_URL=http://localhost:8080

# Organisation (depuis .env.test)
NEXT_PUBLIC_ORG_ID=${NEXT_PUBLIC_ORG_ID}
NEXT_PUBLIC_ORG_SLUG=${NEXT_PUBLIC_ORG_SLUG}

# Supabase (depuis .env.test)
NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}

# Mode développement
NODE_ENV=development
EOF

echo "✅ .env.local créé avec backend LOCAL"
echo ""

# Nettoyer le cache Next.js
echo "🧹 Nettoyage du cache Next.js..."
rm -rf .next

echo ""
echo "=========================================="
echo "🚀 FRONTEND TEST - Mode LOCAL"
echo "=========================================="
echo ""
echo "URLs:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8080 (LOCAL)"
echo ""
echo "Configuration:"
echo "  NEXT_PUBLIC_ORG_SLUG: ${NEXT_PUBLIC_ORG_SLUG}"
echo "  NEXT_PUBLIC_ORG_ID: ${NEXT_PUBLIC_ORG_ID}"
echo ""
echo "Page de login:"
echo "  http://localhost:3000/${NEXT_PUBLIC_ORG_SLUG}/login"
echo ""
echo "💡 Appuyez sur Ctrl+C pour arrêter"
echo ""

# Lancer Next.js
exec npm run dev
