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
# Forcer le port du backend pour les tests (conftest.py lit BACKEND_BASE_URL)
export BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://localhost:8080}"

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

# Lancer le script de démarrage backend (il attend lui-même le health)
"$E2E_DIR/start-backend-e2e.sh"
echo "   ✅ start-backend-e2e.sh completed successfully"

# Lire le PID du fichier créé par start-backend-e2e.sh
BACKEND_PID=$(cat /tmp/backend_uvicorn_pid.txt 2>/dev/null || echo "")
if [ -z "$BACKEND_PID" ]; then
    echo "❌ Could not read backend PID"
    exit 1
fi
echo "   Backend PID: $BACKEND_PID"

# Vérifier que le process est toujours vivant
sleep 2
if kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "   ✅ Backend process still alive"
else
    echo "   ❌ Backend process died during startup!"
    echo "   === Last 20 lines of $BACKEND_LOG ==="
    tail -20 "$BACKEND_LOG" 2>/dev/null || echo "   (no log file)"
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
