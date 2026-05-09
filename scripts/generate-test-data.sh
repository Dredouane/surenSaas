#!/bin/bash
# Script de génération de données de test pour l'environnement de test
# Usage: ./scripts/generate-test-data.sh [org_id] [user_id] [company_id]
# 
# Ce script génère des données de test aléatoires pour le développement et les tests
# - 5 clients fictifs
# - 20 factures avec différents statuts
# - Historique des changements de statut
#
# ⚠️  ATTENTION: À n'utiliser que sur l'environnement de test!

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "  GÉNÉRATION DE DONNÉES DE TEST"
echo "=========================================="
echo ""

# Vérifier qu'on est en environnement de test
if [ -f .env.test ]; then
    source .env.test
    echo -e "${BLUE}📋 Environnement: TEST${NC}"
elif [ -f .env ]; then
    ENVIRONMENT=$(grep -E '^ENVIRONMENT=' .env | cut -d= -f2 || echo "production")
    if [ "$ENVIRONMENT" != "test" ] && [ "$ENVIRONMENT" != "development" ]; then
        echo -e "${RED}❌ ERREUR: Vous n'êtes pas en environnement de test!${NC}"
        echo ""
        echo "Ce script ne doit être exécuté que sur l'environnement de test."
        echo ""
        echo "Pour l'utiliser:"
        echo "  1. Créez un fichier .env.test avec ENVIRONMENT=test"
        echo "  2. Ou assurez-vous que ENVIRONMENT=test dans votre .env"
        exit 1
    fi
    echo -e "${BLUE}📋 Environnement: $ENVIRONMENT${NC}"
else
    echo -e "${YELLOW}⚠️  Aucun fichier .env trouvé, utilisation des valeurs par défaut${NC}"
fi

echo ""

# Paramètres par défaut pour l'environnement de test
DEFAULT_ORG_ID="REDACTEDORG"
DEFAULT_COMPANY_ID="REDACTED"

# Récupérer les arguments ou utiliser les valeurs par défaut
ORG_ID=${1:-$DEFAULT_ORG_ID}
USER_ID=${2:-}
COMPANY_ID=${3:-$DEFAULT_COMPANY_ID}

echo -e "${BLUE}📋 Organisation: $ORG_ID${NC}"
echo -e "${BLUE}📋 Company: $COMPANY_ID${NC}"

# Si USER_ID n'est pas fourni, on le demande ou on utilise une valeur temporaire
if [ -z "$USER_ID" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Attention: Aucun user_id fourni${NC}"
    echo "Le script va essayer de trouver un user existant automatiquement."
    echo ""
    echo "Pour spécifier un user_id:"
    echo "  ./scripts/generate-test-data.sh $ORG_ID <votre_user_id> $COMPANY_ID"
    echo ""
fi

echo ""
echo -e "${YELLOW}🚀 Lancement de la génération de données...${NC}"
echo ""

# Aller dans le dossier backend
cd surenSaasBack

# Exécuter le script Python
if [ -z "$USER_ID" ]; then
    python3 scripts/generate_test_data.py "$ORG_ID" "$COMPANY_ID" "$COMPANY_ID"
else
    python3 scripts/generate_test_data.py "$ORG_ID" "$USER_ID" "$COMPANY_ID"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Données de test générées avec succès!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}Vous pouvez maintenant:${NC}"
echo ""
echo "1. Consulter le dashboard: http://localhost:3000/dashboard"
echo "2. Voir les clients: http://localhost:3000/dashboard/clients"
echo "3. Voir les factures: http://localhost:3000/dashboard/invoices"
echo ""
echo -e "${YELLOW}📝 Note: Ces données sont uniquement pour le développement.${NC}"
echo ""
