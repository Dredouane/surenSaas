#!/bin/bash
# Script de déploiement du FRONTEND PRODUCTION sur GCP Cloud Run

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🚀 DEPLOIEMENT FRONTEND PRODUCTION${NC}"
echo "=========================================="
echo ""

# Vérification de sécurité
echo -e "${RED}⚠️  ATTENTION: Vous allez déployer en PRODUCTION!${NC}"
echo -e "${YELLOW}Cela impactera les utilisateurs actifs.${NC}"
echo ""
read -p "Êtes-vous sûr? (tapez 'prod' pour confirmer): " CONFIRM

if [ "$CONFIRM" != "prod" ]; then
    echo -e "${YELLOW}❌ Déploiement annulé${NC}"
    exit 0
fi

echo ""

# Charger l'environnement PROD
if [ ! -f .env.prod ]; then
    echo -e "${RED}❌ Erreur: .env.prod non trouvé${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Chargement de .env.prod...${NC}"
set -a
source .env.prod
set +a

# Vérifier les variables
if [ -z "$GCP_PROJECT_ID" ] || [ -z "$PROD_FRONT_SERVICE_NAME" ]; then
    echo -e "${RED}❌ Erreur: Variables manquantes dans .env.prod${NC}"
    exit 1
fi

# Build ID
BUILD_ID=$(git rev-parse --short HEAD 2>/dev/null || echo "prod-$(date +%s)")
echo -e "${BLUE}🔨 Build ID: $BUILD_ID${NC}"
echo ""

# Vérifier backend prod
BACKEND_URL=$(gcloud run services describe $PROD_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null || echo "")

if [ -z "$BACKEND_URL" ]; then
    echo -e "${RED}❌ Erreur: Backend prod non déployé!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend prod: $BACKEND_URL${NC}"
echo ""

# Déploiement
echo -e "${YELLOW}🚀 Déploiement Frontend PROD...${NC}"
cd surenSaasFront

gcloud run deploy $PROD_FRONT_SERVICE_NAME \
    --source . \
    --platform managed \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --allow-unauthenticated \
    --set-env-vars "BUILD_ID=$BUILD_ID,API_URL=$BACKEND_URL,NEXT_PUBLIC_API_URL=$BACKEND_URL,ENVIRONMENT=production,NEXT_PUBLIC_ENV=production,NEXT_PUBLIC_ORG_SLUG=$PROD_ORG_SLUG,NEXT_PUBLIC_ORG_ID=$PROD_ORG_ID" \
    --memory 512Mi \
    --cpu 1 \
    --concurrency 80 \
    --max-instances 10 \
    --min-instances 1

cd ..

FRONT_URL=$(gcloud run services describe $PROD_FRONT_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null)

echo ""
echo "=========================================="
echo -e "${GREEN}✅ FRONTEND PROD DÉPLOYÉ!${NC}"
echo "=========================================="
echo -e "${BLUE}🌐 URL: $FRONT_URL${NC}"
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "   gcloud logging tail --service=$PROD_FRONT_SERVICE_NAME"
