#!/bin/bash
# Script pour configurer les variables d'environnement dans ~/.bashrc
# Usage: source ./scripts/setup-local-env.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🔐 CONFIGURATION ENVIRONNEMENT LOCAL${NC}"
echo "=========================================="
echo ""

BASHRC="$HOME/.bashrc"

# Fonction pour ajouter une variable si elle n'existe pas
add_to_bashrc() {
    local var_name=$1
    local var_value=$2
    local comment=$3
    
    if grep -q "^export $var_name=" "$BASHRC" 2>/dev/null; then
        echo -e "${YELLOW}  ⚠️  $var_name existe déjà dans ~/.bashrc${NC}"
        read -p "Voulez-vous le mettre à jour? (o/N): " update
        if [[ $update =~ ^[Oo]$ ]]; then
            # Supprimer l'ancienne ligne
            sed -i "/^export $var_name=/d" "$BASHRC"
            sed -i "/^# $var_name/d" "$BASHRC"
        else
            return
        fi
    fi
    
    # Ajouter la variable
    echo "" >> "$BASHRC"
    if [ -n "$comment" ]; then
        echo "# $comment" >> "$BASHRC"
    fi
    echo "export $var_name=\"$var_value\"" >> "$BASHRC"
    echo -e "${GREEN}  ✅ $var_name ajouté${NC}"
}

echo -e "${BLUE}📝 Ce script va ajouter les variables dans ~/.bashrc${NC}"
echo ""
echo -e "${YELLOW}Variables nécessaires pour TEST:${NC}"
echo "  - TEST_SUPABASE_SERVICE_KEY"
echo "  - TEST_JWT_SECRET"
echo ""
echo -e "${YELLOW}Variables nécessaires pour PROD:${NC}"
echo "  - PROD_SUPABASE_SERVICE_KEY"
echo "  - PROD_JWT_SECRET"
echo ""

read -p "Configurer l'environnement TEST? (O/n): " setup_test
if [[ ! $setup_test =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${BLUE}Configuration TEST:${NC}"
    
    echo -n "Entrez TEST_SUPABASE_SERVICE_KEY: "
    read -s test_supabase_key
    echo ""
    add_to_bashrc "TEST_SUPABASE_SERVICE_KEY" "$test_supabase_key" "SurenSaaS - Test Supabase Service Key"
    
    echo ""
    echo -n "Entrez TEST_JWT_SECRET (min 32 caractères): "
    read -s test_jwt
    echo ""
    add_to_bashrc "TEST_JWT_SECRET" "$test_jwt" "SurenSaaS - Test JWT Secret"
fi

echo ""
read -p "Configurer l'environnement PROD? (o/N): " setup_prod
if [[ $setup_prod =~ ^[Oo]$ ]]; then
    echo ""
    echo -e "${BLUE}Configuration PROD:${NC}"
    
    echo -n "Entrez PROD_SUPABASE_SERVICE_KEY: "
    read -s prod_supabase_key
    echo ""
    add_to_bashrc "PROD_SUPABASE_SERVICE_KEY" "$prod_supabase_key" "SurenSaaS - Prod Supabase Service Key"
    
    echo ""
    echo -n "Entrez PROD_JWT_SECRET (différent de TEST, min 32 caractères): "
    read -s prod_jwt
    echo ""
    add_to_bashrc "PROD_JWT_SECRET" "$prod_jwt" "SurenSaaS - Prod JWT Secret"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ CONFIGURATION TERMINÉE!${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}Pour appliquer les changements:${NC}"
echo "  source ~/.bashrc"
echo ""
echo -e "${YELLOW}Pour vérifier les variables:${NC}"
echo "  env | grep -E '^(TEST_|PROD_)'"
echo ""
echo -e "${BLUE}⚠️  Important:${NC}"
echo "  - Les variables sont maintenant dans ~/.bashrc"
echo "  - Ne commitez jamais ce fichier!"
echo "  - Elles seront utilisées automatiquement par les scripts de déploiement"
