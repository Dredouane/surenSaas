#!/bin/bash
# Script de vérification des secrets GCP pour le déploiement

echo "=========================================="
echo "🔍 VÉRIFICATION DES SECRETS GCP"
echo "=========================================="
echo ""

# Vérifier les variables du .bashrc
echo "📋 Variables dans ~/.bashrc :"
echo "  SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN: ${SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN:0:20}..."
echo "  TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME: $TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME"
echo "  SUREN_GOOGLE_GEMINI_CREDENTIALS_B64: ${SUREN_GOOGLE_GEMINI_CREDENTIALS_B64:0:20}..."
echo "  SUREN_GMAIL_OAUTH_CLIENT_ID: ${SUREN_GMAIL_OAUTH_CLIENT_ID:0:20}..."
echo "  SUREN_GMAIL_OAUTH_CLIENT_SECRET: ${SUREN_GMAIL_OAUTH_CLIENT_SECRET:0:20}..."
echo "  SUREN_GMAIL_OAUTH_REFRESH_TOKEN: ${SUREN_GMAIL_OAUTH_REFRESH_TOKEN:0:20}..."
echo "  SUREN_GMAIL_ACCOUNT: ${SUREN_GMAIL_ACCOUNT:-REDACTED_EMAIL}"
echo ""

# Charger .env.test
if [ -f .env.test ]; then
    source .env.test
    echo "✅ .env.test chargé"
    echo "  GCP_PROJECT_ID: $GCP_PROJECT_ID"
    echo ""
else
    echo "❌ .env.test non trouvé"
    exit 1
fi

# Vérifier les secrets dans GCP
echo "🔐 Secrets dans GCP Secret Manager :"
echo ""

for secret in "test-telegram-bot-token" "test-telegram-bot-username" "test-google-gemini-credentials" "gmail-oauth-client-id" "gmail-oauth-client-secret" "gmail-oauth-refresh-token" "gmail-account"; do
    echo -n "  $secret: "
    if gcloud secrets describe $secret --project=$GCP_PROJECT_ID > /dev/null 2>&1; then
        echo "✅ EXISTE"
        # Vérifier s'il y a des versions
        versions=$(gcloud secrets versions list $secret --project=$GCP_PROJECT_ID --format="value(name)" 2>/dev/null | wc -l)
        echo "    Versions: $versions"
    else
        echo "❌ N'EXISTE PAS"
    fi
done

echo ""
echo "=========================================="
echo "💡 RECOMMANDATIONS :"
echo "=========================================="
echo ""

if [ -z "$SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN" ]; then
    echo "❌ SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN n'est pas défini dans ~/.bashrc"
    echo "   Ajoutez-le: export SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN='votre_token'"
    echo ""
fi

if [ -z "$SUREN_GOOGLE_GEMINI_CREDENTIALS_B64" ]; then
    echo "❌ SUREN_GOOGLE_GEMINI_CREDENTIALS_B64 n'est pas défini dans ~/.bashrc"
    echo "   Ajoutez-le: export SUREN_GOOGLE_GEMINI_CREDENTIALS_B64='...'"
    echo ""
fi

if [ -z "$SUREN_GMAIL_OAUTH_CLIENT_ID" ]; then
    echo "❌ SUREN_GMAIL_OAUTH_CLIENT_ID n'est pas défini dans ~/.bashrc"
    echo "   Ajoutez-le: export SUREN_GMAIL_OAUTH_CLIENT_ID='votre-client-id'"
    echo ""
fi

if [ -z "$SUREN_GMAIL_OAUTH_CLIENT_SECRET" ]; then
    echo "❌ SUREN_GMAIL_OAUTH_CLIENT_SECRET n'est pas défini dans ~/.bashrc"
    echo "   Ajoutez-le: export SUREN_GMAIL_OAUTH_CLIENT_SECRET='votre-client-secret'"
    echo ""
fi

if [ -z "$SUREN_GMAIL_OAUTH_REFRESH_TOKEN" ]; then
    echo "❌ SUREN_GMAIL_OAUTH_REFRESH_TOKEN n'est pas défini dans ~/.bashrc"
    echo "   Ajoutez-le: export SUREN_GMAIL_OAUTH_REFRESH_TOKEN='votre-refresh-token'"
    echo ""
fi

echo "Pour créer les secrets manquants :"
echo "  ./scripts/deploy_back_test.sh"
