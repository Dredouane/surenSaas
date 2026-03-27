#!/bin/bash
# Script d'installation et configuration initiale

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "  Setup SurenSaaS"
echo "=========================================="
echo ""

# Vérifier les prérequis
echo -e "${YELLOW}🔍 Vérification des prérequis...${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker requis${NC}"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}❌ Docker Compose requis${NC}"; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e "${YELLOW}⚠️  Node.js recommandé pour le dev${NC}"; }
command -v python3 >/dev/null 2>&1 || { echo -e "${YELLOW}⚠️  Python3 recommandé pour le dev${NC}"; }

echo -e "${GREEN}✅ Prérequis OK${NC}"
echo ""

# Créer le fichier .env s'il n'existe pas
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Création du fichier .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Fichier .env créé${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Modifiez le fichier .env avec vos vraies valeurs Supabase!${NC}"
    echo ""
fi

# Créer les dossiers node_modules
if [ -d surenSaasFront ] && [ ! -d surenSaasFront/node_modules ]; then
    echo -e "${YELLOW}📦 Installation des dépendances Frontend...${NC}"
    cd surenSaasFront
    npm install
    cd ..
    echo -e "${GREEN}✅ Frontend installé${NC}"
fi

# Créer l'environnement Python virtuel pour le backend
if [ -d surenSaasBack ] && [ ! -d surenSaasBack/venv ]; then
    echo -e "${YELLOW}🐍 Création de l'environnement Python...${NC}"
    cd surenSaasBack
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    cd ..
    echo -e "${GREEN}✅ Backend configuré${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup terminé!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}Prochaines étapes:${NC}"
echo ""
echo "1. Configurez votre fichier .env:"
echo "   nano .env"
echo ""
echo "2. Créez un projet Supabase et copiez les URLs/clés dans .env"
echo ""
echo "3. Lancez les migrations DB:"
echo "   ./scripts/migrate.sh"
echo ""
echo "4. Démarrez en local:"
echo "   docker-compose up"
echo ""
echo "5. Ou déployez sur GCP:"
echo "   ./scripts/deploy.sh all"
echo ""
