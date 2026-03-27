#!/bin/bash
# Script de correction complète pour toutes les politiques RLS restantes
# Usage: ./scripts/fix-all-rls-policies.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "  CORRECTION COMPLÈTE RLS POLICIES"
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

echo -e "${BLUE}📋 Exécution de la migration 016_fix_all_remaining_rls_policies.sql...${NC}"
echo ""

if psql "$DATABASE_URL" -f "db/schema/016_fix_all_remaining_rls_policies.sql" > /tmp/fix_all_rls.log 2>&1; then
    echo -e "${GREEN}✅ Toutes les politiques RLS ont été corrigées avec succès!${NC}"
    echo ""
    echo -e "${BLUE}Tables corrigées :${NC}"
    echo "  • telegram_bots"
    echo "  • telegram_users"
    echo "  • telegram_audit"
    echo "  • companies"
    echo "  • organization_capabilities"
    echo "  • user_capabilities"
    echo "  • invoice_status_history"
    echo ""
    echo -e "${YELLOW}📝 Prochaines étapes :${NC}"
    echo "  1. Rafraîchir le dashboard (F5)"
    echo "  2. Vérifier que les bots Telegram apparaissent"
    echo "  3. Vérifier que les companies sont accessibles"
    echo ""
else
    echo -e "${RED}❌ Erreur lors de la correction${NC}"
    echo ""
    cat /tmp/fix_all_rls.log
    exit 1
fi
