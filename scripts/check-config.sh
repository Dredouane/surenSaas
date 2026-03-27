#!/bin/bash
# Script de vérification de la configuration des scripts Run et Deploy
# Vérifie que tout est aligné avant de lancer les services

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cd /home/redouane/dev/AI-ERA/surenSaas

echo "=========================================="
echo -e "${BLUE}🔍 VÉRIFICATION DE LA CONFIGURATION${NC}"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0

# 1. Vérifier que .env.test existe
echo -e "${BLUE}1. Vérification de .env.test...${NC}"
if [ ! -f .env.test ]; then
    echo -e "${RED}   ❌ .env.test non trouvé !${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "${GREEN}   ✅ .env.test présent${NC}"
    
    # Vérifier les variables critiques
    if grep -q "NEXT_PUBLIC_ORG_ID=" .env.test; then
        ORG_ID=$(grep "NEXT_PUBLIC_ORG_ID=" .env.test | cut -d'=' -f2)
        echo -e "${GREEN}   ✅ NEXT_PUBLIC_ORG_ID=$ORG_ID${NC}"
    else
        echo -e "${RED}   ❌ NEXT_PUBLIC_ORG_ID manquant${NC}"
        ERRORS=$((ERRORS+1))
    fi
    
    if grep -q "NEXT_PUBLIC_ORG_SLUG=" .env.test; then
        ORG_SLUG=$(grep "NEXT_PUBLIC_ORG_SLUG=" .env.test | cut -d'=' -f2)
        echo -e "${GREEN}   ✅ NEXT_PUBLIC_ORG_SLUG=$ORG_SLUG${NC}"
    else
        echo -e "${RED}   ❌ NEXT_PUBLIC_ORG_SLUG manquant${NC}"
        ERRORS=$((ERRORS+1))
    fi
fi
echo ""

# 2. Vérifier que .env.local est dans .gitignore
echo -e "${BLUE}2. Vérification de .gitignore...${NC}"
if grep -q ".env.local" .gitignore 2>/dev/null && \
   grep -q ".env.local" surenSaasFront/.gitignore 2>/dev/null; then
    echo -e "${GREEN}   ✅ .env.local dans .gitignore (racine et frontend)${NC}"
else
    echo -e "${YELLOW}   ⚠️  .env.local pas dans .gitignore${NC}"
    WARNINGS=$((WARNINGS+1))
fi
echo ""

# 3. Vérifier que .env.local n'existe pas
echo -e "${BLUE}3. Vérification des fichiers .env.local...${NC}"
if [ -f surenSaasFront/.env.local ]; then
    echo -e "${YELLOW}   ⚠️  surenSaasFront/.env.local existe (sera écrasé par les scripts)${NC}"
    WARNINGS=$((WARNINGS+1))
else
    echo -e "${GREEN}   ✅ Pas de .env.local résiduel${NC}"
fi
echo ""

# 4. Vérifier les secrets dans ~/.bashrc
echo -e "${BLUE}4. Vérification des secrets dans ~/.bashrc...${NC}"
source ~/.bashrc 2>/dev/null || true

if [ -z "$TEST_SUPABASE_SERVICE_KEY" ]; then
    echo -e "${RED}   ❌ TEST_SUPABASE_SERVICE_KEY non défini${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "${GREEN}   ✅ TEST_SUPABASE_SERVICE_KEY défini${NC}"
fi

if [ -z "$TEST_JWT_SECRET" ]; then
    echo -e "${RED}   ❌ TEST_JWT_SECRET non défini${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "${GREEN}   ✅ TEST_JWT_SECRET défini${NC}"
fi

if [ -z "$SUREN_TEST_API_BASE_URL" ]; then
    echo -e "${YELLOW}   ⚠️  SUREN_TEST_API_BASE_URL non défini (nécessaire pour run-local-front_test-gcp.sh)${NC}"
    WARNINGS=$((WARNINGS+1))
else
    echo -e "${GREEN}   ✅ SUREN_TEST_API_BASE_URL=$SUREN_TEST_API_BASE_URL${NC}"
fi
echo ""

