#!/bin/bash
# Script de déploiement du BACKEND TEST sur GCP Cloud Run

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🚀 DEPLOIEMENT BACKEND TEST${NC}"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Charger l'environnement TEST (sans secrets)
if [ ! -f .env.test ]; then
    echo -e "${RED}❌ Erreur: .env.test non trouvé${NC}"
    echo "Créez-le à partir du template: cp .env.test.example .env.test"
    exit 1
fi

echo -e "${BLUE}📋 Chargement de .env.test...${NC}"
set -a
source .env.test
set +a

# Vérifier les variables du .bashrc
echo ""
echo -e "${YELLOW}🔐 Vérification des secrets dans ~/.bashrc...${NC}"
MISSING_VARS=()

if [ -z "$TEST_SUPABASE_SERVICE_KEY" ]; then
    MISSING_VARS+=("TEST_SUPABASE_SERVICE_KEY")
fi

if [ -z "$TEST_JWT_SECRET" ]; then
    MISSING_VARS+=("TEST_JWT_SECRET")
fi

# Telegram Bot
HAS_TELEGRAM=false
if [ ! -z "$SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN" ]; then
    HAS_TELEGRAM=true
fi

# Gemini est optionnel (désactivé temporairement)
# Utilise SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 depuis .bashrc (partagé test/prod)
HAS_GEMINI=false
if [ ! -z "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64" ]; then
    HAS_GEMINI=true
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Variables manquantes dans ~/.bashrc:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo -e "${BLUE}Pour les configurer:${NC}"
    echo "  ./scripts/setup-local-env.sh"
    exit 1
fi

echo -e "${GREEN}✅ Secrets trouvés dans ~/.bashrc${NC}"
if [ "$HAS_TELEGRAM" = true ]; then
    echo -e "${GREEN}✅ SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN trouvé (Bot Telegram activé)${NC}"
    if [ -z "$SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME" ]; then
        echo -e "${YELLOW}⚠️  SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME non défini (utilisation du nom par défaut)${NC}"
    else
        echo -e "${GREEN}✅ SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME trouvé: $SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN non défini (Bot Telegram désactivé)${NC}"
fi
if [ "$HAS_GEMINI" = true ]; then
    echo -e "${GREEN}✅ SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 trouvé (Gemini activé)${NC}"
else
    echo -e "${YELLOW}⚠️  SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 non défini (Gemini désactivé)${NC}"
fi

# Vérifier les variables GCP
if [ -z "$GCP_PROJECT_ID" ] || [ -z "$TEST_BACK_SERVICE_NAME" ]; then
    echo -e "${RED}❌ Erreur: Variables GCP manquantes dans .env.test${NC}"
    exit 1
fi

echo ""

# Fonction pour créer/mettre à jour un secret GCP
create_or_update_secret() {
    local name=$1
    local value=$2
    
    if gcloud secrets describe $name --project=$GCP_PROJECT_ID > /dev/null 2>&1; then
        echo -e "${YELLOW}  Mise à jour du secret: $name${NC}"
        echo -n "$value" | gcloud secrets versions add $name --data-file=- --project=$GCP_PROJECT_ID > /dev/null 2>&1
    else
        echo -e "${BLUE}  Création du secret: $name${NC}"
        echo -n "$value" | gcloud secrets create $name --data-file=- --project=$GCP_PROJECT_ID > /dev/null 2>&1
    fi
    echo -e "${GREEN}  ✅ $name${NC}"
}

# Créer/mettre à jour les secrets GCP
echo -e "${YELLOW}🔐 Configuration des secrets GCP...${NC}"
create_or_update_secret "supabase-url" "$SUPABASE_URL"
create_or_update_secret "test-supabase-service-key" "$TEST_SUPABASE_SERVICE_KEY"
create_or_update_secret "test-jwt-secret" "$TEST_JWT_SECRET"

