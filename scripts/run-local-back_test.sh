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

# Fonction pour évaluer les variables
eval_env() {
    local content
    content=$(cat .env.test)
    
    # Remplacer les références de variables
    while [[ "$content" =~ (\$\{[A-Za-z0-9_]+\}) ]]; do
        local var_ref="${BASH_REMATCH[1]}"
        local var_name="${var_ref:2:-1}"
        local var_value="${!var_name:-}"
        content="${content//$var_ref/$var_value}"
    done
    
    echo "$content"
}

# Lire les variables depuis .env.test avec évaluation
while IFS='=' read -r key value; do
    # Ignorer les lignes vides et les commentaires
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    
    # Supprimer les espaces
    key=$(echo "$key" | xargs)
    
    # Exporter la variable
    export "$key=$value"
done < <(eval_env)

# Charger les secrets depuis ~/.bashrc
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

echo "✅ Variables chargées depuis .env.test et ~/.bashrc"

cd surenSaasBack

# Exporter les variables d'environnement pour que config.py les lise
export ENVIRONMENT=test
export SUPABASE_URL=${SUPABASE_URL}
export SUPABASE_SERVICE_KEY=${TEST_SUPABASE_SERVICE_KEY:-}
export JWT_SECRET=${TEST_JWT_SECRET:-local-dev-jwt-secret-not-for-production}
export ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:3000}
export SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT=${SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT:-}
export SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID=${SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID:-}
export SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY=${SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY:-}
export SUREN_GED_CLOUDFLARE_TOKEN=${SUREN_GED_CLOUDFLARE_TOKEN:-}
export SUREN_GED_CLOUDFLARE_BUCKET_NAME=${SUREN_GED_CLOUDFLARE_BUCKET_NAME:-}

# Variables GCP pour Vertex AI
export GCP_PROJECT_ID=${GCP_PROJECT_ID:-suren-saas}
export GCP_REGION=${GCP_REGION:-europe-west1}
export VERTEX_AI_PROJECT_ID=${VERTEX_AI_PROJECT_ID:-${GCP_PROJECT_ID}}
export VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-${GCP_REGION}}

# Gemini API Key (nécessaire pour les nouveaux agents)
export TEST_GOOGLE_GEMINI_CREDENTIALS_B64=${TEST_GOOGLE_GEMINI_CREDENTIALS_B64:-}
export GOOGLE_GEMINI_CREDENTIALS_B64=${TEST_GOOGLE_GEMINI_CREDENTIALS_B64}

# Variables Telegram
export TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN=${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN:-}
export TELEGRAM_CONSTRUCTION_BOT_TOKEN=${TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN}
export TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN="REDACTED_BOT_TOKEN"
# Ajout explicite du mapping pour le username
export TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME=${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_USERNAME:-}
export TELEGRAM_CONSTRUCTION_BOT_USERNAME=${TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME}

echo "✅ Variables d'environnement exportées"

# Activer le venv
source venv/bin/activate

echo ""
echo "=========================================="
echo "🚀 BACKEND TEST - Local Development"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Supabase URL: ${SUPABASE_URL:0:40}..."
echo "  Service Key: $([ -n "$TEST_SUPABASE_SERVICE_KEY" ] && echo '✅ défini' || echo '❌ MANQUANT')"
echo "  JWT Secret: $([ -n "$TEST_JWT_SECRET" ] && echo '✅ défini (depuis ~/.bashrc)' || echo '⚠️  Valeur par défaut (non sécurisé)')"
echo "  Cloudflare R2: $([ -n "$SUREN_GED_CLOUDFLARE_TOKEN" ] && echo '✅ configuré' || echo '❌ MANQUANT - stockage fichiers désactivé')
  R2 Bucket: ${SUREN_GED_CLOUDFLARE_BUCKET_NAME:-❌ NON DÉFINI}"
echo ""
echo "URL: http://localhost:8080"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

# Lancer uvicorn avec workers pour le parallélisme
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload --workers 8
