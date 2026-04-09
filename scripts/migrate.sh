#!/bin/bash
# Script pour exécuter les migrations SQL sur Supabase

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Charger les variables d'environnement
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Vérifier que DATABASE_URL est défini
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ Erreur: DATABASE_URL non défini${NC}"
    echo "Ajoutez-le dans le fichier .env ou exportez-le:"
    echo "export DATABASE_URL=REDACTED_DB_URL"
    exit 1
fi

# Fonction pour exécuter un fichier SQL
execute_sql() {
    local file=$1
    echo -e "${YELLOW}▶ Exécution de: $(basename $file)${NC}"
    
    if psql "$DATABASE_URL" -f "$file" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Succès${NC}"
        return 0
    else
        echo -e "${RED}❌ Échec${NC}"
        return 1
    fi
}

echo "=========================================="
echo "  Migrations SurenSaaS Database"
echo "=========================================="
echo ""

# Schéma de base (ordre important)
echo -e "${YELLOW}📦 Schéma de base...${NC}"
for file in db/schema/*.sql; do
    if [ -f "$file" ]; then
        execute_sql "$file"
    fi
done

echo ""
echo -e "${YELLOW}🔒 Policies RLS...${NC}"
for file in db/policies/*.sql; do
    if [ -f "$file" ]; then
        execute_sql "$file"
    fi
done

echo ""
echo -e "${GREEN}✅ Toutes les migrations sont terminées!${NC}"
