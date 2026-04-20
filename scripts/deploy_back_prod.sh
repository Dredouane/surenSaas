#!/bin/bash
# Script de déploiement du BACKEND PRODUCTION sur GCP Cloud Run

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${RED}🚀 DEPLOIEMENT BACKEND PRODUCTION${NC}"
echo -e "${RED}⚠️  ATTENTION: Environnement de production${NC}"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Vérification de sécurité
read -p "Êtes-vous sûr de vouloir déployer en PRODUCTION? (tapez 'prod' pour confirmer): " confirm
if [ "$confirm" != "prod" ]; then
    echo -e "${YELLOW}❌ Déploiement annulé${NC}"
    exit 0
fi

echo ""

# Charger l'environnement PROD (sans secrets)
if [ ! -f .env.prod ]; then
    echo -e "${RED}❌ Erreur: .env.prod non trouvé${NC}"
    echo "Créez-le à partir du template: cp .env.prod.example .env.prod"
    exit 1
fi

echo -e "${BLUE}📋 Chargement de .env.prod...${NC}"
set -a
source .env.prod
set +a

# Vérifier les variables du .bashrc
echo ""
echo -e "${YELLOW}🔐 Vérification des secrets dans ~/.bashrc...${NC}"
MISSING_VARS=()

if [ -z "$PROD_SUPABASE_SERVICE_KEY" ]; then
    MISSING_VARS+=("PROD_SUPABASE_SERVICE_KEY")
fi

if [ -z "$PROD_JWT_SECRET" ]; then
    MISSING_VARS+=("PROD_JWT_SECRET")
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Variables manquantes dans ~/.bashrc:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo -e "${BLUE}Pour les configurer:${NC}"
    echo "  ./scripts/setup-local-env.sh"
    exit 1
fi

# Gemini est optionnel (désactivé temporairement)
# Utilise SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 depuis .bashrc (partagé test/prod)
HAS_GEMINI=false
if [ ! -z "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64" ]; then
    HAS_GEMINI=true
fi

# Gmail OAuth2 (partagé test/prod - même compte Gmail)
HAS_GMAIL=false
if [ ! -z "$SUREN_GMAIL_OAUTH_CLIENT_ID" ] && [ ! -z "$SUREN_GMAIL_OAUTH_CLIENT_SECRET" ] && [ ! -z "$SUREN_GMAIL_OAUTH_REFRESH_TOKEN" ]; then
    HAS_GMAIL=true
fi

