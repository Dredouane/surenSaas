#!/usr/bin/env bash
# ============================================================
# E2E Test Runner — Orchestre backend + tg-mock + tests
# ============================================================
# Usage:
#   ./scripts/run-e2e.sh                         # Mode réel API Telegram
#   ./scripts/run-e2e.sh --tg-mock                # Mode local tg-mock Docker
#   ./scripts/run-e2e.sh --tg-mock --verbose      # Logs détaillés
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
E2E_DIR="$PROJECT_DIR/e2e-harness"
BACKEND_DIR="$PROJECT_DIR/surenSaasBack"

USE_TG_MOCK=false
VERBOSE=false
for arg in "$@"; do
    case "$arg" in
        --tg-mock|--use-tg-mock) USE_TG_MOCK=true ;;
        --verbose|-v) VERBOSE=true ;;
    esac
done

echo "============================================"
echo "  E2E Test Runner"
echo "============================================"
echo "  Mode tg-mock: $USE_TG_MOCK"
echo ""

# ── 1. Extraire les variables du .bashrc sans le sourcer (contourne PS1 guard) ──
if [ -f ~/.bashrc ]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# || "$key" =~ ^\[ ]] && continue
    if [[ "$key" =~ ^export[[:space:]]+(SUPABASE|TELEGRAM|GOOGLE|VERTEX|OPENAI|SUREN|TEST|JWT|GCP|ALLOWED|ORG) ]]; then
      local k="${key#export }"
      local v="${value%\"}"; v="${v#\"}"
      export "$k=$v"
    fi
  done < <(grep '^export ' ~/.bashrc)
fi

# ── 2. Fallbacks pour les vars critiques ──────────────────────────────────────
export ENVIRONMENT=test
export SUPABASE_URL="${SUPABASE_URL:-https://REDACTED.supabase.co}"
export SUPABASE_SERVICE_KEY="${TEST_SUPABASE_SERVICE_KEY:-${SUPABASE_SERVICE_KEY:-}}"
export JWT_SECRET="${TEST_JWT_SECRET:-${JWT_SECRET:-}}"
export GEMINI_API_KEY="${SUREN_GEMINI_API_KEY:-${GEMINI_API_KEY:-}}"

# ── 3. Verify required env vars ──────────────────────────────────────────
: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_SERVICE_KEY:?SUPABASE_SERVICE_KEY is required}"
: "${GEMINI_API_KEY:?GEMINI_API_KEY is required for the LLM judge}"

# ── 4. Start tg-mock (Docker) ───────────────────────────────────────────
if [ "$USE_TG_MOCK" = true ]; then
    echo "🐳 Starting tg-mock (Docker aiogram/telegram-bot-api)..."
    if [ -z "${TELEGRAM_API_ID:-}" ] || [ -z "${TELEGRAM_API_HASH:-}" ]; then
        echo "❌ TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in ~/.bashrc"
        echo "   Get them from https://my.telegram.org/apps"
        exit 1
    fi
    export TELEGRAM_TOKEN="${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN:-}"
    docker compose -f "$E2E_DIR/docker-compose.e2e.yml" up -d 2>&1

    echo "⏳ Waiting for tg-mock..."
    for i in $(seq 1 15); do
        if curl -sf "http://localhost:8081/" > /dev/null 2>&1; then
            echo "   ✅ tg-mock ready (attempt $i)"
            break
        fi
        sleep 2
    done

    export TELEGRAM_API_URL="http://localhost:8081"
else
    echo "📡 Using real Telegram API"
fi

# ── 5. Ensure backend is started ─────────────────────────────────────────
echo ""
echo "🚀 Starting backend..."
BACKEND_LOG="/tmp/backend_e2e_error.log"
> "$BACKEND_LOG"

# Lancer le script de démarrage backend en arrière-plan
"$E2E_DIR/start-backend-e2e.sh" &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

echo "⏳ Waiting for backend /health..."
BACKEND_READY=false
for i in $(seq 1 30); do
    if curl -sf "http://localhost:8080/health" > /dev/null 2>&1; then
        echo "   ✅ Backend healthy (attempt $i)"

        # Vérifier que le process est toujours vivant 3s après
        sleep 3
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            echo "   ✅ Backend process still alive after 3s"
            BACKEND_READY=true
            break
        else
            echo "   ❌ Backend process died within 3s of health check!"
            echo "   === Last 20 lines of $BACKEND_LOG ==="
            tail -20 "$BACKEND_LOG" 2>/dev/null || echo "   (no log file)"
            exit 1
        fi
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend did not start within 60s"
        echo "   === Last 30 lines of $BACKEND_LOG ==="
        tail -30 "$BACKEND_LOG" 2>/dev/null || echo "   (no log file)"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 2
done

if [ "$BACKEND_READY" != true ]; then
    echo "❌ Backend did not become ready"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# ── 6. Bot seed handled by test fixture ───────────────────────────────────
echo ""
echo "🌱 Bot seed will be handled by the test fixture"

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
if [ "$USE_TG_MOCK" = true ]; then
    echo "   Stopping tg-mock..."
    docker compose -f "$E2E_DIR/docker-compose.e2e.yml" down -v 2>/dev/null || true
fi
echo "   Stopping backend..."
kill $BACKEND_PID 2>/dev/null || true

# ── 10. Report ──────────────────────────────────────────────────────────
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All E2E tests passed!"
else
    echo "❌ Some E2E tests failed (exit code: $EXIT_CODE)"
fi
exit $EXIT_CODE
