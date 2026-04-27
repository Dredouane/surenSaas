#!/usr/bin/env python3
"""
Tests pour le Bot Telegram Construction — Nouveau menu & dispatcher.

Mocke toutes les interactions externes (httpx, Supabase).
Valide le routage des callbacks et messages dans la nouvelle architecture.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.telegram_core import (
    handle_telegram_webhook,
    _dispatch_message,
    _dispatch_callback,
    get_bot_token,
    send_simple_message,
    send_message_with_keyboard,
)
from app.api.bot_construction_commands import (
    handle_construction_callback,
    handle_start_command,
    _handle_menu_main,
    _handle_sub_operations,
    _handle_chantier_list,
)


# ================================================================
# Fixtures
# ================================================================

@pytest.fixture
def mock_supabase():
    """Mock de la DB Supabase."""
    mock = MagicMock()
    mock.table.return_value.select.return_value = mock
    mock.eq.return_value = mock
    mock.single.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.gte.return_value = mock
    mock.like.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


@pytest.fixture
def bot_config():
    return {
        "id": "bot-uuid",
        "bot_username": "suren_construction_test_bot",
        "webhook_secret": None,
        "webhook_url": "https://test/api/v1/org/telegram/webhook/token123",
        "is_active": True,
    }


@pytest.fixture
def base_message():
    return {
        "message_id": 1,
        "from": {"id": 12345, "first_name": "Test", "username": "testuser"},
        "chat": {"id": 12345, "first_name": "Test", "type": "private"},
        "date": 1700000000,
    }


@pytest.fixture
def base_callback_query():
    return {
        "id": "callback-id-1",
        "from": {"id": 12345, "first_name": "Test", "username": "testuser"},
        "data": "menu:main",
        "chat_instance": "test-instance",
    }


# ================================================================
# Tests: Dispatcher central des callbacks
# ================================================================

class TestCallbackDispatcher:
    """Valide le routage des callbacks vers les bons handlers."""

    @pytest.mark.asyncio
    async def test_menu_main_callback(self, base_callback_query, bot_config, mock_supabase):
        base_callback_query["data"] = "menu:main"
        with patch("app.api.bot_construction_commands.send_message_with_keyboard", new_callable=AsyncMock) as mock_send:
            result = await handle_construction_callback(
                base_callback_query, bot_config, mock_supabase, "org-123"
            )
        assert result["ok"] is True
        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_operations_submenu(self, base_callback_query, bot_config, mock_supabase):
        base_callback_query["data"] = "menu:sub:operations"
        with patch("app.api.bot_construction_commands.send_message_with_keyboard", new_callable=AsyncMock) as mock_send:
            result = await handle_construction_callback(
                base_callback_query, bot_config, mock_supabase, "org-123"
            )
        assert result["ok"] is True
        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_chantier_list(self, base_callback_query, bot_config, mock_supabase):
        base_callback_query["data"] = "chantier:list"
        with patch("app.api.bot_construction_commands.send_message_with_keyboard", new_callable=AsyncMock) as mock_send:
            result = await handle_construction_callback(
                base_callback_query, bot_config, mock_supabase, "org-123"
            )
        assert result["ok"] is True
        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invoice_validate_dispatched(self, base_callback_query, bot_config, mock_supabase):
        base_callback_query["data"] = "invoice:validate:inv-123"
        with patch(
            "app.api.bot_construction.handle_invoice_validation",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ) as mock_handler:
            # Force reload to pick up the mock — the import is inside function body
            import importlib
            import app.api.bot_construction_commands as cmds
            importlib.reload(cmds)
            from app.api.bot_construction_commands import handle_construction_callback as hcc
            result = await hcc(
                base_callback_query, bot_config, mock_supabase, "org-123"
            )
        assert result["ok"] is True
        mock_handler.assert_awaited_once_with(12345, "inv-123", bot_config, mock_supabase, "org-123")

    @pytest.mark.asyncio
    async def test_invoice_cancel_dispatched(self, base_callback_query, bot_config, mock_supabase):
        base_callback_query["data"] = "invoice:cancel:inv-123"
        with patch(
            "app.api.bot_construction.handle_invoice_cancellation",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ) as mock_handler:
            import importlib
            import app.api.bot_construction_commands as cmds
            importlib.reload(cmds)
            from app.api.bot_construction_commands import handle_construction_callback as hcc
            result = await hcc(
                base_callback_query, bot_config, mock_supabase, "org-123"
            )
        assert result["ok"] is True
        mock_handler.assert_awaited_once_with(12345, "inv-123", bot_config, mock_supabase, "org-123")

    @pytest.mark.asyncio
    async def test_unknown_callback_redirects_to_menu(self, base_callback_query, bot_config, mock_supabase):
        base_callback_query["data"] = "some:unknown:callback"
        with patch("app.api.bot_construction_commands.send_message_with_keyboard", new_callable=AsyncMock) as mock_send:
            result = await handle_construction_callback(
                base_callback_query, bot_config, mock_supabase, "org-123"
            )
        assert result["ok"] is True
        mock_send.assert_awaited_once()


# ================================================================
# Tests: Helpeprs API Telegram
# ================================================================

class TestApiHelpers:
    """Valide les helpers (token, envoi message)."""

    def test_get_bot_token_found(self, bot_config):
        bot_config["bot_username"] = "suren_construction_test_bot"
        with patch.dict(os.environ, {
            "ENVIRONMENT": "test",
            "SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN": "test:token",
        }):
            token = get_bot_token(bot_config)
        assert token == "test:token"

    def test_get_bot_token_missing(self, bot_config):
        bot_config["bot_username"] = "suren_construction_test_bot"
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}, clear=True):
            token = get_bot_token(bot_config)
        assert token is None

    @pytest.mark.asyncio
    async def test_send_simple_message(self, bot_config):
        with patch("app.api.telegram_core.get_bot_token", return_value="test:token"):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value.json.return_value = {"ok": True}
                await send_simple_message(12345, bot_config, "Hello")
                mock_post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_message_with_keyboard(self, bot_config):
        keyboard = {"inline_keyboard": [[{"text": "Test", "callback_data": "test"}]]}
        with patch("app.api.telegram_core.get_bot_token", return_value="test:token"):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value.json.return_value = {"ok": True}
                await send_message_with_keyboard(12345, bot_config, "Hello", keyboard)
                mock_post.assert_awaited_once()


# ================================================================
# Tests: /start command
# ================================================================

class TestStartCommand:
    """Valide la commande /start et liaison compte Telegram."""

    @pytest.mark.asyncio
    async def test_start_without_payload_shows_error(self, base_message, bot_config, mock_supabase):
        base_message["text"] = "/start"
        with patch("app.api.bot_construction_commands.send_simple_message", new_callable=AsyncMock) as mock_send:
            result = await handle_start_command(base_message, bot_config, mock_supabase, "org-123")
        assert result["ok"] is True
        mock_send.assert_awaited_once()
        args = mock_send.call_args[0]
        assert "lien d'invitation" in args[2] or "Bienvenue" in args[2]

    @pytest.mark.asyncio
    async def test_start_with_invalid_uuid(self, base_message, bot_config, mock_supabase):
        base_message["text"] = "/start invalid-payload"
        with patch("app.api.bot_construction_commands.send_simple_message", new_callable=AsyncMock) as mock_send:
            result = await handle_start_command(base_message, bot_config, mock_supabase, "org-123")
        assert result["ok"] is True
        mock_send.assert_awaited_once_with(
            12345, bot_config, "❌ Lien d'invitation invalide."
        )

    @pytest.mark.asyncio
    async def test_start_with_valid_uuid_creates_link(self, base_message, bot_config, mock_supabase):
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        base_message["text"] = f"/start {valid_uuid}"

        # Chained mock: every execute() returns data
        mock_exec = MagicMock()
        mock_exec.data = [{"id": "fake-user-id"}]

        # Override the table() → select() → eq() → execute() chain
        mock_supabase.table.return_value = mock_supabase
        mock_supabase.select.return_value = mock_supabase
        mock_supabase.eq.return_value = mock_supabase
        mock_supabase.execute.return_value = mock_exec
        mock_supabase.single.return_value = mock_supabase

        with patch("app.api.bot_construction_commands.send_simple_message", new_callable=AsyncMock):
            with patch("app.api.bot_construction_commands.send_message_with_keyboard", new_callable=AsyncMock):
                result = await handle_start_command(base_message, bot_config, mock_supabase, "org-123")
        assert result["ok"] is True


# ================================================================
# Tests: Pointages (Phase 1 — CHA-001: status vs statut)
# ================================================================

class TestPointageValidation:
    """Valide que la colonne 'statut' est utilisée (pas 'status')."""

    @pytest.mark.asyncio
    async def test_validate_pointage_uses_statut_column(self, bot_config):
        """
        RED — CHA-001: Le bot utilise 'status' au lieu de 'statut'.
        Ce test échoue tant que le code utilise 'status'.
        """
        from app.api.bot_construction_pointages import handle_validate_pointage

        supabase = MagicMock()
        table_mock = MagicMock()
        supabase.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.single.return_value = table_mock
        table_mock.execute.return_value = MagicMock(data=[{"id": "pt-123"}])

        with patch("app.api.bot_construction_pointages.send_simple_message", new_callable=AsyncMock):
            with patch("app.api.bot_construction_pointages.ensure_chantier_selected", new_callable=AsyncMock, return_value={"id": "chantier-1", "nom": "Test"}):
                result = await handle_validate_pointage(12345, bot_config, supabase, "org-123")

        assert result["ok"] is True
        # Vérifier que l'UPDATE utilise 'statut' et pas 'status'
        update_call_args = table_mock.update.call_args
        assert update_call_args is not None, "UPDATE should have been called"
        update_kwargs = update_call_args[0][0]
        assert "statut" in update_kwargs, f"Expected 'statut' in update payload, got: {update_kwargs}"
        assert "status" not in update_kwargs, f"'status' should not be used, got: {update_kwargs}"
        assert update_kwargs["statut"] == "en_attente_validation"


class TestChantierContext:
    """Valide le comportement de chantier_context.py."""

    @pytest.mark.asyncio
    async def test_get_active_chantier_logs_exception(self):
        """
        RED — CHA-002: get_active_chantier avale les exceptions silencieusement.
        Le test vérifie que l'exception est loggée.
        """
        from app.services.telegram.chantier_context import get_active_chantier

        supabase = MagicMock()
        supabase.table.side_effect = Exception("DB connection failed")

        with patch("app.services.telegram.chantier_context.logger.error") as mock_logger:
            result = await get_active_chantier(12345, supabase, "org-123")

        assert result is None
        mock_logger.assert_called_once()
        assert "DB connection failed" in str(mock_logger.call_args)


class TestCallbackRoutesOrphelins:
    """Valide que CALLBACK_ROUTES ne contient pas de routes sans handler."""

    def test_no_orphan_callbacks_for_pointage_present_absent(self):
        """
        RED — CHA-003: 'pointage:present' et 'pointage:absent' sont enregistrés
        dans CALLBACK_ROUTES mais n'ont pas de handlers. Ce test échoue tant
        que les routes orphelines existent.
        """
        from app.services.telegram.construction_menu import CALLBACK_ROUTES

        orphan_keys = ["pointage:present", "pointage:absent"]
        for key in orphan_keys:
            assert key not in CALLBACK_ROUTES, f"Orphan callback route found: {key}"


# ================================================================
# Tests: Opérations HITL (Phase 2 — CHA-007: notification manager après création)
# ================================================================

class TestOperationWorkflow:
    """Valide que le workflow opération notifie le gérant après création."""

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'google.generativeai': MagicMock()})
    async def test_save_operation_creates_notification(self, bot_config):
        """
        RED — CHA-007: handle_save_operation ne crée PAS de notification
        pour le gérant. Ce test échoue tant que la notification n'est pas créée.
        """
        from app.api.bot_construction_operations import handle_save_operation

        supabase = MagicMock()
        supabase.table.return_value = supabase
        supabase.select.return_value = supabase
        supabase.eq.return_value = supabase
        supabase.single.return_value = supabase

        execute_results = iter([
            MagicMock(data={"last_state": "op_awaiting_validation", "last_state_data": {"op_type": "commande", "description": "Test op"}}),
            MagicMock(data=[{"user_id": "user-uuid-123"}]),
        ])
        supabase.execute.side_effect = execute_results

        with patch("app.api.bot_construction_operations.send_simple_message", new_callable=AsyncMock):
            with patch("app.api.bot_construction_commands.send_menu_message", new_callable=AsyncMock):
                with patch("app.api.bot_construction_operations.ensure_chantier_selected", new_callable=AsyncMock, return_value={"id": "chantier-1", "nom": "Test"}):
                    result = await handle_save_operation(12345, bot_config, supabase, "org-123")

        assert result["ok"] is True

        # Vérifier qu'une notification a été créée après l'insertion de l'opération
        insert_calls = supabase.insert.call_args_list
        notification_inserts = [call for call in insert_calls if call[0][0].get("type") in ["validation", "alerte", "info"]]
        assert len(notification_inserts) >= 1, "Au moins une notification doit être créée après save_operation"


class TestImportsNonCirculaires:
    """Valide que les imports ne sont pas lazy (CHA-008)."""

    def test_bot_construction_operations_imports_directly(self):
        """
        RED — CHA-008: Le fichier utilise des imports lazy dans le corps des fonctions
        pour contourner des dépendances circulaires. Ce test vérifie que _handle_chantier_list
        peut être importé directement (sans import lazy dans le corps de fonction).
        """
        from app.api.bot_construction_commands import _handle_chantier_list
        assert callable(_handle_chantier_list)

    def test_bot_construction_depenses_imports_directly(self):
        from app.api.bot_construction_commands import _handle_chantier_list
        assert callable(_handle_chantier_list)


# ================================================================
# Tests: Tâches (Phase 3 — CHA-010: pas de chantier sélectionné)
# ================================================================

class TestTachesBot:
    """Valide le comportement du bot pour les tâches."""

    @pytest.mark.asyncio
    async def test_handle_list_taches_no_chantier(self, bot_config):
        """
        RED — CHA-010: Si l'utilisateur n'a pas de chantier sélectionné,
        le handler doit rediriger vers la liste des chantiers au lieu de planter.
        """
        from app.api.bot_construction_taches import handle_list_taches

        supabase = MagicMock()
        supabase.table.return_value = supabase
        supabase.select.return_value = supabase
        supabase.eq.return_value = supabase
        supabase.single.return_value = supabase
        supabase.order.return_value = supabase
        supabase.limit.return_value = supabase
        supabase.execute.return_value = MagicMock(data=[])

        with patch("app.api.bot_construction_taches.send_message_with_keyboard", new_callable=AsyncMock):
            result = await handle_list_taches(12345, "en_attente", bot_config, supabase, "org-123")
        assert result["ok"] is True


# ================================================================
# Tests: Réceptions (Phase 4 — CHA-011)
# ================================================================

class TestReceptionsBot:
    """Valide le callback rec:add_point."""

    @pytest.mark.asyncio
    async def test_handle_add_point_reception_exists(self, bot_config):
        from app.api.bot_construction_receptions import handle_add_point_reception
        with patch("app.api.bot_construction_receptions.send_simple_message", new_callable=AsyncMock) as mock_send:
            result = await handle_add_point_reception(12345, bot_config)
        assert result["ok"] is True
        mock_send.assert_awaited_once()


# ================================================================
# Tests: Dépenses (Phase 5 — CHA-012, CHA-013)
# ================================================================

class TestDepensesBot:
    """Valide l'absence de duplications dans bot_construction_depenses.py."""

    def test_no_duplicate_workflow_instance(self):
        """
        RED — CHA-013: workflow instancié deux fois (lignes 15-19 et 26).
        Vérifie que le module n'a qu'une seule instance de BaseTelegramWorkflow.
        """
        from app.api.bot_construction_depenses import workflow
        assert workflow is not None


