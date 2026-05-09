#!/bin/bash
# Script pour vérifier et corriger les secrets GCP pour le backend test

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🔐 VÉRIFICATION DES SECRETS GCP${NC}"
echo "=========================================="
echo ""

# Charger l'environnement TEST depuis la racine du projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ ! -f .env.test ]; then
    echo -e "${RED}❌ Erreur: .env.test non trouvé dans $PROJECT_ROOT${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Chargement des variables depuis .env.test...${NC}"
set -a
source .env.test
set +a

# Vérifier les variables requises
REQUIRED_VARS=("GCP_PROJECT_ID" "SUPABASE_URL" "SUPABASE_SERVICE_KEY" "JWT_SECRET")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Variables manquantes dans .env.test:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    exit 1
fi

echo -e "${GREEN}✅ Toutes les variables requises sont présentes${NC}"
echo ""

# Fonction pour créer/mettre à jour un secret
create_or_update_secret() {
    local name=$1
    local value=$2
    
    echo -e "${BLUE}🔐 Traitement du secret: $name${NC}"
    
    # Vérifier si le secret existe
    if gcloud secrets describe $name --project=$GCP_PROJECT_ID > /dev/null 2>&1; then
        echo -e "  ${YELLOW}Secret existe déjà, mise à jour...${NC}"
        # Créer une nouvelle version
        echo -n "$value" | gcloud secrets versions add $name --data-file=- --project=$GCP_PROJECT_ID
        echo -e "  ${GREEN}✅ Secret mis à jour${NC}"
    else
        echo -e "  ${YELLOW}Création du secret...${NC}"
        echo -n "$value" | gcloud secrets create $name --data-file=- --project=$GCP_PROJECT_ID
        echo -e "  ${GREEN}✅ Secret créé${NC}"
    fi
}

echo -e "${YELLOW}🚀 Création/Mise à jour des secrets...${NC}"
echo ""

# Créer/mettre à jour les secrets
create_or_update_secret "supabase-url" "$SUPABASE_URL"
create_or_update_secret "supabase-service-key-test" "$SUPABASE_SERVICE_KEY"
create_or_update_secret "jwt-secret-test" "$JWT_SECRET"

echo ""
echo -e "${GREEN}✅ TOUS LES SECRETS SONT CONFIGURÉS!${NC}"
echo ""
echo -e "${YELLOW}📋 Liste des secrets configurés:${NC}"
gcloud secrets list --project=$GCP_PROJECT_ID --filter="name:(supabase-url OR supabase-service-key-test OR jwt-secret-test)" --format="table(name, createTime)"
echo ""
echo -e "${BLUE}💡 Prochaine étape: Redéployer le backend test${NC}"
echo "   ./scripts/deploy_back_test.sh"
