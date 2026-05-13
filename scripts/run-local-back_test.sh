#!/bin/bash
# Lancer le backend TEST en local
# Tue les processus existants et charge la config depuis .env.test
#
# Usage:
#   ./scripts/run-local-back_test.sh              # Par défaut : vrai API Telegram (https://api.telegram.org)
#   ./scripts/run-local-back_test.sh --tg-mock    # Utilise tg-mock (http://localhost:8081)
#   ./scripts/run-local-back_test.sh --use-tg-mock

set -e

# === PARSE ARGS ===
USE_TG_MOCK=false
for arg in "$@"; do
    case "$arg" in
        --tg-mock|--use-tg-mock)
            USE_TG_MOCK=true
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
cd "$SCRIPT_DIR"

echo "=========================================="
echo "🧹 Nettoyage des processus existants..."
echo "=========================================="

# Tuer les mock_telegram en cours (sur le port 8081 uniquement)
if lsof -ti:8081 > /dev/null 2>&1; then
    echo "  → Arrêt de mock_telegram sur port 8081..."
    lsof -ti:8081 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Tuer uvicorn sur le port 8080
if lsof -ti:8080 > /dev/null 2>&1; then
    echo "  → Arrêt du backend sur port 8080..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    sleep 2
fi
# Force kill si le port est toujours occupé
if lsof -ti:8080 > /dev/null 2>&1; then
    echo "  → Force kill sur 8080..."
    fuser -k 8080/tcp 2>/dev/null || true
    sleep 2
fi

# Nettoyage des processus uvicorn orphelins (reload workers)
for pid in $(pgrep -f "uvicorn app.main:app" 2>/dev/null); do
    kill "$pid" 2>/dev/null || true
done
sleep 1

echo "✅ Port 8080 libre — backend prêt à démarrer"

echo "✅ Ports nettoyés"
echo ""

echo "📋 Chargement de la configuration TEST..."

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

# Activer le venv et installer les dépendances si elles ne sont pas déjà présentes
source venv/bin/activate

# Use the pip from the activated venv to install necessary packages
# Check if langgraph_checkpoint_postgres is installed, if not, install it
if ! $VIRTUAL_ENV/bin/pip show langgraph-checkpoint-postgres > /dev/null 2>&1; then
    echo "Installing langgraph-checkpoint-postgres..."
    $VIRTUAL_ENV/bin/pip install langgraph-checkpoint-postgres>=3.0.5
fi

# Check if psycopg is installed, if not, install it
if ! $VIRTUAL_ENV/bin/pip show psycopg > /dev/null 2>&1; then
    echo "Installing psycopg..."
    $VIRTUAL_ENV/bin/pip install psycopg[binary,pool]>=3.1.0
fi

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
# Utilise SUREN_GEMINI_API_KEY du .bashrc
if [ -z "$SUREN_GEMINI_API_KEY" ]; then
    SUREN_GEMINI_API_KEY=$(grep -oP 'export SUREN_GEMINI_API_KEY="\K[^"]+' ~/.bashrc 2>/dev/null)
fi
if [ -z "$SUREN_GEMINI_API_KEY" ]; then
    echo "⚠️  SUREN_GEMINI_API_KEY non trouvée! Vérifie ton ~/.bashrc"
fi
export GOOGLE_API_KEY="${SUREN_GEMINI_API_KEY}"
echo "  Gemini API Key: $([ -n "$GOOGLE_API_KEY" ] && echo '✅ définie' || echo '❌ MANQUANTE')"

# Variables Telegram
export TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN=${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN:-}
export TELEGRAM_CONSTRUCTION_BOT_TOKEN=${TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN}
export TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN="${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN:-}"
# Ajout explicite du mapping pour le username
export TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME=${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_USERNAME:-}
export TELEGRAM_CONSTRUCTION_BOT_USERNAME=${TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME}

# LLM Provider (gemini ou deepseek — laisser l'env décider)
export LLM_PROVIDER="${LLM_PROVIDER}"
# DeepSeek API Key (nécessaire si LLM_PROVIDER=deepseek)
export SUREN_DEEP_SEEK_API_KEY="${SUREN_DEEP_SEEK_API_KEY:-${NEMO_CLAW_DEEP_SEEK_API_KEY:-}}"

# Point vers l'API Telegram (tg-mock si demandé, sinon vrai Telegram)
if [ "$USE_TG_MOCK" = true ]; then
    echo "  → Mode tg-mock : TELEGRAM_API_URL=http://localhost:8081"
    export TELEGRAM_API_URL="http://localhost:8081"
else
    echo "  → Mode réel : TELEGRAM_API_URL=https://api.telegram.org (défaut)"
fi

echo "✅ Variables d'environnement exportées"


echo ""
echo "=========================================="
echo "🚀 BACKEND TEST - Local Development"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Supabase URL: ${SUPABASE_URL:0:40}..."
echo "  Service Key: $([ -n "$TEST_SUPABASE_SERVICE_KEY" ] && echo '✅ défini' || echo '❌ MANQUANT')"
echo "  JWT Secret: $([ -n "$TEST_JWT_SECRET" ] && echo '✅ défini (depuis ~/.bashrc)' || echo '⚠️  Valeur par défaut (non sécurisé)')"
echo "  Cloudflare R2: $([ -n "$SUREN_GED_CLOUDFLARE_TOKEN" ] && echo '✅ configuré' || echo '❌ NON DÉFINI - stockage fichiers désactivé')"
R2_BUCKET_INFO="R2 Bucket: ${SUREN_GED_CLOUDFLARE_BUCKET_NAME:-'❌ NON DÉFINI'}"
echo "  ${R2_BUCKET_INFO}"
echo ""
echo "URL: http://localhost:8080"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

# Lancer uvicorn — reload désactivé en mode tg-mock pour éviter
# les interruptions de workers pendant les tests E2E
if [ "$USE_TG_MOCK" = true ]; then
    echo "  → Mode tests E2E : uvicorn sans reload (workers=2)"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2
else
    echo "  → Mode dev : uvicorn avec reload (workers=8)"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload --workers 8
fi
