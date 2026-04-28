"""
LogsAgentService — Couche dédiée au logging des interactions IA TMA.

Enrichit le AuditService existant avec les champs spécifiques TMA :
  - origin_context (TELEGRAM_BOT, TMA_PROGRESS_SLIDER, TMA_EXPENSE_SCANNER)
  - target_entity (JSONB : {type, id, project_id})
  - device_info (JSONB : {platform, app_version, connection_type})
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.core.logging import get_logger

logger = get_logger(__name__)

ORIGIN_BOT = "TELEGRAM_BOT"
ORIGIN_TMA_PROGRESS = "TMA_PROGRESS_SLIDER"
ORIGIN_TMA_EXPENSE = "TMA_EXPENSE_SCANNER"


class LogsAgentService:
    def __init__(self, supabase_client: Any):
        self.supabase = supabase_client

    def log_interaction(
        self,
        org_id: str,
        correlation_id: str,
        origin_context: str,
        agent_type: str,
        model: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        raw_input: Optional[dict] = None,
        raw_output: Optional[dict] = None,
        extracted_data: Optional[dict] = None,
        response_text: Optional[str] = None,
        status: str = "completed",
        processing_duration_ms: Optional[int] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        cost_estimate: float = 0.0,
        input_validated: bool = False,
        output_validated: bool = False,
        validation_result: Optional[dict] = None,
        guardrail_issues: Optional[list] = None,
        entity_table: Optional[str] = None,
        entity_id: Optional[str] = None,
        parent_correlation_id: Optional[str] = None,
        agent_version: str = "",
        target_entity: Optional[dict] = None,
        device_info: Optional[dict] = None,
    ) -> Optional[str]:
        try:
            record = {
                "org_id": org_id,
                "correlation_id": correlation_id,
                "parent_correlation_id": parent_correlation_id,
                "origin_context": origin_context,
                "agent_type": agent_type,
                "agent_version": agent_version,
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw_input": json.dumps(raw_input) if raw_input else "{}",
                "raw_output": json.dumps(raw_output) if raw_output else "{}",
                "response_text": response_text,
                "extracted_data": json.dumps(extracted_data) if extracted_data else "{}",
                "status": status,
                "processing_duration_ms": processing_duration_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_estimate": cost_estimate,
                "input_validated": input_validated,
                "output_validated": output_validated,
                "validation_result": json.dumps(validation_result) if validation_result else "{}",
                "guardrail_issues": json.dumps(guardrail_issues or []),
                "entity_table": entity_table,
                "entity_id": entity_id,
                "target_entity": json.dumps(target_entity) if target_entity else "{}",
                "device_info": json.dumps(device_info) if device_info else "{}",
            }

            result = self.supabase.table("logs_agents").insert(record).execute()
            inserted_id = result.data[0]["id"] if result.data else None
            return inserted_id
        except Exception as e:
            logger.error(f"Erreur log_interaction: {e}")
            return None

    def record_hitl_feedback(
        self,
        agent_log_id: str,
        feedback: str,
        user_id: str,
        action: Optional[str] = None,
    ) -> bool:
        try:
            self.supabase.table("logs_agents").update({
                "hitl_feedback": json.dumps({"feedback": feedback, "timestamp": datetime.utcnow().isoformat()}),
                "hitl_user_id": user_id,
                "hitl_action": action,
                "hitl_reviewed_at": datetime.utcnow().isoformat(),
            }).eq("id", agent_log_id).execute()
            return True
        except Exception as e:
            logger.error(f"Erreur record_hitl_feedback: {e}")
            return False

    def get_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        try:
            result = self.supabase.table("logs_agents").select("*").eq("correlation_id", correlation_id).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Erreur get_by_correlation_id: {e}")
            return []

    def get_by_entity(self, entity_table: str, entity_id: str) -> List[Dict[str, Any]]:
        try:
            result = self.supabase.table("logs_agents").select("*").eq("entity_table", entity_table).eq("entity_id", entity_id).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Erreur get_by_entity: {e}")
            return []

    def get_by_origin(self, origin_context: str) -> List[Dict[str, Any]]:
        try:
            result = self.supabase.table("logs_agents").select("*").eq("origin_context", origin_context).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Erreur get_by_origin: {e}")
            return []
