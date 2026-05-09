#!/bin/bash
# Script pour vérifier l'état des variables d'environnement sur le backend test déployé

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🔍 VÉRIFICATION DU BACKEND TEST${NC}"
echo "=========================================="
echo ""

# Charger l'environnement
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ -f .env.test ]; then
    set -a
    source .env.test
    set +a
fi

if [ -z "$GCP_PROJECT_ID" ] || [ -z "$TEST_BACK_SERVICE_NAME" ]; then
    echo -e "${RED}❌ Variables GCP non définies${NC}"
    exit 1
fi

# Récupérer les infos du service
SERVICE_INFO=$(gcloud run services describe $TEST_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format json 2>/dev/null || echo "null")

if [ "$SERVICE_INFO" = "null" ]; then
    echo -e "${RED}❌ Service $TEST_BACK_SERVICE_NAME non trouvé${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Service trouvé${NC}"
echo ""

# Afficher l'URL
URL=$(echo $SERVICE_INFO | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', {}).get('url', 'N/A'))")
echo -e "${BLUE}🌐 URL: $URL${NC}"
echo ""

# Vérifier les secrets
echo -e "${YELLOW}🔐 Secrets configurés:${NC}"
gcloud run services describe $TEST_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format='table[box](spec.template.spec.containers[0].envFrom.secretRef.secrets.list():label=SECRETS)' 2>/dev/null || echo "Aucun secret trouvé"

echo ""

# Vérifier les variables d'environnement
echo -e "${YELLOW}📊 Variables d'environnement:${NC}"
gcloud run services describe $TEST_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format='table[box](spec.template.spec.containers[0].env.name, spec.template.spec.containers[0].env.value:label=ENV_VARS)' 2>/dev/null || echo "Aucune variable trouvée"

echo ""

# Test de santé
echo -e "${YELLOW}🧪 Test de santé:${NC}"
if curl -sf "$URL/api/v1/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend répond${NC}"
    
    # Tester un endpoint qui nécessite Supabase
    echo -e "${YELLOW}  Test connexion Supabase:${NC}"
    RESPONSE=$(curl -s -X POST "$URL/api/v1/auth/check-email" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com"}' 2>/dev/null || echo "ERROR")
    
    if echo "$RESPONSE" | grep -q "Invalid API key"; then
        echo -e "${RED}❌ ERREUR: Clé API Supabase invalide${NC}"
        echo -e "${YELLOW}💡 Les secrets ne sont pas correctement configurés${NC}"
        echo ""
        echo -e "${BLUE}Pour corriger:${NC}"
        echo "  1. ./scripts/setup-gcp-secrets.sh"
        echo "  2. ./scripts/deploy_back_test.sh"
    elif echo "$RESPONSE" | grep -q "authorized\|exists"; then
        echo -e "${GREEN}✅ Connexion Supabase OK${NC}"
    else
        echo -e "${YELLOW}⚠️ Réponse inattendue: $RESPONSE${NC}"
    fi
else
    echo -e "${RED}❌ Backend ne répond pas${NC}"
fi

echo ""
