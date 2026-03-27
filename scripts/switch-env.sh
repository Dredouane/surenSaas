#!/bin/bash
# Script pour basculer entre environnement test et prod
# Usage: ./scripts/switch-env.sh [test|prod]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ENV=${1:-}

if [ -z "$ENV" ]; then
    echo "Usage: ./scripts/switch-env.sh [test|prod]"
    echo ""
    echo "Environnement actuel:"
    if [ -L .env ]; then
        CURRENT=$(readlink .env)
        if [[ "$CURRENT" == *".env.test"* ]]; then
            echo -e "${YELLOW}  TEST${NC} (.env -> .env.test)"
        elif [[ "$CURRENT" == *".env.prod"* ]]; then
            echo -e "${RED}  PRODUCTION${NC} (.env -> .env.prod)"
        fi
    else
        echo "  (fichier .env standard)"
    fi
    exit 0
fi

if [ "$ENV" != "test" ] && [ "$ENV" != "prod" ]; then
    echo -e "${RED}❌ Erreur: environnement doit être 'test' ou 'prod'${NC}"
    exit 1
fi

# Sauvegarder l'ancien .env s'il existe et n'est pas un lien
if [ -f .env ] && [ ! -L .env ]; then
    echo -e "${YELLOW}💾 Sauvegarde de .env vers .env.backup${NC}"
    mv .env .env.backup.$(date +%s)
fi

# Créer le lien symbolique
if [ "$ENV" == "test" ]; then
    if [ ! -f .env.test ]; then
        echo -e "${RED}❌ Erreur: .env.test n'existe pas${NC}"
        exit 1
    fi
    rm -f .env
    ln -s .env.test .env
    echo -e "${GREEN}✅ Environnement basculé sur TEST${NC}"
    echo -e "${YELLOW}💡 Vous êtes maintenant en mode TEST${NC}"
    
elif [ "$ENV" == "prod" ]; then
    if [ ! -f .env.prod ]; then
        echo -e "${RED}❌ Erreur: .env.prod n'existe pas${NC}"
        exit 1
    fi
    
    echo -e "${RED}⚠️  ATTENTION: Vous allez passer en PRODUCTION${NC}"
    read -p "Confirmer? (oui/non): " CONFIRM
    
    if [ "$CONFIRM" != "oui" ]; then
        echo -e "${YELLOW}❌ Changement annulé${NC}"
        exit 0
    fi
    
    rm -f .env
    ln -s .env.prod .env
    echo -e "${GREEN}✅ Environnement basculé sur PRODUCTION${NC}"
    echo -e "${RED}⚠️  ATTENTION: Toutes les commandes déploieront en PROD${NC}"
fi

echo ""
echo "Variables chargées:"
echo "  PROJECT_ID: $GCP_PROJECT_ID"
echo "  FRONT_SERVICE: $([ "$ENV" == "test" ] && echo $TEST_FRONT_SERVICE_NAME || echo $PROD_FRONT_SERVICE_NAME)"
echo "  BACK_SERVICE: $([ "$ENV" == "test" ] && echo $TEST_BACK_SERVICE_NAME || echo $PROD_BACK_SERVICE_NAME)"
