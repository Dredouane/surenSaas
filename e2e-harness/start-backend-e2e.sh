#!/usr/bin/env bash
# Minimal backend launcher for E2E tests — inline env vars only.
set -euo pipefail

cd /opt/projects/suren/saas/surenSaas/surenSaasBack
source venv/bin/activate

ENVIRONMENT=test \
SUPABASE_URL="https://REDACTED.supabase.co" \
SUPABASE_SERVICE_KEY="REDACTED_JWT" \
JWT_SECRET="938ed98cdea8b20b6f093d6f03aa2696c0532a6ab1b5b291e5e7084e326d26b9" \
ALLOWED_ORIGINS="http://localhost:3000" \
ORG_ID=REDACTEDORG \
ORG_SLUG=REDACTED_ORG_SLUG \
TELEGRAM_CONSTRUCTION_BOT_TOKEN="REDACTED_BOT_TOKEN" \
TELEGRAM_CONSTRUCTION_BOT_USERNAME="suren_construction_test_bot" \
TELEGRAM_API_URL="http://localhost:8081" \
GOOGLE_API_KEY="REDACTED_GEMINI_KEY" \
GEMINI_API_KEY="REDACTED_GEMINI_KEY" \
GCP_PROJECT_ID="suren-saas" \
VERTEX_AI_PROJECT_ID="suren-saas" \
VERTEX_AI_LOCATION="europe-west1" \
SUREN_GEMINI_API_KEY="REDACTED_GEMINI_KEY" \
SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN="REDACTED_BOT_TOKEN" \
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1 --log-level info
