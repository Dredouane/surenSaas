#!/bin/bash
# Script pour afficher les commandes SQL à copier dans Supabase SQL Editor
# Usage: ./scripts/show-sql.sh

set -e

YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=========================================="
echo "  SQL À COPIER DANS SUPABASE"
echo "=========================================="
echo ""
echo -e "${BLUE}Ouvre : https://supabase.com/dashboard/project/REDACTED/sql/new${NC}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT : Exécute chaque fichier dans l'ordre !${NC}"
echo ""

# Liste des fichiers dans l'ordre
FILES=(
    "db/schema/001_organizations.sql:1. Organizations (table racine)"
    "db/schema/002_users.sql:2. Users (profils)"
    "db/schema/003_pre_authorized_emails.sql:3. Pre-authorized emails (invitations)"
    "db/schema/004_user_org_membership.sql:4. User-Org Membership"
    "db/schema/005_auth_triggers.sql:5. Auth Triggers (automatisation)"
    "db/policies/auth_rls.sql:6. RLS Policies (sécurité)"
)

for item in "${FILES[@]}"; do
    IFS=':' read -r file description <<< "$item"
    
    echo "=========================================="
    echo -e "${GREEN}FICHIER: $description${NC}"
    echo "=========================================="
    echo ""
    cat "$file"
    echo ""
    echo -e "${YELLOW}>>> Copie ce SQL dans Supabase et clique 'Run'${NC}"
    echo -e "${YELLOW}>>> Puis appuie sur Entrée pour voir le suivant...${NC}"
    echo ""
    read
    clear
done

echo "=========================================="
echo -e "${GREEN}✅ TOUS LES SCRIPTS SONT AFFICHÉS !${NC}"
echo "=========================================="
echo ""
echo "Maintenant, crée l'organisation TEST:"
echo ""
echo "=========================================="
echo "CRÉER ORGANISATION TEST"
echo "=========================================="
echo ""
cat << 'SQL'
-- Créer l'organisation de test
INSERT INTO organizations (slug, name) 
VALUES ('test-ma-societe', 'Ma Société - TEST')
RETURNING id, slug;
SQL
echo ""
echo -e "${YELLOW}Copie ce SQL, exécute-le, et note l'UUID retourné${NC}"
echo ""
echo "Puis mets cet UUID dans .env.test.local :"
echo "TEST_ORG_ID=<uuid-affiché>"
