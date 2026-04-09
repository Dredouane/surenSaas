#!/bin/bash
# Script pour configurer le webhook du bot Telegram Construction
# Ce script charge les variables depuis le bashrc et le .env

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Charger les variables du bashrc si elles existent
if [ -f "$HOME/.bashrc" ]; then
    echo -e "${BLUE}Chargement des variables depuis ~/.bashrc...${NC}"
    # Extraire les variables SUREN_* du bashrc
    while IFS= read -r line; do
        if [[ "$line" =~ ^export\ (SUREN_[A-Z_]+)=(.+)$ ]]; then
            var_name="${BASH_REMATCH[1]}"
            var_value="${BASH_REMATCH[2]}"
            # Supprimer les guillemets simples et doubles au début et à la fin
            var_value="${var_value#\"}"
            var_value="${var_value%\"}"
            var_value="${var_value#\'}"
            var_value="${var_value%\'}"
            export "$var_name=$var_value"
            echo -e "  ${GREEN}✓${NC} $var_name"
        fi
    done < "$HOME/.bashrc"
fi

# Vérifier les arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Usage: $0 --env {test|prod} [--delete]${NC}"
    echo ""
    echo "Options:"
    echo "  --env {test|prod}  Environnement (test ou prod)"
    echo "  --delete          Supprimer le webhook au lieu de le configurer"
    echo ""
    echo "Variables attendues dans ~/.bashrc:"
    echo "  export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN=\"...\""
    echo "  export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME=\"...\""
    echo "  export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN=\"...\""
    echo "  export SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_USERNAME=\"...\""
    exit 1
fi

# Parser les arguments
ENV=""
DELETE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV="$2"
            shift 2
            ;;
        --delete)
            DELETE=true
            shift
            ;;
        *)
            echo -e "${RED}Option inconnue: $1${NC}"
            exit 1
            ;;
    esac
done

# Vérifier l'environnement
if [[ ! "$ENV" =~ ^(test|prod)$ ]]; then
    echo -e "${RED}Erreur: Environnement doit être 'test' ou 'prod'${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Configuration Bot Telegram Construction${NC}"
echo -e "${BLUE}  Environnement: $ENV${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Déterminer les variables à utiliser
if [ "$ENV" = "test" ]; then
    TOKEN_VAR="SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN"
    USERNAME_VAR="SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME"
else
    TOKEN_VAR="SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_TOKEN"
    USERNAME_VAR="SUREN_PROD_TELEGRAM_CONSTRUCTION_BOT_USERNAME"
fi

# Vérifier que les variables sont définies
TOKEN="${!TOKEN_VAR}"
USERNAME="${!USERNAME_VAR}"

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Erreur: $TOKEN_VAR non définie${NC}"
    echo ""
    echo "Assurez-vous d'avoir défini la variable dans ~/.bashrc:"
    echo "  export $TOKEN_VAR=\"votre_token_ici\""
    exit 1
fi

if [ -z "$USERNAME" ]; then
    echo -e "${RED}❌ Erreur: $USERNAME_VAR non définie${NC}"
    exit 1
fi

# Vérifier que API_URL est défini
API_URL="${API_URL:-}"
if [ -z "$API_URL" ]; then
    # Essayer de charger depuis le .env
    if [ -f ".env.$ENV" ]; then
        API_URL=$(grep "^API_URL=" ".env.$ENV" | cut -d'=' -f2 | tr -d '"')
    fi
    
    if [ -z "$API_URL" ]; then
        echo -e "${RED}❌ Erreur: API_URL non défini${NC}"
        echo ""
        echo "Définissez API_URL dans .env.$ENV ou en variable d'environnement"
        exit 1
    fi
fi

echo -e "${BLUE}Configuration:${NC}"
echo "  Bot: @$USERNAME"
echo "  API URL: $API_URL"
echo ""

# Construire l'URL du webhook
WEBHOOK_URL="${API_URL%/}/api/v1/webhook/construction"

if [ "$DELETE" = true ]; then
    echo -e "${YELLOW}🗑️  Suppression du webhook...${NC}"
    
    RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TOKEN}/deleteWebhook" 2>&1)
    
    if echo "$RESPONSE" | grep -q '"ok":true'; then
        echo -e "${GREEN}✅ Webhook supprimé avec succès!${NC}"
        exit 0
    else
        echo -e "${RED}❌ Erreur lors de la suppression:${NC}"
        echo "$RESPONSE"
        exit 1
    fi
else
    echo -e "${YELLOW}🔧 Configuration du webhook...${NC}"
    echo "  URL: $WEBHOOK_URL"
    echo ""
    
    # Vérifier le bot
    echo -e "${BLUE}Vérification du bot...${NC}"
    ME_RESPONSE=$(curl -s "https://api.telegram.org/bot${TOKEN}/getMe")
    
    if ! echo "$ME_RESPONSE" | grep -q '"ok":true'; then
        echo -e "${RED}❌ Erreur: Token invalide${NC}"
        echo "Réponse: $ME_RESPONSE"
        exit 1
    fi
    
    BOT_NAME=$(echo "$ME_RESPONSE" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
    echo -e "  ${GREEN}✓${NC} Bot connecté: @$BOT_NAME"
    echo ""
    
    # Configurer le webhook
    echo -e "${BLUE}Configuration du webhook...${NC}"
    WEBHOOK_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
        -H "Content-Type: application/json" \
        -d "{\"url\":\"${WEBHOOK_URL}\",\"allowed_updates\":[\"message\",\"callback_query\"]}")
    
    if echo "$WEBHOOK_RESPONSE" | grep -q '"ok":true'; then
        echo -e "  ${GREEN}✓${NC} Webhook configuré"
        
        # Vérifier les infos
        INFO_RESPONSE=$(curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo")
        
        echo ""
        echo -e "${BLUE}📊 Informations webhook:${NC}"
        
        WEBHOOK_URL_RESULT=$(echo "$INFO_RESPONSE" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
        PENDING_UPDATES=$(echo "$INFO_RESPONSE" | grep -o '"pending_update_count":[0-9]*' | cut -d':' -f2)
        
        echo "  URL: $WEBHOOK_URL_RESULT"
        echo "  Pending updates: $PENDING_UPDATES"
        
        if echo "$INFO_RESPONSE" | grep -q '"last_error_date"'; then
            LAST_ERROR=$(echo "$INFO_RESPONSE" | grep -o '"last_error_message":"[^"]*"' | cut -d'"' -f4)
            echo -e "  ${RED}⚠️  Dernier erreur: $LAST_ERROR${NC}"
        fi
        
        echo ""
        echo -e "${GREEN}✅ Configuration terminée!${NC}"
        echo ""
        echo "Pour tester, envoyez une facture à @$USERNAME"
        
    else
        echo -e "${RED}❌ Erreur configuration webhook:${NC}"
        echo "$WEBHOOK_RESPONSE"
        exit 1
    fi
fi
