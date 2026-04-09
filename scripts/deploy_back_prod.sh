#!/bin/bash
# Script de déploiement du BACKEND PRODUCTION sur GCP Cloud Run

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${RED}🚀 DEPLOIEMENT BACKEND PRODUCTION${NC}"
echo -e "${RED}⚠️  ATTENTION: Environnement de production${NC}"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Vérification de sécurité
read -p "Êtes-vous sûr de vouloir déployer en PRODUCTION? (tapez 'prod' pour confirmer): " confirm
if [ "$confirm" != "prod" ]; then
    echo -e "${YELLOW}❌ Déploiement annulé${NC}"
    exit 0
fi

echo ""

# Charger l'environnement PROD (sans secrets)
if [ ! -f .env.prod ]; then
    echo -e "${RED}❌ Erreur: .env.prod non trouvé${NC}"
    echo "Créez-le à partir du template: cp .env.prod.example .env.prod"
    exit 1
fi

echo -e "${BLUE}📋 Chargement de .env.prod...${NC}"
set -a
source .env.prod
set +a

# Vérifier les variables du .bashrc
echo ""
echo -e "${YELLOW}🔐 Vérification des secrets dans ~/.bashrc...${NC}"
MISSING_VARS=()

if [ -z "$PROD_SUPABASE_SERVICE_KEY" ]; then
    MISSING_VARS+=("PROD_SUPABASE_SERVICE_KEY")
fi

if [ -z "$PROD_JWT_SECRET" ]; then
    MISSING_VARS+=("PROD_JWT_SECRET")
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

# Gemini est optionnel (désactivé temporairement)
# Utilise SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 depuis .bashrc (partagé test/prod)
HAS_GEMINI=false
if [ ! -z "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64" ]; then
    HAS_GEMINI=true
fi

echo -e "${GREEN}✅ Secrets trouvés dans ~/.bashrc${NC}"
if [ "$HAS_GEMINI" = true ]; then
    echo -e "${GREEN}✅ SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 trouvé (Gemini activé)${NC}"
else
    echo -e "${YELLOW}⚠️  SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 non défini (Gemini désactivé)${NC}"
fi

# Vérification de sécurité: JWT différent de TEST
if [ ! -z "$TEST_JWT_SECRET" ] && [ "$PROD_JWT_SECRET" = "$TEST_JWT_SECRET" ]; then
    echo -e "${RED}❌ ERREUR CRITIQUE: PROD_JWT_SECRET identique à TEST_JWT_SECRET!${NC}"
    echo "Modifiez ~/.bashrc avec des secrets différents pour la sécurité."
    exit 1
fi

# Vérifier les variables GCP
if [ -z "$GCP_PROJECT_ID" ] || [ -z "$PROD_BACK_SERVICE_NAME" ]; then
    echo -e "${RED}❌ Erreur: Variables GCP manquantes dans .env.prod${NC}"
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
create_or_update_secret "prod-supabase-service-key" "$PROD_SUPABASE_SERVICE_KEY"
create_or_update_secret "prod-jwt-secret" "$PROD_JWT_SECRET"

# Gemini (optionnel)
if [ "$HAS_GEMINI" = true ]; then
    create_or_update_secret "prod-google-gemini-credentials" "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64"
fi

echo ""

# Déploiement
echo -e "${RED}🚀 Déploiement Backend PRODUCTION...${NC}"
cd surenSaasBack

# Calculer les origines CORS
CORS_ORIGINS=""
FRONT_URL=$(gcloud run services describe $PROD_FRONT_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null || echo "")

if [ ! -z "$FRONT_URL" ]; then
    CORS_ORIGINS="$FRONT_URL"
else
    CORS_ORIGINS="https://$PROD_FRONT_SERVICE_NAME-$GCP_REGION-run.app"
fi

# Créer un fichier temporaire pour les variables d'environnement
ENV_FILE=$(mktemp)
cat > $ENV_FILE << EOF
ALLOWED_ORIGINS: "$CORS_ORIGINS"
ENVIRONMENT: "production"
ORG_ID: "$PROD_ORG_ID"
DEBUG: "false"
EOF

# Préparer les secrets
SECRETS="SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=prod-supabase-service-key:latest,JWT_SECRET=prod-jwt-secret:latest"
if [ "$HAS_GEMINI" = true ]; then
    SECRETS="$SECRETS,GOOGLE_GEMINI_CREDENTIALS_B64=prod-google-gemini-credentials:latest"
fi

gcloud run deploy $PROD_BACK_SERVICE_NAME \
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
    --max-instances 50 \
    --min-instances 1

# Nettoyer
rm -f $ENV_FILE

cd ..

# Récupérer l'URL
BACK_URL=$(gcloud run services describe $PROD_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null)

echo ""
echo "=========================================="
echo -e "${GREEN}✅ BACKEND PRODUCTION DÉPLOYÉ!${NC}"
echo "=========================================="
echo -e "${BLUE}⚙️  URL: $BACK_URL${NC}"
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "   gcloud logging tail --service=$PROD_BACK_SERVICE_NAME"
