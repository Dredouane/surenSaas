#!/bin/bash
# Lancer le backend TEST en local
# Tue les processus existants et charge la config depuis .env.test

set -e

cd /home/redouane/dev/AI-ERA/surenSaas

echo "=========================================="
echo "🧹 Nettoyage des processus existants..."
echo "=========================================="

# Tuer uvicorn sur le port 8080
if lsof -ti:8080 > /dev/null 2>&1; then
    echo "  → Arrêt du backend sur port 8080..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo "✅ Ports nettoyés"
echo ""

echo "📋 Chargement de la configuration TEST..."

# Charger le fichier .env.test
if [ ! -f .env.test ]; then
    echo "❌ Fichier .env.test non trouvé!"
    exit 1
fi

# Lire les variables depuis .env.test
while IFS='=' read -r key value; do
    # Ignorer les lignes vides et les commentaires
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    
    # Supprimer les espaces
    key=$(echo "$key" | xargs)
    
    # Exporter la variable
    export "$key=$value"
done < .env.test

# Charger les secrets depuis ~/.bashrc
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

echo "✅ Variables chargées depuis .env.test et ~/.bashrc"

cd surenSaasBack

# Créer un fichier .env temporaire avec les valeurs réelles
# Utiliser TEST_JWT_SECRET depuis .bashrc ou une valeur par défaut
JWT_SECRET=${TEST_JWT_SECRET:-local-dev-jwt-secret-not-for-production}
SUPABASE_SERVICE_KEY=${TEST_SUPABASE_SERVICE_KEY:-}

cat > .env << EOF
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
JWT_SECRET=${JWT_SECRET}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:3000}
ENVIRONMENT=test
EOF

echo "📝 Fichier .env créé"

# Activer le venv
source venv/bin/activate

echo ""
echo "=========================================="
echo "🚀 BACKEND TEST - Local Development"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Supabase URL: ${SUPABASE_URL:0:40}..."
echo "  Service Key: $([ -n "$SUPABASE_SERVICE_KEY" ] && echo '✅ défini' || echo '❌ MANQUANT')"
echo "  JWT Secret: $([ -n "$TEST_JWT_SECRET" ] && echo '✅ défini (depuis ~/.bashrc)' || echo '⚠️  Valeur par défaut (non sécurisé)')"
echo ""
echo "URL: http://localhost:8080"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

# Lancer uvicorn avec reload
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