# 5. Vérifier que les scripts sont exécutables
echo -e "${BLUE}5. Vérification des scripts...${NC}"
SCRIPTS=(
    "scripts/run-local-back_test.sh"
    "scripts/run-local-front_test.sh"
    "scripts/run-local-front_test-gcp.sh"
    "scripts/run-local_test.sh"
    "scripts/deploy_back_test.sh"
    "scripts/deploy_front_test.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -x "$script" ]; then
        echo -e "${GREEN}   ✅ $script${NC}"
    else
        echo -e "${RED}   ❌ $script (non exécutable)${NC}"
        ERRORS=$((ERRORS+1))
    fi
done
echo ""

# 6. Vérifier les ports
echo -e "${BLUE}6. Vérification des ports...${NC}"
PORT_3000=$(lsof -ti:3000 2>/dev/null || echo "")
PORT_8080=$(lsof -ti:8080 2>/dev/null || echo "")

if [ -z "$PORT_3000" ]; then
    echo -e "${GREEN}   ✅ Port 3000 libre${NC}"
else
    echo -e "${YELLOW}   ⚠️  Port 3000 occupé (PID: $PORT_3000)${NC}"
    echo -e "${YELLOW}      Les scripts le libéreront automatiquement${NC}"
    WARNINGS=$((WARNINGS+1))
fi

if [ -z "$PORT_8080" ]; then
    echo -e "${GREEN}   ✅ Port 8080 libre${NC}"
else
    echo -e "${YELLOW}   ⚠️  Port 8080 occupé (PID: $PORT_8080)${NC}"
    echo -e "${YELLOW}      Les scripts le libéreront automatiquement${NC}"
    WARNINGS=$((WARNINGS+1))
fi
echo ""

# 7. Vérifier la cohérence des variables
echo -e "${BLUE}7. Vérification de la cohérence...${NC}"

# Vérifier que .env.test n'a pas d'URLs hardcodées
if grep -q "API_URL=https://" .env.test 2>/dev/null || \
   grep -q "API_URL=http://" .env.test 2>/dev/null | grep -v "localhost"; then
    echo -e "${YELLOW}   ⚠️  Des URLs sont hardcodées dans .env.test${NC}"
    echo -e "${YELLOW}      (ça devrait être géré par les scripts ou ~/.bashrc)${NC}"
    WARNINGS=$((WARNINGS+1))
else
    echo -e "${GREEN}   ✅ Pas d'URLs hardcodées dans .env.test${NC}"
fi

# Vérifier que les scripts utilisent les bonnes variables
if grep -q "TEST_ORG_ID" scripts/deploy_back_test.sh; then
    echo -e "${RED}   ❌ deploy_back_test.sh utilise encore TEST_ORG_ID${NC}"
    echo -e "${RED}      (devrait utiliser NEXT_PUBLIC_ORG_ID)${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "${GREEN}   ✅ Variables d'organisation uniformisées (NEXT_PUBLIC_*)${NC}"
fi
echo ""

# Résumé
echo "=========================================="
echo -e "${BLUE}📊 RÉSULTAT${NC}"
echo "=========================================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ Tout est parfaitement configuré !${NC}"
    echo ""
    echo "Vous pouvez lancer :"
    echo "  - ./scripts/run-local-back_test.sh (backend local)"
    echo "  - ./scripts/run-local-front_test.sh (frontend local)"
    echo "  - ./scripts/run-local_test.sh (les deux)"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS avertissement(s)${NC}"
    echo ""
    echo "La configuration fonctionnera, mais :"
    if [ -z "$SUREN_TEST_API_BASE_URL" ]; then
        echo "  - run-local-front_test-gcp.sh ne fonctionnera pas sans SUREN_TEST_API_BASE_URL"
    fi
    if [ ! -z "$PORT_3000" ] || [ ! -z "$PORT_8080" ]; then
        echo "  - Les scripts arrêteront les processus existants sur les ports"
    fi
    exit 0
else
    echo -e "${RED}❌ $ERRORS erreur(s) et $WARNINGS avertissement(s)${NC}"
    echo ""
    echo "Corrigez les erreurs avant de continuer."
    exit 1
fi
