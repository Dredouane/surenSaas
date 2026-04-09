#!/bin/bash
# Script pour tester le build Docker localement avant déploiement GCP

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🔨 TEST BUILD LOCAL DOCKER${NC}"
echo "=========================================="
echo ""

cd surenSaasBack

echo -e "${YELLOW}📦 Installation des dépendances...${NC}"
pip install -r requirements.txt --quiet 2>&1 | grep -i error || echo -e "${GREEN}✅ Dépendances OK${NC}"

echo ""
echo -e "${YELLOW}🔨 Build Docker...${NC}"
docker build -t surensaas-back:test .

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ BUILD LOCAL RÉUSSI !${NC}"
    echo ""
    echo "Tu peux maintenant déployer sur GCP :"
    echo "  ./scripts/deploy_back_test.sh"
else
    echo ""
    echo -e "${RED}❌ BUILD ÉCHOUÉ${NC}"
    echo "Corrige les erreurs avant de déployer"
    exit 1
fi
