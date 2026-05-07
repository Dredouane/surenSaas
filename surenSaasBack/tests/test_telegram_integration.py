
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["OPEN_ROUTER_API_KEY"] = "fake-openrouter-key"

@pytest.mark.asyncio
async def test_telegram_webhook_integration_agentic():
    """Test direct de handle_telegram_webhook avec mocks."""
    
    org_id = "REDACTEDORG"
    webhook_token = "test-token"
    
    update_payload = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "TestUser", "username": "testuser"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "Bonjour, quel est le budget du chantier CRF ?"
        }
    }
    
    with patch("app.api.telegram_core.get_supabase") as mock_supabase:
        mock_sb = MagicMock()
        mock_supabase.return_value = mock_sb
        
        def mock_table(name):
            m = MagicMock()
            if name == 'telegram_bots':
                def mock_select(*args, **kwargs):
                    sel = args[0] if args else '*'
                    if sel == 'org_id':
                        return MagicMock(**{'eq.return_value': MagicMock(
                            **{'single.return_value': MagicMock(
                                **{'execute.return_value': MagicMock(data={'org_id': org_id})}
                            )}
                        )})
                    eq_mock = MagicMock()
                    like_mock = MagicMock()
                    single_mock = MagicMock()
                    eq_mock.like.return_value = like_mock
                    eq_mock.single.return_value = single_mock
                    eq_mock.like.return_value.eq.return_value = MagicMock(
                        **{'execute.return_value': MagicMock(
                            data=[{"id": "bot_123", "bot_username": "suren_construction_test_bot", "webhook_secret": None}]
                        )}
                    )
                    single_mock.execute.return_value = MagicMock(data={"token": "fake:token"})
                    return MagicMock(**{'eq.return_value': eq_mock})
                m.select.side_effect = mock_select
            elif name == 'telegram_users':
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"org_id": org_id}
            elif name == 'logs_agents':
                m.insert.return_value.execute.return_value.data = [{"id": "log_123"}]
            elif name == 'telegram_audit':
                m.insert.return_value.execute.return_value.data = [{"id": "audit_123"}]
            return m
        
        mock_sb.table.side_effect = mock_table
        
        with patch("app.services.telegram.factory.get_supabase") as mock_factory_sb:
            mock_factory_sb.return_value = mock_sb
            
            with patch("app.core.vertex.get_chat_model") as MockLLM:
                from langchain_core.messages import AIMessage
                mock_llm_instance = MockLLM.return_value
                mock_llm_instance.invoke.return_value = AIMessage(content="Le budget du chantier CRF est de 1,018,112€ HT.")
                mock_llm_instance.bind_tools.return_value.invoke.return_value = mock_llm_instance.invoke.return_value
                
                from langgraph.checkpoint.memory import MemorySaver
                with patch("app.services.agents.persistence.agent_persistence.get_saver", new_callable=AsyncMock) as mock_saver:
                    mock_saver.return_value = MemorySaver()
                    
                    with patch("app.services.telegram.interface.httpx.AsyncClient.post") as mock_tg_post:
                        mock_tg_post.return_value = MagicMock(status_code=200)
                        mock_tg_post.return_value.json.return_value = {"ok": True}
                        
                        from app.api.telegram_core import handle_telegram_webhook
                        request_mock = MagicMock(spec=Request)
                        request_mock.json = AsyncMock(return_value=update_payload)
                        
                        result = await handle_telegram_webhook(org_id, webhook_token, request_mock)
                        
                        # Peut être dict ou JSONResponse (FastAPI)
                        if hasattr(result, 'body'):
                            import json as _json
                            result = _json.loads(result.body)
                        
                        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
                        assert result.get("status") == "agentic_success", f"Webhook failed. Result: {result}"
                        
                        calls = [call for call in mock_tg_post.call_args_list if "sendMessage" in str(call)]
                        assert len(calls) > 0, "No sendMessage calls found"
                        
                        sent_payload = calls[0].kwargs["json"]
                        assert "1,018,112" in sent_payload["text"]
                        
                        print("\n✅ Test intégration Webhook -> Agentic Flow validé.")