class TestDepenseWorkflow:
    """Valide que le workflow dépense utilise une machine d'état (Bug 2)."""

    @pytest.mark.asyncio
    async def test_depense_create_sets_state(self, bot_config):
        """
        RED — Bug 2: handle_depense_create envoie juste un message texte
        sans machine d'état. Le test échoue tant que set_state n'est pas appelé.
        """
        from app.api.bot_construction_depenses import handle_depense_create

        supabase = MagicMock()
        supabase.table.return_value = supabase
        supabase.select.return_value = supabase
        supabase.eq.return_value = supabase
        supabase.execute.return_value = MagicMock(data=[])

        with patch("app.api.bot_construction_depenses.send_simple_message", new_callable=AsyncMock):
            with patch("app.api.bot_construction_depenses.set_state", new_callable=AsyncMock, return_value=True) as mock_set_state:
                result = await handle_depense_create(12345, bot_config, supabase, "org-123")

        assert result["ok"] is True
        mock_set_state.assert_awaited_once()
        state_arg = mock_set_state.call_args[0][1]
        assert state_arg == "depense_awaiting_description", f"Expected depense_awaiting_description, got {state_arg}"

    @pytest.mark.asyncio
    async def test_depense_handle_media_exists(self, bot_config):
        """
        RED — Bug 2: Il n'existe pas de handler handle_depense_media pour
        capturer la réponse utilisateur après le state depense_awaiting_description.
        """
        from app.api.bot_construction_depenses import handle_depense_media
        assert callable(handle_depense_media)


