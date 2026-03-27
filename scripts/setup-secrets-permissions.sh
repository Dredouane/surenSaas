#!/bin/bash
# Script pour donner les permissions aux secrets GCP

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=========================================="
echo -e "${YELLOW}🔐 CONFIGURATION PERMISSIONS SECRETS${NC}"
echo "=========================================="
echo ""

# Charger l'env
set -a
source .env.test
set +a

SERVICE_ACCOUNT="$GCP_PROJECT_ID-compute@developer.gserviceaccount.com"

echo "Service account: $SERVICE_ACCOUNT"
echo ""

# Donner accès à tous les secrets
echo -e "${YELLOW}Attribution du rôle Secret Accessor...${NC}"

for SECRET in supabase-url supabase-service-key-test jwt-secret-test; do
    echo "  - $SECRET"
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$GCP_PROJECT_ID > /dev/null 2>&1
done

echo ""
echo -e "${GREEN}✅ Permissions configurées!${NC}"
echo ""
echo "Tu peux maintenant redéployer:"
echo "  ./scripts/deploy_back_test.sh"
