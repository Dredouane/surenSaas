ln -sf .env.test .env#!/bin/bash
# Script pour vérifier la configuration de l'environnement

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "  VÉRIFICATION CONFIGURATION"
echo "=========================================="
echo ""

# Détecter l'environnement actuel
if [ -L .env ]; then
    CURRENT=$(readlink .env)
    if [[ "$CURRENT" == *".env.test"* ]]; then
        echo -e "${YELLOW}🔧 Environnement: TEST${NC}"
        ENV="test"
    elif [[ "$CURRENT" == *".env.prod"* ]]; then
        echo -e "${RED}🔴 Environnement: PRODUCTION${NC}"
        ENV="prod"
    fi
else
    echo -e "${BLUE}⚙️  Environnement: Standard (.env)${NC}"
    ENV="standard"
fi

echo ""

# Charger les variables
set -a
source .env
set +a

ERRORS=0

# Fonction de vérification
check_var() {
    local name=$1
    local value=$2
    local required=$3
    
    if [ -z "$value" ]; then
        if [ "$required" == "true" ]; then
            echo -e "${RED}❌ $name: MANQUANT (obligatoire)${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠️  $name: vide (optionnel)${NC}"
        fi
    else
        # Masquer les valeurs sensibles
        if [[ "$name" == *"SECRET"* ]] || [[ "$name" == *"KEY"* ]] || [[ "$name" == *"PASSWORD"* ]]; then
            echo -e "${GREEN}✅ $name: ${value:0:10}...${NC}"
        else
            echo -e "${GREEN}✅ $name: $value${NC}"
        fi
    fi
}

echo -e "${BLUE}📋 Variables Supabase:${NC}"
check_var "SUPABASE_URL" "$SUPABASE_URL" "true"
check_var "SUPABASE_SERVICE_KEY" "$SUPABASE_SERVICE_KEY" "true"

echo ""
echo -e "${BLUE}📋 Variables Backend:${NC}"
check_var "JWT_SECRET" "$JWT_SECRET" "true"
check_var "ALLOWED_ORIGINS" "$ALLOWED_ORIGINS" "false"

echo ""
echo -e "${BLUE}📋 Variables GCP:${NC}"
check_var "GCP_PROJECT_ID" "$GCP_PROJECT_ID" "true"
check_var "GCP_REGION" "$GCP_REGION" "true"

if [ "$ENV" == "test" ] || [ "$ENV" == "standard" ]; then
    echo ""
    echo -e "${BLUE}📋 Services TEST:${NC}"
    check_var "TEST_FRONT_SERVICE_NAME" "$TEST_FRONT_SERVICE_NAME" "true"
    check_var "TEST_BACK_SERVICE_NAME" "$TEST_BACK_SERVICE_NAME" "true"
    check_var "TEST_ORG_ID" "$TEST_ORG_ID" "true"
    check_var "TEST_ORG_SLUG" "$TEST_ORG_SLUG" "true"
fi

if [ "$ENV" == "prod" ] || [ "$ENV" == "standard" ]; then
    echo ""
    echo -e "${BLUE}📋 Services PROD:${NC}"
    check_var "PROD_FRONT_SERVICE_NAME" "$PROD_FRONT_SERVICE_NAME" "true"
    check_var "PROD_BACK_SERVICE_NAME" "$PROD_BACK_SERVICE_NAME" "true"
    check_var "PROD_ORG_ID" "$PROD_ORG_ID" "true"
    check_var "PROD_ORG_SLUG" "$PROD_ORG_SLUG" "true"
fi

echo ""
echo "=========================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ Configuration valide!${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS erreur(s) trouvée(s)${NC}"
    echo ""
    echo "Corrigez votre fichier .env et relancez ce script."
    exit 1
fi