# Cloudflare R2 (obligatoire - stockage de fichiers)
HAS_R2=false
if [ ! -z "$SUREN_GED_CLOUDFLARE_TOKEN" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT" ] && [ ! -z "$SUREN_GED_CLOUDFLARE_BUCKET_NAME" ]; then
    HAS_R2=true
fi

echo -e "${GREEN}✅ Secrets trouvés dans ~/.bashrc${NC}"
if [ "$HAS_GEMINI" = true ]; then
    echo -e "${GREEN}✅ SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 trouvé (Gemini activé)${NC}"
else
    echo -e "${YELLOW}⚠️  SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 non défini (Gemini désactivé)${NC}"
fi
if [ "$HAS_GMAIL" = true ]; then
    echo -e "${GREEN}✅ SUREN_GMAIL_OAUTH_* trouvé (Module Emails activé)${NC}"
else
    echo -e "${YELLOW}⚠️  SUREN_GMAIL_OAUTH_* non défini (Module Emails désactivé)${NC}"
fi
if [ "$HAS_R2" = true ]; then
    echo -e "${GREEN}✅ Credentials Cloudflare R2 trouvés (Stockage GED activé)${NC}"
else
    echo -e "${RED}❌ Credentials Cloudflare R2 manquants - Le stockage de fichiers ne fonctionnera pas${NC}"
    echo "   Variables requises dans ~/.bashrc:"
    echo "   - SUREN_GED_CLOUDFLARE_TOKEN"
    echo "   - SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID"
    echo "   - SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY"
    echo "   - SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT"
    echo "   - SUREN_GED_CLOUDFLARE_BUCKET_NAME"
    exit 1
fi

# Vérification de sécurité: JWT différent de TEST
if [ ! -z "$TEST_JWT_SECRET" ] && [ "$PROD_JWT_SECRET" = "$TEST_JWT_SECRET" ]; then
    echo -e "${RED}❌ ERREUR CRITIQUE: PROD_JWT_SECRET identique à TEST_JWT_SECRET!${NC}"
    echo "Modifiez ~/.bashrc avec des secrets différents pour la sécurité."
    exit 1
fi

# Vérifier les variables GCP
if [ -z "$GCP_PROJECT_ID" ] || [ -z "$PROD_BACK_SERVICE_NAME" ]; then
    echo -e "${RED}❌ Erreur: Variables GCP manquantes dans .env.prod${NC}"
    exit 1
fi

echo ""

# Fonction pour créer/mettre à jour un secret GCP
create_or_update_secret() {
    local name=$1
    local value=$2
    
    if gcloud secrets describe "$name" --project="$GCP_PROJECT_ID" > /dev/null 2>&1; then
        echo -e "${YELLOW}  Mise à jour du secret: $name${NC}"
        echo -n "$value" | gcloud secrets versions add "$name" --data-file=- --project="$GCP_PROJECT_ID" > /dev/null 2>&1
        
        # Nettoyer les anciennes versions (garder uniquement la plus récente)
        echo -e "${BLUE}  Nettoyage des anciennes versions...${NC}"
        # Lister toutes les versions et supprimer les anciennes
        local versions
        versions=$(gcloud secrets versions list "$name" --project="$GCP_PROJECT_ID" --format="value(name)" --sort-by="~createTime" 2>/dev/null || echo "")
        if [ ! -z "$versions" ]; then
            local count=0
            for version in $versions; do
                if [ $count -ge 1 ]; then
                    # Supprimer les versions anciennes (garder seulement la plus récente)
                    gcloud secrets versions destroy "$version" --secret="$name" --project="$GCP_PROJECT_ID" --quiet > /dev/null 2>&1
                    echo -e "${BLUE}    Version $version supprimée${NC}"
                fi
                ((count++))
            done
        fi
    else
        echo -e "${BLUE}  Création du secret: $name${NC}"
        echo -n "$value" | gcloud secrets create "$name" --data-file=- --project="$GCP_PROJECT_ID" \
            --replication-policy user-managed --locations "$GCP_REGION" > /dev/null 2>&1
    fi
    echo -e "${GREEN}  ✅ $name${NC}"
}

# Créer/mettre à jour les secrets GCP
echo -e "${YELLOW}🔐 Configuration des secrets GCP...${NC}"
create_or_update_secret "supabase-url" "$SUPABASE_URL"
create_or_update_secret "prod-supabase-service-key" "$PROD_SUPABASE_SERVICE_KEY"
create_or_update_secret "prod-jwt-secret" "$PROD_JWT_SECRET"

# Gemini (optionnel)
if [ "$HAS_GEMINI" = true ]; then
    create_or_update_secret "prod-google-gemini-credentials" "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64"
fi

# Gmail OAuth2 (optionnel, mais recommandé)
if [ "$HAS_GMAIL" = true ]; then
    create_or_update_secret "gmail-oauth-client-id" "$SUREN_GMAIL_OAUTH_CLIENT_ID"
    create_or_update_secret "gmail-oauth-client-secret" "$SUREN_GMAIL_OAUTH_CLIENT_SECRET"
    create_or_update_secret "gmail-oauth-refresh-token" "$SUREN_GMAIL_OAUTH_REFRESH_TOKEN"
    create_or_update_secret "gmail-account" "${SUREN_GMAIL_ACCOUNT:-REDACTED_EMAIL}"
fi

# Cloudflare R2 (obligatoire)
if [ "$HAS_R2" = true ]; then
    create_or_update_secret "r2-endpoint-url" "$SUREN_GED_CLOUDFLARE_S3_EU_ENDPOINT"
    create_or_update_secret "r2-access-key-id" "$SUREN_GED_CLOUDFLARE_ACCESS_KEY_ID"
    create_or_update_secret "r2-secret-access-key" "$SUREN_GED_CLOUDFLARE_SECRET_ACCESS_KEY"
    create_or_update_secret "r2-token" "$SUREN_GED_CLOUDFLARE_TOKEN"
    create_or_update_secret "r2-bucket-name" "$SUREN_GED_CLOUDFLARE_BUCKET_NAME"
fi

echo ""

# Déploiement
echo -e "${RED}🚀 Déploiement Backend PRODUCTION...${NC}"
cd surenSaasBack

# Calculer les origines CORS
CORS_ORIGINS=""
FRONT_URL=$(gcloud run services describe $PROD_FRONT_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null || echo "")

if [ ! -z "$FRONT_URL" ]; then
    CORS_ORIGINS="$FRONT_URL"
else
    CORS_ORIGINS="https://$PROD_FRONT_SERVICE_NAME-$GCP_REGION-run.app"
fi

# Créer un fichier temporaire pour les variables d'environnement
ENV_FILE=$(mktemp)
cat > $ENV_FILE << EOF
ALLOWED_ORIGINS: "$CORS_ORIGINS"
ENVIRONMENT: "production"
ORG_ID: "$PROD_ORG_ID"
DEBUG: "false"
EOF

# Préparer les secrets
SECRETS="SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=prod-supabase-service-key:latest,JWT_SECRET=prod-jwt-secret:latest"
if [ "$HAS_GEMINI" = true ]; then
    SECRETS="$SECRETS,GOOGLE_GEMINI_CREDENTIALS_B64=prod-google-gemini-credentials:latest"
fi
if [ "$HAS_GMAIL" = true ]; then
    SECRETS="$SECRETS,SUREN_GMAIL_OAUTH_CLIENT_ID=gmail-oauth-client-id:latest,SUREN_GMAIL_OAUTH_CLIENT_SECRET=gmail-oauth-client-secret:latest,SUREN_GMAIL_OAUTH_REFRESH_TOKEN=gmail-oauth-refresh-token:latest,SUREN_GMAIL_ACCOUNT=gmail-account:latest"
fi
if [ "$HAS_R2" = true ]; then
    SECRETS="$SECRETS,R2_ENDPOINT_URL=r2-endpoint-url:latest,R2_ACCESS_KEY_ID=r2-access-key-id:latest,R2_SECRET_ACCESS_KEY=r2-secret-access-key:latest,R2_TOKEN=r2-token:latest"
fi

gcloud run deploy $PROD_BACK_SERVICE_NAME \
    --source . \
    --platform managed \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --allow-unauthenticated \
    --set-secrets "$SECRETS" \
    --env-vars-file $ENV_FILE \
    --memory 2Gi \
    --cpu 1 \
    --concurrency 100 \
    --max-instances 50 \
    --min-instances 1

# Nettoyer
rm -f $ENV_FILE

cd ..

# Récupérer l'URL
BACK_URL=$(gcloud run services describe $PROD_BACK_SERVICE_NAME \
    --region $GCP_REGION \
    --project $GCP_PROJECT_ID \
    --format 'value(status.url)' 2>/dev/null)

echo ""
echo "=========================================="
echo -e "${GREEN}✅ BACKEND PRODUCTION DÉPLOYÉ!${NC}"
echo "=========================================="
echo -e "${BLUE}⚙️  URL: $BACK_URL${NC}"
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "   gcloud logging tail --service=$PROD_BACK_SERVICE_NAME"

# Nettoyage Artifact Registry
echo ""
echo -e "${YELLOW}🧹 Nettoyage Artifact Registry...${NC}"
REPOSITORY="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/cloud-run-source-deploy/$PROD_BACK_SERVICE_NAME"

# Vérifier si le dépôt existe
if gcloud artifacts repositories describe "cloud-run-source-deploy" --location="$GCP_REGION" --project="$GCP_PROJECT_ID" > /dev/null 2>&1; then
    echo -e "${BLUE}  Dépôt trouvé: $REPOSITORY${NC}"
    
    # Lister toutes les images avec leurs timestamps
    IMAGES=$(gcloud artifacts docker images list "$REPOSITORY" --sort-by="~UPDATE_TIME" --format="value(digest)" 2>/dev/null || echo "")
    
    if [ ! -z "$IMAGES" ]; then
        echo -e "${BLUE}  Images trouvées: $(echo "$IMAGES" | wc -l)${NC}"
        
        # Garder seulement les 3 images les plus récentes
        local count=0
        for digest in $IMAGES; do
            if [ $count -ge 3 ]; then
                # Supprimer les images anciennes
                echo -e "${YELLOW}    Suppression de l'image: ${digest:0:20}...${NC}"
                gcloud artifacts docker images delete "$REPOSITORY@$digest" --quiet > /dev/null 2>&1
            fi
            ((count++))
        done
        
        echo -e "${GREEN}  ✅ Nettoyage Artifact Registry terminé (3 images conservées)${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Aucune image trouvée dans le dépôt${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠️  Dépôt Artifact Registry non trouvé${NC}"
fi
