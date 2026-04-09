#!/bin/bash
# Script pour désactiver RLS sur toutes les tables
# Usage: ./scripts/disable-rls-all.sh [environment]

set -e

ENV=${1:-test}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔐 Désactivation RLS sur toutes les tables"
echo "=========================================="
echo "Environnement: $ENV"
echo ""

# Vérifier que le fichier de migration existe
MIGRATION_FILE="$PROJECT_ROOT/db/schema/019_disable_all_rls.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Fichier de migration non trouvé: $MIGRATION_FILE"
    exit 1
fi

echo "📄 Fichier de migration: $MIGRATION_FILE"
echo ""

# Charger les variables d'environnement
ENV_FILE="$PROJECT_ROOT/.env.$ENV"

if [ -f "$ENV_FILE" ]; then
    echo "📂 Chargement de $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "⚠️  Fichier $ENV_FILE non trouvé, utilisation des variables existantes"
fi

# Vérifier que SUPABASE_DB_URL est défini
if [ -z "$SUPABASE_DB_URL" ]; then
    echo "❌ SUPABASE_DB_URL non défini"
    echo "   Définissez-le dans .env.$ENV ou en variable d'environnement"
    exit 1
fi

echo "🗄️  Connexion à la base de données..."
echo ""

# Exécuter la migration
echo "⚡ Exécution de la migration 019_disable_all_rls.sql..."
psql "$SUPABASE_DB_URL" -f "$MIGRATION_FILE"

echo ""
echo "✅ Migration terminée avec succès!"
echo ""
echo "📊 Tables concernées:"
echo "   - organizations"
echo "   - users"
echo "   - pre_authorized_emails"
echo "   - organization_capabilities"
echo "   - user_capabilities"
echo "   - companies"
echo "   - clients"
echo "   - invoices"
echo "   - invoice_items"
echo "   - invoice_status_history"
echo "   - telegram_bots"
echo "   - telegram_users"
echo "   - telegram_audit"
echo ""
echo "🔒 Note: RLS est maintenant désactivé."
echo "   Le contrôle d'accès est géré par l'application (capabilities)."
