#!/bin/bash
# Script pour tester tous les builds avant déploiement

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🧪 TEST DE TOUS LES BUILDS${NC}"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

BACKEND_SUCCESS=false
FRONTEND_SUCCESS=false

# Test Backend
echo -e "${BLUE}🔧 Test du build Backend...${NC}"
echo ""
cd "$PROJECT_ROOT"
if ./scripts/test-build-back.sh; then
    BACKEND_SUCCESS=true
    echo ""
    echo -e "${GREEN}✅ Backend: OK${NC}"
else
    echo ""
    echo -e "${RED}❌ Backend: ÉCHEC${NC}"
fi

echo ""
echo "------------------------------------------"
echo ""

# Test Frontend
echo -e "${BLUE}🎨 Test du build Frontend...${NC}"
echo ""
cd "$PROJECT_ROOT"
if ./scripts/test-build-front.sh; then
    FRONTEND_SUCCESS=true
    echo ""
    echo -e "${GREEN}✅ Frontend: OK${NC}"
else
    echo ""
    echo -e "${RED}❌ Frontend: ÉCHEC${NC}"
fi

echo ""
echo "=========================================="
echo -e "${YELLOW}📊 RÉSULTATS${NC}"
echo "=========================================="
echo ""

if [ "$BACKEND_SUCCESS" = true ] && [ "$FRONTEND_SUCCESS" = true ]; then
    echo -e "${GREEN}✅ TOUS LES BUILDS SONT VALIDES!${NC}"
    echo ""
    echo -e "${BLUE}Vous pouvez maintenant déployer:${NC}"
    echo "  ./scripts/deploy_back_test.sh"
    echo "  ./scripts/deploy_front_test.sh"
    exit 0
else
    echo -e "${RED}❌ CERTAINS BUILDS ONT ÉCHOUÉ${NC}"
    echo ""
    [ "$BACKEND_SUCCESS" = false ] && echo -e "${RED}  ✗ Backend${NC}"
    [ "$FRONTEND_SUCCESS" = false ] && echo -e "${RED}  ✗ Frontend${NC}"
    echo ""
    echo -e "${YELLOW}Corrigez les erreurs avant de déployer.${NC}"
    exit 1
fi
