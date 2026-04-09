#!/bin/bash
# Script d'initialisation complète de la base de données
# Usage: ./scripts/init-db.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "  INITIALISATION BASE DE DONNÉES"
echo "=========================================="
echo ""

# Vérifier DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    if [ -f .env.test ]; then
        export $(cat .env.test | grep -v '^#' | grep DATABASE_URL | xargs)
    fi
fi

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ Erreur: DATABASE_URL non défini${NC}"
    echo ""
    echo "Options:"
    echo "  1. Ajoutez DATABASE_URL dans .env.test"
    echo "  2. Ou exportez directement:"
    echo "     export DATABASE_URL=REDACTED_DB_URL"
    exit 1
fi

echo -e "${BLUE}📂 Dossier des scripts: db/schema/${NC}"
echo ""

# Fonction pour exécuter un script
run_script() {
    local file=$1
    local name=$(basename $file)
    
    echo -e "${YELLOW}▶ $name${NC}"
    
    if psql "$DATABASE_URL" -f "$file" > /tmp/db_init.log 2>&1; then
        echo -e "${GREEN}  ✅ OK${NC}"
        return 0
    else
        echo -e "${RED}  ❌ ERREUR${NC}"
        echo ""
        cat /tmp/db_init.log
        return 1
    fi
}

# Exécuter les scripts dans l'ordre
SCRIPTS=(
    "db/schema/001_organizations.sql"
    "db/schema/002_users.sql"
    "db/schema/003_pre_authorized_emails.sql"
    "db/schema/004_user_org_membership.sql"
    "db/schema/005_auth_triggers.sql"
    "db/policies/auth_rls.sql"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        run_script "$script" || exit 1
    else
        echo -e "${RED}❌ Script non trouvé: $script${NC}"
        exit 1
    fi
done

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Base de données initialisée!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}Prochaines étapes:${NC}"
echo ""
echo "1. Créer l'organisation TEST:"
echo "   Dans Supabase SQL Editor:"
echo ""
echo "   INSERT INTO organizations (slug, name)"
echo "   VALUES ('test-ma-societe', 'Ma Société - TEST')"
echo "   RETURNING id;"
echo ""
echo "2. Copier l'UUID affiché dans .env.test.local:"
echo "   TEST_ORG_ID=<uuid-affiché>"
echo ""
echo "3. Inviter ton premier utilisateur (toi-même):"
echo ""
echo "   INSERT INTO pre_authorized_emails (email, org_id, role)"
echo "   VALUES ('ton-email@test.com', '<uuid-org>', 'admin');"
