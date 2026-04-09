#!/bin/bash
# Script de correction rapide pour le problème RLS
# Usage: ./scripts/fix-rls-policies.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "  CORRECTION RLS POLICIES"
echo "=========================================="
echo ""

# Vérifier DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    if [ -f .env.test ]; then
        export $(cat .env.test | grep -v '^#' | grep DATABASE_URL | xargs)
    elif [ -f .env ]; then
        export $(cat .env | grep -v '^#' | grep DATABASE_URL | xargs)
    fi
fi

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ Erreur: DATABASE_URL non défini${NC}"
    echo ""
    echo "Ajoutez DATABASE_URL dans .env ou .env.test"
    exit 1
fi

echo -e "${BLUE}📋 Exécution de la migration 015_fix_rls_policies.sql...${NC}"
echo ""

if psql "$DATABASE_URL" -f "db/schema/015_fix_rls_policies.sql" > /tmp/fix_rls.log 2>&1; then
    echo -e "${GREEN}✅ Politiques RLS corrigées avec succès!${NC}"
    echo ""
    echo -e "${BLUE}Résumé des changements :${NC}"
    echo "  • invoices : RLS basée sur users.org_id"
    echo "  • clients : RLS basée sur users.org_id"
    echo "  • invoice_status_history : RLS corrigée"
    echo ""
    echo -e "${YELLOW}📝 Prochaines étapes :${NC}"
    echo "  1. Rafraîchir le dashboard (F5)"
    echo "  2. Vérifier que les factures et clients apparaissent"
    echo ""
else
    echo -e "${RED}❌ Erreur lors de la correction${NC}"
    echo ""
    cat /tmp/fix_rls.log
    exit 1
fi
