#!/usr/bin/env bash
# ============================================================
# E2E Test Runner — Orchestre backend + mock Telegram + tests
# ============================================================
# Usage:
#   ./scripts/run-e2e.sh
#   ./scripts/run-e2e.sh --verbose          # Logs détaillés
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
E2E_DIR="$PROJECT_DIR/e2e-harness"

VENV_E2E="${VENV_E2E:-/home/redouane/dev/AI-ERA/venv-e2e}"

VERBOSE=false
for arg in "$@"; do
    case "$arg" in
        --verbose|-v) VERBOSE=true ;;
    esac
done

echo "============================================"
echo "  E2E Test Runner"
echo "  Mock Telegram Python (port 8081)"
echo "============================================"
echo ""

# ── 1. Extraire les variables du .bashrc ─────────────────────────────────
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

# ── 2. Fallbacks ─────────────────────────────────────────────────────────
export ENVIRONMENT=test
export SUPABASE_URL="${SUPABASE_URL:-https://REDACTED.supabase.co}"
export SUPABASE_SERVICE_KEY="${TEST_SUPABASE_SERVICE_KEY:-${SUPABASE_SERVICE_KEY:-}}"
export JWT_SECRET="${TEST_JWT_SECRET:-${JWT_SECRET:-}}"
export GEMINI_API_KEY="${SUREN_GEMINI_API_KEY:-${GEMINI_API_KEY:-}}"
export BACKEND_BASE_URL="http://localhost:8080"

# ── 3. Vérifier les vars critiques ──────────────────────────────────────
: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_SERVICE_KEY:?SUPABASE_SERVICE_KEY is required}"
: "${GEMINI_API_KEY:?GEMINI_API_KEY is required for the LLM judge}"

# ── 4. Tue tout ce qui traîne sur 8081 ──────────────────────────────────
fuser -k 8081/tcp 2>/dev/null || true
sleep 1

# ── 5. Lancer le mock Telegram Python ────────────────────────────────────
echo "🚀 Starting mock Telegram (Python)..."
source "$VENV_E2E/bin/activate"
python "$E2E_DIR/mock_telegram.py" &
MOCK_PID=$!

# Nettoyage à la sortie
cleanup() {
    echo ""
    echo "🧹 Cleanup..."
    echo "   Stopping mock Telegram (PID $MOCK_PID)..."
    kill $MOCK_PID 2>/dev/null || true
    echo "   Stopping backend..."
    kill $BACKEND_PID 2>/dev/null || true
}
trap cleanup EXIT

echo "⏳ Waiting for mock Telegram on port 8081..."
for i in $(seq 1 10); do
    if curl -sf "http://localhost:8081/health" > /dev/null 2>&1; then
        echo "   ✅ Mock Telegram ready (attempt $i)"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Mock Telegram failed to start"
        exit 1
    fi
    sleep 0.5
done

# Pointer le backend vers le mock local
export TELEGRAM_API_URL="http://localhost:8081"
echo "   TELEGRAM_API_URL=$TELEGRAM_API_URL"
echo ""

# ── 6. Démarrer le backend ─────────────────────────────────────────────
echo "🚀 Starting backend (run-local-back_test.sh --tg-mock)..."
"$SCRIPT_DIR/run-local-back_test.sh" --tg-mock &
BACKEND_PID=$!

echo "⏳ Waiting for backend /health..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:8080/health" > /dev/null 2>&1; then
        echo "   ✅ Backend healthy (attempt $i)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend did not start within 60s"
        exit 1
    fi
    sleep 2
done
echo ""

# ── 7. Vérifier que les dépendances sont installées ──────────────────────
echo "📦 Dependencies check..."
pip install -q -r "$E2E_DIR/requirements-e2e.txt" 2>/dev/null || true
echo ""

# ── 8. Lancer les tests ────────────────────────────────────────────────
echo "🧪 Running E2E tests..."
echo "============================================"
set +e
cd "$PROJECT_DIR"
python -m pytest "$E2E_DIR/tests" -v --tb=short "$@"
EXIT_CODE=$?
set -e
echo "============================================"

# ── 9. Report ────────────────────────────────────────────────────────────
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All E2E tests passed!"
else
    echo "❌ Some E2E tests failed (exit code: $EXIT_CODE)"
fi
exit $EXIT_CODE
