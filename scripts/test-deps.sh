#!/bin/bash
# Test rapide des dépendances Python (sans Docker)

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🧪 TEST DÉPENDANCES PYTHON${NC}"
echo "=========================================="
echo ""

cd surenSaasBack

echo -e "${YELLOW}📦 Installation dans venv temporaire...${NC}"

# Créer venv temporaire
python3 -m venv /tmp/test-venv
source /tmp/test-venv/bin/activate

# Installer
if pip install -r requirements.txt 2>&1; then
    echo ""
    echo -e "${GREEN}✅ DÉPENDANCES OK !${NC}"
    echo ""
    
    # Test import
    echo -e "${YELLOW}🧪 Test import modules...${NC}"
    python3 -c "
import fastapi
import uvicorn
import pydantic
from supabase import create_client
import jwt
print('✅ Tous les modules importés avec succès')
"
    
    deactivate
    rm -rf /tmp/test-venv
    
    echo ""
    echo "Tu peux maintenant déployer :"
    echo "  ./scripts/deploy_back_test.sh"
else
    echo ""
    echo -e "${RED}❌ ERREUR D'INSTALLATION${NC}"
    deactivate
    rm -rf /tmp/test-venv
    exit 1
fi