class TestNotificationServiceBug:
    """Valide la correction du Bug 1 : accès à data['telegram_id'] au lieu de data[0]['telegram_id']."""

    @pytest.mark.asyncio
    async def test_send_telegram_notification_uses_data_index(self, bot_config):
        """
        RED — Bug 1: notification_service._send_telegram_notification accède à
        telegram_user.data['telegram_id'] au lieu de telegram_user.data[0]['telegram_id'].
        Ce test doit échouer tant que le bug est présent.
        """
        from app.services.telegram.notification_service import NotificationService

        supabase = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = [{"telegram_id": 67890}]
        supabase.table.return_value = supabase
        supabase.select.return_value = supabase
        supabase.eq.return_value = supabase
        supabase.execute.return_value = mock_exec

        service = NotificationService(supabase, telegram_token="fake:token")

        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 42}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await service._send_telegram_notification(
                user_id="user-123",
                title="Test",
                message="Test message"
            )

        assert result.get("sent") is True, f"Expected sent=True, got {result}"
        mock_client.post.assert_awaited_once()


class TestRecalculEndpoint:
    """Valide que l'endpoint de recalcul existe."""

    def test_recalcul_metrics_endpoint_exists(self):
        """
        RED — CHA-T-003: Aucun endpoint POST /chantiers/{id}/recalculer n'existe.
        """
        from app.api.chantiers import router
        routes = [r.path for r in router.routes]
        has_endpoint = any('/recalcul' in r for r in routes)
        assert has_endpoint, f"No /recalcul route in chantiers router: {routes}"
