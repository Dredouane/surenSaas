#!/usr/bin/env bash
# Backend launcher for E2E tests — extraction statique des vars du .bashrc
set -euo pipefail

cd /opt/projects/suren/saas/surenSaas/surenSaasBack

# ── Extraire les variables du .bashrc sans le sourcer (contourne PS1 guard) ──
if [ -f ~/.bashrc ]; then
  while IFS='=' read -r key value; do
    # Ignorer lignes vides, commentaires, et la ligne [ -z "$PS1" ] && return
    [ -z "$key" ] && continue
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ "$key" =~ ^\[ ]] && continue
    # Ne garder que les export avec les préfixes qui nous intéressent
    if [[ "$key" =~ ^export[[:space:]]+(SUPABASE|TELEGRAM|GOOGLE|VERTEX|OPENAI|SUREN|TEST|JWT|GCP|ALLOWED|ORG) ]]; then
      clean_key="${key#export }"
      # Nettoyer les guillemets autour de la valeur
      clean_value="${value%\"}"; clean_value="${clean_value#\"}"
      export "$clean_key=$clean_value"
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

# ── Kill any previous process on port 8080 ──
if lsof -ti :8080 >/dev/null 2>&1; then
  echo "   ⚠️ Killing old process on port 8080..."
  lsof -ti :8080 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# ── Activer le venv et lancer en arrière-plan ──
source venv/bin/activate

# Lancer uvicorn en arrière-plan, détaché du job control du script
# nohup + disown évite que SIGHUP tue uvicorn quand le script se termine
nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1 --log-level info > /dev/null 2>/tmp/backend_e2e_error.log &
UVICORN_PID=$!
disown $UVICORN_PID
echo "$UVICORN_PID" > /tmp/backend_uvicorn_pid.txt

# Attendre que le backend soit prêt (jusqu'à 90s pour le warm-up Vertex AI)
for i in $(seq 1 45); do
  if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo "   ✅ Backend healthy after ~$((i*2))s"
    exit 0
  fi
  sleep 2
done

echo "❌ Backend did not become healthy within 90s"
echo "=== Last 30 lines of /tmp/backend_e2e_error.log ==="
tail -30 /tmp/backend_e2e_error.log 2>/dev/null || echo "(no log)"
kill $UVICORN_PID 2>/dev/null || true
exit 1
