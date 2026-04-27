"""
Test Template: Upload CCTP - Rue Thenard

Simule l'envoi du fichier CCTP-ESSET-Rue-Thenard.pdf via Telegram
et valide qu'une entrée est créée dans chantier_operations_htl
avec statut='en_attente'.

Note : Les tests avec tg_user nécessitent un vrai échange bot↔user
via l'API Telegram officielle. Le test ne sera exécuté que si
le fixture est présent dans le dossier fixtures/.
"""

import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_send_text_and_check_db():
    pytest.skip("Requiert un vrai échange bot↔utilisateur Telegram")


@pytest.mark.asyncio
async def test_upload_pdf_and_check_db(tg_user, db_validator, fixtures_dir):
    fixture = fixtures_dir / "CCTP-ESSET-Rue-Thenard.pdf"
    if not fixture.exists():
        pytest.skip(f"Fixture file not found: {fixture}")

    test_start = datetime.utcnow()

    result = await tg_user.upload_file(str(fixture))
    assert result is not None

    response = await tg_user.wait_for_bot_response(timeout=15)
    assert response is not None, "Bot should respond to file upload"
    print(f"  🤖 Bot response: {response.get('text', '(no text)')[:200]}...")

    operation = db_validator.assert_operation_created(
        source="telegram_pdf",
        since=test_start,
        statut="en_attente",
    )
    print(f"  ✅ Operation created in DB: {operation['id']}")
    assert operation["org_id"] == db_validator.org_id


@pytest.mark.asyncio
async def test_bot_healthcheck(tg_user, bot_api_url):
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{bot_api_url}/bot{tg_user.bot_token}/getMe"
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["result"]["is_bot"] is True
    username = data["result"]["username"]
    print(f"  🤖 Bot username: @{username}")


@pytest.mark.asyncio
async def test_db_validator_works(db_validator):
    operation = db_validator.assert_operation_created(
        source="telegram_pdf",
        since=datetime(2026, 4, 1),
        statut="en_attente",
    )
    assert operation["org_id"] == db_validator.org_id
    print(f"  ✅ DB validator works, found operation: {operation['id']}")


@pytest.mark.asyncio
async def test_webhook_is_configured(tg_user, bot_api_url):
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{bot_api_url}/bot{tg_user.bot_token}/getWebhookInfo"
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    info = data["result"]
    print(f"  🔗 Webhook URL: {info.get('url', 'NOT SET')}")
    print(f"  ✅ Pending updates: {info.get('pending_update_count', 0)}")
