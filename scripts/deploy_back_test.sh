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

# Tools API Key (optionnel - pour Hermes/agents externes)
HAS_TOOLS_API_KEY=false
if [ ! -z "$TOOLS_API_KEY" ]; then
    HAS_TOOLS_API_KEY=true
fi

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
# Utilise SUREN_GEMINI_API_KEY ou SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 depuis .bashrc
HAS_GEMINI=false
if [ ! -z "$SUREN_GEMINI_API_KEY" ]; then
    HAS_GEMINI=true
elif [ ! -z "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64" ]; then
    HAS_GEMINI=true
fi

# Cloudflare R2 (obligatoire - stockage de fichiers)
HAS_R2=false
if [ ! -z "$SUREN_GED_CLOUDFLARE_TOKEN" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_BUCKET_NAME" ]; then
    HAS_R2=true
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
    echo -e "${GREEN}✅ Clé Gemini trouvée (Gemini activé)${NC}"
else
    echo -e "${YELLOW}⚠️  Clé Gemini non définie (Gemini désactivé)${NC}"
fi
echo -e "${GREEN}✅ Secrets Gmail OAuth créés (Module Emails activé)${NC}"
if [ "$HAS_TOOLS_API_KEY" = true ]; then
    echo -e "${GREEN}✅ TOOLS_API_KEY trouvée (API REST agents externes activée)${NC}"
else
    echo -e "${YELLOW}⚠️  TOOLS_API_KEY non défini (API REST agents externes désactivée)${NC}"
fi

if [ "$HAS_R2" = true ]; then
    echo -e "${GREEN}✅ Credentials Cloudflare R2 trouvés (Stockage GED activé)${NC}"
else
    echo -e "${RED}❌ Credentials Cloudflare R2 manquants - Le stockage de fichiers ne fonctionnera pas${NC}"
    echo "   Variables requises dans ~/.bashrc:"
    echo "   - SUREN_GED_CLOUDFLARE_TOKEN"
    echo "   - SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID"
    echo "   - SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY"
    echo "   - SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT"
    echo "   - SUREN_GED_CLOUDFLARE_BUCKET_NAME"
    exit 1
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
    
    if gcloud secrets describe "$name" --project="$GCP_PROJECT_ID" > /dev/null 2>&1; then
        echo -e "${YELLOW}  Mise à jour du secret: $name${NC}"
        echo -n "$value" | gcloud secrets versions add "$name" --data-file=- --project="$GCP_PROJECT_ID" > /dev/null 2>&1
        
        # Nettoyer les anciennes versions (garder seulement la dernière version)
        echo -e "${BLUE}  Nettoyage des anciennes versions...${NC}"
        # Lister seulement les versions actives (ENABLED), triées par date décroissante
        local versions
        versions=$(gcloud secrets versions list "$name" --project="$GCP_PROJECT_ID" --filter="state:ENABLED" --format="value(name)" --sort-by="~createTime" 2>/dev/null || echo "")
        if [ ! -z "$versions" ]; then
            local count=0
            for version in $versions; do
                if [ $count -ge 1 ]; then
                    # Supprimer les versions anciennes (garder seulement la plus récente)
                    echo -e "${BLUE}    Suppression de la version $version...${NC}"
                    gcloud secrets versions destroy "$version" --secret="$name" --project="$GCP_PROJECT_ID" --quiet > /dev/null 2>&1
                fi
                count=$((count+1))
            done
        fi
    else
        echo -e "${BLUE}  Création du secret: $name${NC}"
        echo -n "$value" | gcloud secrets create "$name" --data-file=- --project="$GCP_PROJECT_ID" \
            --replication-policy user-managed --locations "$GCP_REGION" > /dev/null 2>&1
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
    # Priorité à SUREN_GEMINI_API_KEY, fallback SUREN_GOOGLE_GEMINI_CREDENTIALS_B64
    GEMINI_VALUE="${SUREN_GEMINI_API_KEY:-$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64}"
    create_or_update_secret "test-google-gemini-api-key" "$GEMINI_VALUE"
fi

# Gmail OAuth2 (obligatoire pour Hermès)
GMAIL_CLIENT_ID="${SUREN_GMAIL_OAUTH_CLIENT_ID:-$(grep "^GMAIL_OAUTH_CLIENT_ID=" "$PROJECT_ROOT/.env.test" 2>/dev/null | cut -d= -f2-)}"
GMAIL_CLIENT_SECRET="${SUREN_GMAIL_OAUTH_CLIENT_SECRET:-$(grep "^GMAIL_OAUTH_CLIENT_SECRET=" "$PROJECT_ROOT/.env.test" 2>/dev/null | cut -d= -f2-)}"
GMAIL_REFRESH_TOKEN="${SUREN_GMAIL_OAUTH_REFRESH_TOKEN:-$(grep "^GMAIL_OAUTH_REFRESH_TOKEN=" "$PROJECT_ROOT/.env.test" 2>/dev/null | cut -d= -f2-)}"

create_or_update_secret "gmail-oauth-client-id" "$GMAIL_CLIENT_ID"
create_or_update_secret "gmail-oauth-client-secret" "$GMAIL_CLIENT_SECRET"
create_or_update_secret "gmail-oauth-refresh-token" "$GMAIL_REFRESH_TOKEN"
create_or_update_secret "gmail-account" "REDACTED_EMAIL"

# Tools API Key (optionnel - Hermes/agents externes)
if [ "$HAS_TOOLS_API_KEY" = true ]; then
    create_or_update_secret "tools-api-key" "$TOOLS_API_KEY"
fi

# Cloudflare R2 (obligatoire)
if [ "$HAS_R2" = true ]; then
    create_or_update_secret "r2-endpoint-url" "$SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT"
    create_or_update_secret "r2-access-key-id" "$SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID"
    create_or_update_secret "r2-secret-access-key" "$SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY"
    create_or_update_secret "r2-token" "$SUREN_GED_CLOUDFLARE_TOKEN"
    create_or_update_secret "r2-bucket-name" "$SUREN_GED_CLOUDFLARE_BUCKET_NAME"
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
GCP_PROJECT_ID: "suren-saas"
DEBUG: "true"
EOF

# Préparer les secrets
SECRETS="SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=test-supabase-service-key:latest,JWT_SECRET=test-jwt-secret:latest"
if [ "$HAS_TELEGRAM" = true ]; then
    SECRETS="$SECRETS,SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN=test-telegram-bot-token:latest,SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME=test-telegram-bot-username:latest"
fi
if [ "$HAS_GEMINI" = true ]; then
    SECRETS="$SECRETS,GOOGLE_API_KEY=test-google-gemini-api-key:latest"
fi
# Gmail OAuth toujours inclus (obligatoire pour Hermès)
SECRETS="$SECRETS,SUREN_GMAIL_OAUTH_CLIENT_ID=gmail-oauth-client-id:latest,SUREN_GMAIL_OAUTH_CLIENT_SECRET=gmail-oauth-client-secret:latest,SUREN_GMAIL_OAUTH_REFRESH_TOKEN=gmail-oauth-refresh-token:latest,SUREN_GMAIL_ACCOUNT=gmail-account:latest"
if [ "$HAS_TOOLS_API_KEY" = true ]; then
    SECRETS="$SECRETS,TOOLS_API_KEY=tools-api-key:latest"
fi

if [ "$HAS_R2" = true ]; then
    SECRETS="$SECRETS,R2_ENDPOINT_URL=r2-endpoint-url:latest,R2_ACCESS_KEY_ID=r2-access-key-id:latest,R2_SECRET_ACCESS_KEY=r2-secret-access-key:latest,R2_TOKEN=r2-token:latest,R2_BUCKET_NAME=r2-bucket-name:latest"
fi

gcloud run deploy $TEST_BACK_SERVICE_NAME \
    --source . \
    --platform managed \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --allow-unauthenticated \
    --set-secrets "$SECRETS" \
    --env-vars-file $ENV_FILE \
    --memory 2Gi \
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

# Nettoyage Artifact Registry
echo ""
echo -e "${YELLOW}🧹 Nettoyage Artifact Registry...${NC}"
REPOSITORY="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/cloud-run-source-deploy/$TEST_BACK_SERVICE_NAME"

# Vérifier si le dépôt existe
if gcloud artifacts repositories describe "cloud-run-source-deploy" --location="$GCP_REGION" --project="$GCP_PROJECT_ID" > /dev/null 2>&1; then
    echo -e "${BLUE}  Dépôt trouvé: $REPOSITORY${NC}"
    
    # Lister toutes les images avec leurs timestamps
    IMAGES=$(gcloud artifacts docker images list "$REPOSITORY" --sort-by="~UPDATE_TIME" --format="value(digest)" 2>/dev/null || echo "")
    
    if [ ! -z "$IMAGES" ]; then
        echo -e "${BLUE}  Images trouvées: $(echo "$IMAGES" | wc -l)${NC}"
        
        # Garder seulement les 3 images les plus récentes
        count=0
        for digest in $IMAGES; do
            if [ $count -ge 3 ]; then
                # Supprimer les images anciennes
                echo -e "${YELLOW}    Suppression de l'image: ${digest:0:20}...${NC}"
                gcloud artifacts docker images delete "$REPOSITORY@$digest" --quiet > /dev/null 2>&1
            fi
            count=$((count+1))
        done
        
        echo -e "${GREEN}  ✅ Nettoyage Artifact Registry terminé (3 images conservées)${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Aucune image trouvée dans le dépôt${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠️  Dépôt Artifact Registry non trouvé${NC}"
fi
