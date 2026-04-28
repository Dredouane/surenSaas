#!/bin/bash
# Script de déploiement GCP Cloud Run
# Usage: ./deploy.sh [front|back|all]

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Charger les variables d'environnement
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Vérifier les variables requises
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}❌ Erreur: GCP_PROJECT_ID non défini${NC}"
    exit 1
fi

if [ -z "$GCP_REGION" ]; then
    GCP_REGION="europe-west1"
    echo -e "${YELLOW}⚠️  GCP_REGION non défini, utilisation de: $GCP_REGION${NC}"
fi

# Configuration
DEPLOY_TARGET=${1:-all}
BUILD_ID=$(git rev-parse --short HEAD 2>/dev/null || echo "manual-$(date +%s)")

echo "=========================================="
echo "  Déploiement SurenSaaS sur Cloud Run"
echo "=========================================="
echo -e "${BLUE}Project: $GCP_PROJECT_ID${NC}"
echo -e "${BLUE}Region: $GCP_REGION${NC}"
echo -e "${BLUE}Build ID: $BUILD_ID${NC}"
echo -e "${BLUE}Target: $DEPLOY_TARGET${NC}"
echo ""

# Fonction pour déployer le backend
deploy_backend() {
    echo -e "${YELLOW}🚀 Déploiement Backend...${NC}"
    
    cd surenSaasBack
    
    # Vérifier que les secrets existent
    if ! gcloud secrets versions list supabase-url --project=$GCP_PROJECT_ID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Création des secrets...${NC}"
        echo "$SUPABASE_URL" | gcloud secrets create supabase-url --data-file=- --project=$GCP_PROJECT_ID
        echo "$SUPABASE_SERVICE_KEY" | gcloud secrets create supabase-service-key --data-file=- --project=$GCP_PROJECT_ID
        echo "$JWT_SECRET" | gcloud secrets create jwt-secret --data-file=- --project=$GCP_PROJECT_ID
    fi
    
    # Déployer
    gcloud run deploy $BACK_SERVICE_NAME \
        --source . \
        --platform managed \
        --region $GCP_REGION \
        --project $GCP_PROJECT_ID \
        --no-allow-unauthenticated \
        --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=supabase-service-key:latest,JWT_SECRET=jwt-secret:latest" \
        --set-env-vars "ALLOWED_ORIGINS=https://$FRONT_SERVICE_NAME-$GCP_REGION-run.app" \
        --memory 1Gi \
        --cpu 1 \
        --concurrency 100 \
        --max-instances 50 \
        --min-instances 0
    
    cd ..
    
    echo -e "${GREEN}✅ Backend déployé!${NC}"
}

# Fonction pour déployer le frontend
deploy_frontend() {
    echo -e "${YELLOW}🚀 Déploiement Frontend...${NC}"
    
    cd surenSaasFront
    
    # Obtenir l'URL du backend
    BACKEND_URL=$(gcloud run services describe $BACK_SERVICE_NAME \
        --region $GCP_REGION \
        --project $GCP_PROJECT_ID \
        --format 'value(status.url)' 2>/dev/null || echo "")
    
    if [ -z "$BACKEND_URL" ]; then
        echo -e "${RED}❌ Erreur: Backend non déployé. Déployez d'abord le backend.${NC}"
        exit 1
    fi
    
    # Déployer
    gcloud run deploy $FRONT_SERVICE_NAME \
        --source . \
        --platform managed \
        --region $GCP_REGION \
        --project $GCP_PROJECT_ID \
        --allow-unauthenticated \
        --set-env-vars "BUILD_ID=$BUILD_ID,API_URL=$BACKEND_URL" \
        --memory 512Mi \
        --cpu 1 \
        --concurrency 80 \
        --max-instances 10 \
        --min-instances 1
    
    cd ..
    
    echo -e "${GREEN}✅ Frontend déployé!${NC}"
}

# Déploiement selon la cible
case $DEPLOY_TARGET in
    back)
        deploy_backend
        ;;
    front)
        deploy_frontend
        ;;
    all)
        deploy_backend
        deploy_frontend
        ;;
    *)
        echo -e "${RED}❌ Usage: $0 [front|back|all]${NC}"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Déploiement terminé!${NC}"
echo "=========================================="

# Afficher les URLs
if [ "$DEPLOY_TARGET" = "all" ] || [ "$DEPLOY_TARGET" = "front" ]; then
    FRONT_URL=$(gcloud run services describe $FRONT_SERVICE_NAME \
        --region $GCP_REGION \
        --project $GCP_PROJECT_ID \
        --format 'value(status.url)' 2>/dev/null)
    echo -e "${BLUE}🌐 Frontend: $FRONT_URL${NC}"
fi

if [ "$DEPLOY_TARGET" = "all" ] || [ "$DEPLOY_TARGET" = "back" ]; then
    BACK_URL=$(gcloud run services describe $BACK_SERVICE_NAME \
        --region $GCP_REGION \
        --project $GCP_PROJECT_ID \
        --format 'value(status.url)' 2>/dev/null)
    echo -e "${BLUE}⚙️  Backend: $BACK_URL${NC}"
fi
