#!/bin/bash
# Script de déploiement du FRONTEND TEST sur GCP Cloud Run

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🚀 DEPLOIEMENT FRONTEND TEST${NC}"
echo "=========================================="
echo ""

# Charger l'environnement TEST
if [ ! -f .env.test ]; then
    echo -e "${RED}❌ Erreur: .env.test non trouvé${NC}"
    echo "Créez-le: cp .env.test.example .env.test"
    exit 1
fi

# Charger les variables
echo -e "${BLUE}📋 Chargement de .env.test...${NC}"
set -a
source .env.test
set +a

# Vérifier les variables requises
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}❌ Erreur: GCP_PROJECT_ID non défini dans .env.test${NC}"
    exit 1
fi

if [ -z "$TEST_FRONT_SERVICE_NAME" ]; then
    echo -e "${RED}❌ Erreur: TEST_FRONT_SERVICE_NAME non défini${NC}"
    exit 1
fi

# Build ID
BUILD_ID=$(git rev-parse --short HEAD 2>/dev/null || echo "test-$(date +%s)")
echo -e "${BLUE}🔨 Build ID: $BUILD_ID${NC}"
echo ""

# Vérifier que le backend test est déployé
echo -e "${YELLOW}🔍 Vérification du backend test...${NC}"
BACKEND_URL=$(gcloud run services describe $TEST_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null || echo "")

if [ -z "$BACKEND_URL" ]; then
    echo -e "${RED}❌ Erreur: Backend test non déployé!${NC}"
    echo "Déployez d'abord: ./scripts/deploy_back_test.sh"
    exit 1
fi

echo -e "${GREEN}✅ Backend test trouvé: $BACKEND_URL${NC}"

# Obtenir l'URL du frontend (pour les redirections)
FRONTEND_URL=$(gcloud run services describe $TEST_FRONT_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null || echo "")
if [ -z "$FRONTEND_URL" ]; then
    echo -e "${YELLOW}⚠️  Frontend test non encore déployé, URL sera définie après déploiement${NC}"
    # URL par défaut basée sur le nom du service
    FRONTEND_URL="https://${TEST_FRONT_SERVICE_NAME}-REDACTED-ew.a.run.app"
fi
echo -e "${GREEN}✅ Frontend URL: $FRONTEND_URL${NC}"
echo ""

# Préparation du build
echo -e "${YELLOW}📋 Préparation du build avec configuration TEST...${NC}"
cd surenSaasFront

echo -e "${BLUE}📝 Création du fichier .env pour le build...${NC}"

# Créer le fichier .env.production avec les variables pour Next.js
# Ce fichier sera copié par le Dockerfile et lu par Next.js au build time (mode production)
cat > .env.production << EOF
NEXT_PUBLIC_API_URL=${BACKEND_URL}
NEXT_PUBLIC_ORG_ID=${NEXT_PUBLIC_ORG_ID}
NEXT_PUBLIC_ORG_SLUG=${NEXT_PUBLIC_ORG_SLUG}
NEXT_PUBLIC_FRONTEND_URL=${FRONTEND_URL}
EOF

# Fonction de nettoyage
cleanup() {
    echo ""
    echo -e "${BLUE}🧹 Nettoyage...${NC}"
    
    # Supprimer le fichier .env.production créé
    if [ -f .env.production ]; then
        rm -f .env.production
        echo -e "${GREEN}   ✅ Fichier .env.production supprimé${NC}"
    fi
}

# Activer le nettoyage automatique
trap cleanup EXIT

echo -e "${BLUE}✅ Configuration API: $BACKEND_URL${NC}"
echo ""

# Déploiement
echo -e "${YELLOW}🚀 Déploiement Frontend TEST...${NC}"
gcloud run deploy $TEST_FRONT_SERVICE_NAME \
    --source . \
    --platform managed \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --allow-unauthenticated \
    --set-env-vars "BUILD_ID=$BUILD_ID,API_URL=$BACKEND_URL,ENVIRONMENT=test,NEXT_PUBLIC_ORG_SLUG=$TEST_ORG_SLUG,FRONTEND_URL=$FRONTEND_URL" \
    --memory 512Mi \
    --cpu 1 \
    --concurrency 80 \
    --max-instances 5 \
    --min-instances 0

cd ..

# Récupérer l'URL déployée
FRONT_URL=$(gcloud run services describe $TEST_FRONT_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null)

echo ""
echo "=========================================="
echo -e "${GREEN}✅ FRONTEND TEST DÉPLOYÉ!${NC}"
echo "=========================================="
echo -e "${BLUE}🌐 URL: $FRONT_URL${NC}"
echo -e "${BLUE}⚙️  Backend: $BACKEND_URL${NC}"
echo ""
echo -e "${YELLOW}💡 Pour tester:${NC}"
echo "   1. Ajoutez votre email dans pre_authorized_emails (org: $NEXT_PUBLIC_ORG_SLUG)"
echo "   2. Accédez à: $FRONT_URL/$NEXT_PUBLIC_ORG_SLUG/login"

# Nettoyage Artifact Registry
echo ""
echo -e "${YELLOW}🧹 Nettoyage Artifact Registry...${NC}"
REPOSITORY="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/cloud-run-source-deploy/$TEST_FRONT_SERVICE_NAME"

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
