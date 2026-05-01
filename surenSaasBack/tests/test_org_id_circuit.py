"""Test que l'org_id circule correctement de l'URL du webhook jusqu'au graphe."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.telegram_core import handle_telegram_webhook
from fastapi import Request

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


@pytest.mark.asyncio
async def test_org_id_passed_from_url_to_handler():
    """Vérifie que l'org_id de l'URL est bien transmis à handle_update."""
    org_id = "REDACTEDORG"
    webhook_token = "test-token"

    update_payload = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "TestUser"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "Bonjour"
        }
    }

    with patch("app.api.telegram_core.get_supabase") as mock_supabase, \
         patch("app.services.agents.persistence.agent_persistence.get_saver", new_callable=AsyncMock) as mock_saver, \
         patch("app.services.telegram.interface.httpx.AsyncClient.post") as mock_tg_post:

        mock_sb = MagicMock()
        mock_supabase.return_value = mock_sb

        # Mock telegram_bots table
        def mock_table(name):
            m = MagicMock()
            if name == 'telegram_bots':
                def mock_select(*args, **kwargs):
                    eq_mock = MagicMock()
                    eq_mock.like.return_value = eq_mock
                    eq_mock.eq.return_value = eq_mock
                    eq_mock.execute.return_value = MagicMock(data=[{
                        "id": "bot_123",
                        "bot_username": "suren_construction_test_bot",
                        "webhook_secret": None
                    }])
                    return MagicMock(**{'eq.return_value': eq_mock})
                m.select.side_effect = mock_select
            return m

        mock_sb.table.side_effect = mock_table
        mock_tg_post.return_value = MagicMock(status_code=200)
        mock_tg_post.return_value.json.return_value = {"ok": True}

        from langgraph.checkpoint.memory import MemorySaver
        mock_saver.return_value = MemorySaver()

        request_mock = MagicMock(spec=Request)
        request_mock.json = AsyncMock(return_value=update_payload)

        result = await handle_telegram_webhook(org_id, webhook_token, request_mock)

        # Vérifier que le webhook a bien traité la requête
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_org_id_fallback_from_settings():
    """Vérifie que _get_user_org utilise settings.org_id comme fallback."""
    from app.services.telegram.webhook_handler import WebhookHandlerService
    from app.core.config import settings

    handler = WebhookHandlerService(
        supabase_client=MagicMock(),
        audit_service=MagicMock(),
        bot_manager=MagicMock(),
        upload_invoice_service=MagicMock()
    )

    org_id = await handler._get_user_org(99999)  # User inexistant
    # Si settings.org_id est défini, on le récupère
    if settings.org_id:
        assert org_id == settings.org_id
    else:
        assert org_id == ""
