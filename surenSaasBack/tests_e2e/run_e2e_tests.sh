#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$BACKEND_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.e2e.yml"

BACKEND_HOST=${BACKEND_HOST:-"http://localhost:8000"}
USE_LOCAL_TELEGRAM=${USE_LOCAL_TELEGRAM:-false}

echo "============================================"
echo "  E2E Telegram ↔ Backend Test Runner"
echo "============================================"
echo ""
echo "🔗 Backend cible : $BACKEND_HOST"
echo "📡 API Telegram   : $([ "$USE_LOCAL_TELEGRAM" = "true" ] && echo "LOCAL (Docker)" || echo "OFFICIELLE (api.telegram.org)")"
echo ""

# 1. Load environment
if [ -f "$PROJECT_DIR/.env.test" ]; then
    set -a; source "$PROJECT_DIR/.env.test"; set +a
fi

if [ -f "$PROJECT_DIR/.env.test.local" ]; then
    set -a; source "$PROJECT_DIR/.env.test.local"; set +a
fi

export ENVIRONMENT=test

: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_SERVICE_KEY:?SUPABASE_SERVICE_KEY is required}"
: "${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN:?SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN is required}"

echo "✅ Configuration loaded"
echo ""

# 2. Verify backend is reachable
echo "🔍 Checking backend at $BACKEND_HOST..."
if ! curl -sf "$BACKEND_HOST/health" > /dev/null 2>&1; then
    echo "   ❌ Backend not reachable"
    echo "   💡 Lance d'abord : cd $PROJECT_DIR && docker compose up -d backend"
    exit 1
fi
echo "   ✅ Backend is healthy"
echo ""

# 3. Optionally start local telegram-bot-api
if [ "$USE_LOCAL_TELEGRAM" = "true" ]; then
    echo "🐳 Starting telegram-bot-api..."
    docker compose -f "$COMPOSE_FILE" up -d

    echo "⏳ Waiting for telegram-bot-api..."
    for i in $(seq 1 20); do
        if curl -sf "http://localhost:8081/" > /dev/null 2>&1; then
            echo "   ✅ telegram-bot-api ready (attempt $i)"
            break
        fi
        echo "   ⏳ waiting... ($i/20)"
        sleep 2
    done

    export SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_URL="http://localhost:8081"
fi
echo ""

# 4. Verify bot token works
echo "🔍 Checking bot token..."
BOT_INFO=$(curl -sf "https://api.telegram.org/bot${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN}/getMe" 2>/dev/null)
if [ -z "$BOT_INFO" ]; then
    echo "   ❌ Bot token invalide ou API Telegram inaccessible"
    exit 1
fi
echo "   ✅ Bot OK: $(echo "$BOT_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])" 2>/dev/null || echo 'unknown')"
echo ""

# 5. Set webhook
echo "🔗 Setting webhook..."
WEBHOOK_URL="${BACKEND_HOST}/api/v1/webhook/construction"
curl -sf "https://api.telegram.org/bot${SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}" > /dev/null
echo "   ✅ Webhook set to $WEBHOOK_URL"
echo ""

# 6. Activate venv
if [ -d "$BACKEND_DIR/venv" ]; then
    source "$BACKEND_DIR/venv/bin/activate"
fi

echo "📦 Installing test dependencies..."
pip install -q httpx pytest-asyncio 2>/dev/null || true
echo ""

# 7. Run tests
echo "🧪 Running E2E tests..."
set +e
cd "$BACKEND_DIR"
python -m pytest "$SCRIPT_DIR" -v "$@"
EXIT_CODE=$?
set -e
echo ""

# 8. Cleanup
if [ "$USE_LOCAL_TELEGRAM" = "true" ]; then
    echo "🧹 Cleaning up Docker..."
    docker compose -f "$COMPOSE_FILE" down -v
fi
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All E2E tests passed!"
else
    echo "❌ Some E2E tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
