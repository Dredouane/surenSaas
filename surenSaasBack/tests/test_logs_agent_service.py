#!/usr/bin/env python3
"""
Tests pour LogsAgentService — Couche Audit Trail TMA.

Valide que les logs d'interaction IA sont correctement structurés
avec les nouveaux champs TMA : origin_context, target_entity, device_info.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.logs_agent_service import LogsAgentService


@pytest.fixture
def mock_supabase():
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    return LogsAgentService(supabase_client=mock_supabase)


class TestLogsAgentServiceCreate:
    def test_log_interaction_basic(self, service, mock_supabase):
        mock_result = MagicMock()
        mock_result.data = [{"id": "log-123"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        log_id = service.log_interaction(
            org_id="org-1",
            correlation_id="corr-abc",
            origin_context="TELEGRAM_BOT",
            agent_type="gemini_extraction",
            model="gemini-2.0-flash",
            user_prompt="Enduit facade 50m2 25e/m2 80%",
        )

        assert log_id == "log-123"

    def test_log_interaction_with_full_fields(self, service, mock_supabase):
        mock_result = MagicMock()
        mock_result.data = [{"id": "log-456"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        log_id = service.log_interaction(
            org_id="org-1",
            correlation_id="corr-xyz",
            origin_context="TMA_PROGRESS_SLIDER",
            agent_type="tma_progress_slider",
            model="gemini-2.0-flash",
            system_prompt="Tu es un extracteur...",
            user_prompt="50m2 d enduit a 25e le m2, 80% fait",
            raw_input={"text": "50m2 d enduit a 25e le m2, 80% fait"},
            raw_output={"description": "Enduit facade", "quantite": 50, "prix_unitaire": 25, "avancement_pourcentage": 80},
            extracted_data={"description": "Enduit facade", "quantite": 50, "prix_unitaire": 25, "montant_total": 1250, "avancement_montant": 1000},
            status="completed",
            processing_duration_ms=1234,
            input_tokens=150,
            output_tokens=80,
            total_tokens=230,
            cost_estimate=0.0023,
            input_validated=True,
            output_validated=True,
            validation_result={"is_valid": True, "errors": []},
            guardrail_issues=[],
            entity_table="chantier_situation_lignes",
            entity_id="situation-line-1",
            target_entity={"type": "situation", "id": "sit-uuid", "project_id": "chantier-uuid"},
            device_info={"platform": "ios", "app_version": "1.0.0", "connection_type": "4G"},
        )

        assert log_id == "log-456"
        # Verify all TMA fields were passed to supabase
        insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
        assert insert_call["origin_context"] == "TMA_PROGRESS_SLIDER"
        assert "target_entity" in insert_call
        assert insert_call["device_info"]  # JSON string

    def test_log_interaction_failure_returns_none(self, service, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        log_id = service.log_interaction(
            org_id="org-1",
            correlation_id="corr-fail",
            origin_context="TELEGRAM_BOT",
            agent_type="gemini_extraction",
            model="gemini-2.0-flash",
            user_prompt="test",
        )

        assert log_id is None


class TestLogsAgentServiceHITL:
    def test_record_hitl_feedback(self, service, mock_supabase):
        mock_update = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        result = service.record_hitl_feedback(
            agent_log_id="log-abc",
            feedback="Les données extraites sont correctes",
            user_id="user-123",
            action="approved",
        )

        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args[0][0]
        assert update_call["hitl_action"] == "approved"
        assert update_call["hitl_user_id"] == "user-123"

    def test_record_hitl_feedback_failure(self, service, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.side_effect = Exception("DB error")

        result = service.record_hitl_feedback(
            agent_log_id="log-abc",
            feedback="Correct",
            user_id="user-123",
        )

        assert result is False


class TestLogsAgentServiceQuery:
    def test_get_by_correlation_id(self, service, mock_supabase):
        mock_result = MagicMock()
        mock_result.data = [{"id": "log-1", "correlation_id": "corr-abc"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        logs = service.get_by_correlation_id("corr-abc")

        assert len(logs) == 1
        assert logs[0]["id"] == "log-1"

    def test_get_by_entity(self, service, mock_supabase):
        mock_result = MagicMock()
        mock_result.data = [{"id": "log-1", "entity_table": "chantier_situation_lignes", "entity_id": "line-1"}]
        mock_query = mock_supabase.table.return_value.select.return_value
        mock_query.eq.return_value.eq.return_value.execute.return_value = mock_result

        logs = service.get_by_entity(entity_table="chantier_situation_lignes", entity_id="line-1")

        assert len(logs) == 1

    def test_get_by_origin(self, service, mock_supabase):
        mock_result = MagicMock()
        mock_result.data = [{"id": "log-1", "origin_context": "TELEGRAM_BOT"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        logs = service.get_by_origin("TELEGRAM_BOT")

        assert len(logs) == 1
