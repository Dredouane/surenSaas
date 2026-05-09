#!/usr/bin/env bash
# ============================================================
# E2E Test Runner — Orchestre backend + tg-mock + tests
# ============================================================
# Usage:
#   ./scripts/run-e2e.sh                    # Mode tg-mock Docker (défaut)
#   ./scripts/run-e2e.sh --verbose          # Logs détaillés
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
E2E_DIR="$PROJECT_DIR/e2e-harness"
BACKEND_DIR="$PROJECT_DIR/surenSaasBack"

VERBOSE=false
for arg in "$@"; do
    case "$arg" in
        --verbose|-v) VERBOSE=true ;;
        --tg-mock|--use-tg-mock) ;;  # acceptés mais redondants (toujours actif)
    esac
done

echo "============================================"
echo "  E2E Test Runner"
echo "  Mode : tg-mock Docker (obligatoire)"
echo "============================================"
echo ""

# ── 1. Extraire les variables du .bashrc sans le sourcer (contourne PS1 guard) ──
if [ -f ~/.bashrc ]; then
  while IFS='=' read -r key value; do
    [ -z "$key" ] && continue
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ "$key" =~ ^\[ ]] && continue
    if [[ "$key" =~ ^export[[:space:]]+(SUPABASE|TELEGRAM|GOOGLE|VERTEX|OPENAI|SUREN|TEST|JWT|GCP|ALLOWED|ORG) ]]; then
      clean_key="${key#export }"
      clean_value="${value%\"}"; clean_value="${clean_value#\"}"
      export "$clean_key=$clean_value"
    fi
  done < <(grep '^export ' ~/.bashrc)
fi

# ── 2. Fallbacks pour les vars critiques ──────────────────────────────────────
export ENVIRONMENT=test
export SUPABASE_URL="${SUPABASE_URL:-https://REDACTED.supabase.co}"
export SUPABASE_SERVICE_KEY="${TEST_SUPABASE_SERVICE_KEY:-${SUPABASE_SERVICE_KEY:-}}"
export JWT_SECRET="${TEST_JWT_SECRET:-${JWT_SECRET:-}}"
export GEMINI_API_KEY="${SUREN_GEMINI_API_KEY:-${GEMINI_API_KEY:-}}"
# Forcer le port du backend (conftest.py lit BACKEND_BASE_URL)
export BACKEND_BASE_URL="http://localhost:8080"

# ── 3. Verify required env vars ──────────────────────────────────────────
: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_SERVICE_KEY:?SUPABASE_SERVICE_KEY is required}"
: "${GEMINI_API_KEY:?GEMINI_API_KEY is required for the LLM judge}"
: "${TELEGRAM_API_ID:?TELEGRAM_API_ID is required for tg-mock Docker — ajoute-le dans ~/.bashrc}"
: "${TELEGRAM_API_HASH:?TELEGRAM_API_HASH is required for tg-mock Docker — ajoute-le dans ~/.bashrc}"

# ── 4. Démarrer tg-mock (Docker) ─────────────────────────────────────────
echo "🐳 Starting tg-mock (Docker aiogram/telegram-bot-api)..."
BOT_TOKEN="${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN:-}"
export TELEGRAM_TOKEN="$BOT_TOKEN"
docker compose -f "$E2E_DIR/docker-compose.e2e.yml" up -d 2>&1

echo "⏳ Waiting for tg-mock to respond on port 8081..."
TG_MOCK_READY=false
for i in $(seq 1 15); do
    if curl -sf "http://localhost:8081/bot${BOT_TOKEN}/getMe" > /dev/null 2>&1; then
        echo "   ✅ tg-mock ready (attempt $i)"
        TG_MOCK_READY=true
        break
    fi
    sleep 2
done
if [ "$TG_MOCK_READY" = false ]; then
    echo "❌ tg-mock Docker did not start within 30s"
    docker compose -f "$E2E_DIR/docker-compose.e2e.yml" logs --tail=20
    exit 1
fi

# Pointer le backend vers le tg-mock local
export TELEGRAM_API_URL="http://localhost:8081"
echo "   TELEGRAM_API_URL=$TELEGRAM_API_URL"
echo ""

# ── 5. Démarrer le backend ─────────────────────────────────────────────
echo "🚀 Starting backend (run-local-back_test.sh --tg-mock)..."
echo ""

# run-local-back_test.sh gère le kill du vieux uvicorn, source .env.test, etc.
# On le lance en background pour pouvoir monitorer /health
"$SCRIPT_DIR/run-local-back_test.sh" --tg-mock &
BACKEND_PID=$!

# Attendre que le backend réponde sur /health
echo "⏳ Waiting for backend /health..."
BACKEND_HEALTHY=false
for i in $(seq 1 30); do
    if curl -sf "http://localhost:8080/health" > /dev/null 2>&1; then
        echo "   ✅ Backend healthy (attempt $i)"
        BACKEND_HEALTHY=true
        break
    fi
    sleep 2
done
if [ "$BACKEND_HEALTHY" = false ]; then
    echo "❌ Backend did not start within 60s"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo ""

# ── 6. Bot seed handled by test fixture ───────────────────────────────────
echo "🌱 Bot seed: handled by the test fixture (bot_seed)"

# ── 7. Activate venv-e2e ─────────────────────────────────────────────────
echo ""
echo "📦 Activating venv-e2e..."
if [ ! -d "$PROJECT_DIR/venv-e2e" ]; then
    echo "❌ venv-e2e not found at $PROJECT_DIR/venv-e2e"
    echo "   Run: python3 -m venv $PROJECT_DIR/venv-e2e"
    echo "   Then: pip install -r $E2E_DIR/requirements-e2e.txt"
    exit 1
fi
source "$PROJECT_DIR/venv-e2e/bin/activate"
pip install -q -r "$E2E_DIR/requirements-e2e.txt" 2>/dev/null || true

# ── 8. Run tests ────────────────────────────────────────────────────────
echo ""
echo "🧪 Running E2E tests..."
echo "============================================"
set +e
cd "$PROJECT_DIR"
python -m pytest "$E2E_DIR/tests" -v --tb=short "$@"
EXIT_CODE=$?
set -e
echo "============================================"

# ── 9. Cleanup ───────────────────────────────────────────────────────────
echo ""
echo "🧹 Cleanup..."
echo "   Stopping backend..."
kill $BACKEND_PID 2>/dev/null || true
echo "   Stopping tg-mock..."
docker compose -f "$E2E_DIR/docker-compose.e2e.yml" down -v 2>/dev/null || true

# ── 10. Report ──────────────────────────────────────────────────────────
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All E2E tests passed!"
else
    echo "❌ Some E2E tests failed (exit code: $EXIT_CODE)"
fi
exit $EXIT_CODE
