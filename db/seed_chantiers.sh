#!/usr/bin/env bash
set -euo pipefail

SUPABASE_URL="${SUPABASE_URL:-}"
SUPABASE_SERVICE_KEY="${SUPABASE_SERVICE_KEY:-}"

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
  echo "Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"
  echo ""
  echo "Usage:"
  echo "  export SUPABASE_URL=\"https://REDACTED.supabase.co\""
  echo "  export SUPABASE_SERVICE_KEY=\"your-service-role-key\""
  echo "  $0"
  exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)/schema"

# Step 0: create the RPC proxy if not exists
echo "=== Étape 0/6 : Création RPC proxy exec_sql ==="
curl -s -X POST "${SUPABASE_URL}/rest/v1/rpc/exec_sql" \
  -H "apikey: ${SUPABASE_SERVICE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT 1"}' \
  --max-time 10 > /dev/null 2>&1

# If RPC doesn't exist yet, create it via a direct SQL approach
# We just assume it was created manually in SQL Editor

exec_sql() {
  local label="$1"
  local file="$2"
  echo "=== $label ==="

  # Read file and escape for JSON
  SQL=$(cat "$file")

  RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/rpc/exec_sql" \
    -H "apikey: ${SUPABASE_SERVICE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg sql "$SQL" '{"sql": $sql}')" \
    --max-time 30)

  if echo "$RESPONSE" | grep -qi "error"; then
    echo "❌ ERROR: $RESPONSE"
    exit 1
  fi
  echo "✅ OK"
}

echo ""
echo "=== Début du seed chantiers ==="
echo ""

exec_sql "Étape 1/6 : Tables, enums, indexes" "$DIR/028a_chantiers_tables.sql"
exec_sql "Étape 2/6 : Fonctions et triggers métier" "$DIR/028b_chantiers_fonctions.sql"
exec_sql "Étape 3/6 : Chantiers (6 chantiers)" "$DIR/029_chantiers_seed.sql"

for f in 029b 029c 029d 029e 029f 029g 029h 029i; do
  file=$(ls "$DIR/${f}_chantiers_seed_"*.sql 2>/dev/null | head -1)
  if [ -n "$file" ]; then
    exec_sql "Étape 4/6 : ${f}" "$file"
  fi
done

exec_sql "Étape 5/6 : Recalcul des métriques" "$DIR/029z_chantiers_seed_recalcul.sql"

exec_sql "Étape 6/6 : Reload PostgREST schema cache" <(echo "NOTIFY pgrst, 'reload schema';")

echo ""
echo "=== ✅ Seed terminé avec succès ==="
