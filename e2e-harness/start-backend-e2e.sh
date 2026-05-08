#!/usr/bin/env bash
# Backend launcher for E2E tests — extraction statique des vars du .bashrc
set -euo pipefail

cd /opt/projects/suren/saas/surenSaas/surenSaasBack

# ── Extraire les variables du .bashrc sans le sourcer (contourne PS1 guard) ──
if [ -f ~/.bashrc ]; then
  while IFS='=' read -r key value; do
    # Ignorer lignes vides, commentaires, et la ligne [ -z "$PS1" ] && return
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# || "$key" =~ ^\[ ]] && continue
    # Ne garder que les export avec les préfixes qui nous intéressent
    if [[ "$key" =~ ^export[[:space:]]+(SUPABASE|TELEGRAM|GOOGLE|VERTEX|OPENAI|SUREN|TEST|JWT|GCP|ALLOWED|ORG) ]]; then
      local k="${key#export }"
      # Nettoyer les guillemets autour de la valeur
      local v="${value%\"}"; v="${v#\"}"
      export "$k=$v"
    fi
  done < <(grep '^export ' ~/.bashrc)
fi

# ── Fallbacks hardcodés si .bashrc n'a pas fourni certaines vars critiques ──
export ENVIRONMENT=test
export SUPABASE_URL="${SUPABASE_URL:-https://REDACTED.supabase.co}"
export SUPABASE_SERVICE_KEY="${TEST_SUPABASE_SERVICE_KEY:-${SUPABASE_SERVICE_KEY:-REDACTED_JWT}}"
export JWT_SECRET="${TEST_JWT_SECRET:-938ed98cdea8b20b6f093d6f03aa2696c0532a6ab1b5b291e5e7084e326d26b9}"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://localhost:3000}"
export TELEGRAM_CONSTRUCTION_BOT_TOKEN="${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN:-REDACTED_BOT_TOKEN}"
export TELEGRAM_CONSTRUCTION_BOT_USERNAME="${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_USERNAME:-suren_construction_test_bot}"
export TELEGRAM_API_URL="${TELEGRAM_API_URL:-http://localhost:8081}"
export GOOGLE_API_KEY="${SUREN_GEMINI_API_KEY:-REDACTED_GEMINI_KEY}"
export GEMINI_API_KEY="${GOOGLE_API_KEY}"

# ── Activer le venv et lancer ──
source venv/bin/activate

exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1 --log-level info 2>/tmp/backend_e2e_error.log
