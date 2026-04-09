#!/bin/bash
# Script pour tester le build Docker localement avant déploiement
# Frontend

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🐳 TEST BUILD DOCKER FRONTEND${NC}"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/surenSaasFront"

echo -e "${BLUE}📋 Vérification des fichiers...${NC}"

# Vérifier que le Dockerfile existe
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ Dockerfile non trouvé${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dockerfile trouvé${NC}"

# Vérifier que package.json existe
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ package.json non trouvé${NC}"
    exit 1
fi

echo -e "${GREEN}✅ package.json trouvé${NC}"

# Test de build Next.js local d'abord (plus rapide)
echo ""
echo -e "${YELLOW}🚀 Test de build Next.js local...${NC}"
echo "   Cela peut prendre plusieurs minutes..."
echo ""

if npm run build 2>&1; then
    echo ""
    echo -e "${GREEN}✅ BUILD NEXT.JS RÉUSSI!${NC}"
    
    # Nettoyer le build local
    rm -rf .next
    
    echo ""
    echo -e "${YELLOW}🐳 Test de build Docker...${NC}"
    echo "   Cela peut prendre plusieurs minutes..."
    echo ""
    
    if docker build -t surensaas-front-test:latest . 2>&1; then
        echo ""
        echo -e "${GREEN}✅ BUILD DOCKER RÉUSSI!${NC}"
        echo ""
        
        # Nettoyer
        docker rmi surensaas-front-test:latest 2>/dev/null || true
        
        echo ""
        echo -e "${GREEN}✅ Le build fonctionne, prêt pour le déploiement!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}❌ BUILD DOCKER ÉCHOUÉ${NC}"
        echo ""
        echo -e "${YELLOW}🔍 Vérifiez:${NC}"
        echo "   - Le Dockerfile"
        echo "   - Les variables d'environnement"
        exit 1
    fi
else
    echo ""
    echo -e "${RED}❌ BUILD NEXT.JS ÉCHOUÉ${NC}"
    echo ""
    echo -e "${YELLOW}🔍 Vérifiez:${NC}"
    echo "   - Les imports manquants"
    echo "   - Les erreurs de syntaxe TypeScript"
    echo "   - Les packages manquants (npm install)"
    exit 1
fi