# Telegram Bot (optionnel)
# Note: Le token et le username sont des secrets
if [ "$HAS_TELEGRAM" = true ]; then
    create_or_update_secret "test-telegram-bot-token" "$SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN"
    BOT_USERNAME="${SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME:-suren_construction_test_bot}"
    create_or_update_secret "test-telegram-bot-username" "$BOT_USERNAME"
fi

# Gemini (optionnel)
if [ "$HAS_GEMINI" = true ]; then
    create_or_update_secret "test-google-gemini-credentials" "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64"
fi

echo ""

# Déploiement
echo -e "${YELLOW}🚀 Déploiement Backend TEST...${NC}"
cd surenSaasBack

# Calculer les origines CORS
echo -e "${BLUE}🔍 Configuration CORS...${NC}"
CORS_ORIGINS="http://localhost:3000"

# Vérifier si le frontend est accessible (ping)
FRONT_URL=$(gcloud run services describe $TEST_FRONT_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null || echo "")

if [ ! -z "$FRONT_URL" ]; then
    # Ping le frontend pour vérifier s'il répond
    if curl -s --max-time 5 "$FRONT_URL/health" > /dev/null 2>&1 || curl -s --max-time 5 "$FRONT_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ Frontend accessible: $FRONT_URL${NC}"
        CORS_ORIGINS="$CORS_ORIGINS,$FRONT_URL"
    else
        echo -e "${YELLOW}  ⚠️  Frontend ne répond pas, utilisation de l'URL par défaut: $FRONT_URL${NC}"
        CORS_ORIGINS="$CORS_ORIGINS,$FRONT_URL"
    fi
else
    echo -e "${YELLOW}  ⚠️  Frontend non déployé, CORS limité à localhost${NC}"
fi

# Créer un fichier temporaire pour les variables d'environnement
ENV_FILE=$(mktemp)
trap "rm -f $ENV_FILE" EXIT

cat > $ENV_FILE << EOF
ALLOWED_ORIGINS: "$CORS_ORIGINS"
ENVIRONMENT: "test"
ORG_ID: "$NEXT_PUBLIC_ORG_ID"
DEBUG: "true"
EOF

# Préparer les secrets
SECRETS="SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=test-supabase-service-key:latest,JWT_SECRET=test-jwt-secret:latest"
if [ "$HAS_TELEGRAM" = true ]; then
    SECRETS="$SECRETS,SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN=test-telegram-bot-token:latest,SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME=test-telegram-bot-username:latest"
fi
if [ "$HAS_GEMINI" = true ]; then
    SECRETS="$SECRETS,TEST_GOOGLE_GEMINI_CREDENTIALS_B64=test-google-gemini-credentials:latest"
fi

gcloud run deploy $TEST_BACK_SERVICE_NAME \
    --source . \
    --platform managed \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --allow-unauthenticated \
    --set-secrets "$SECRETS" \
    --env-vars-file $ENV_FILE \
    --memory 1Gi \
    --cpu 1 \
    --concurrency 100 \
    --max-instances 10 \
    --min-instances 0

cd ..

# Récupérer l'URL
BACK_URL=$(gcloud run services describe $TEST_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null)

echo ""
echo "=========================================="
echo -e "${GREEN}✅ BACKEND TEST DÉPLOYÉ!${NC}"
echo "=========================================="
echo -e "${BLUE}⚙️  URL: $BACK_URL${NC}"
echo ""
echo -e "${YELLOW}💡 Informations:${NC}"
echo "   Le backend est déployé et accessible."
echo ""
echo -e "${YELLOW}📝 Pour le développement local avec backend GCP:${NC}"
echo "   Si l'URL a changé, mettez à jour dans ~/.bashrc:"
echo "      export SUREN_TEST_API_BASE_URL=\"$BACK_URL\""
echo ""
echo -e "${YELLOW}🚀 Pour déployer le frontend:${NC}"
echo "   ./scripts/deploy_front_test.sh"
