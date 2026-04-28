"""
Service d'audit générique pour la traçabilité des mutations et interactions IA.
Remplace: TelegramAuditService, chantier_audit_trail triggers, invoice_status_history triggers.

Utilisation:
    audit = AuditService(supabase, file_storage_service)
    await audit.log_activity(org_id="...", correlation_id="...", action="create", table_name="chantiers", ...)
    await audit.log_agent(org_id="...", correlation_id="...", agent_type="gemini_extraction", ...)
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """
    Service d'audit transverse. Genere et stocke les traces dans logs_activity et logs_agents.
    """

    def __init__(self, supabase_client: Any, file_storage_service=None):
        self.supabase = supabase_client
        self.file_storage = file_storage_service

    # ------------------------------------------------------------------
    # Activity Logs (mutations CRUD)
    # ------------------------------------------------------------------

    async def log_activity(
        self,
        org_id: str,
        correlation_id: str,
        action: str,
        table_name: str,
        entity_id: Optional[str] = None,
        entity_ref: Optional[str] = None,
        previous_state: Optional[dict] = None,
        new_state: Optional[dict] = None,
        user_id: Optional[str] = None,
        user_name: str = "",
        source_system: str = "api",
        source_details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        processing_duration_ms: Optional[int] = None,
    ) -> Optional[str]:
        """
        Enregistre une mutation CRUD dans logs_activity.
        Retourne l'ID de l'enregistrement ou None si erreur.
        """
        try:
            delta = {}
            if previous_state and new_state:
                delta = self._compute_delta(previous_state, new_state)

            record = {
                "org_id": org_id,
                "correlation_id": correlation_id,
                "action": action,
                "table_name": table_name,
                "entity_id": entity_id,
                "entity_ref": entity_ref,
                "previous_state": json.dumps(previous_state) if previous_state else "{}",
                "new_state": json.dumps(new_state) if new_state else "{}",
                "delta": json.dumps(delta),
                "user_id": user_id,
                "user_name": user_name,
                "source_system": source_system,
                "source_details": json.dumps(source_details or {}),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "processing_duration_ms": processing_duration_ms,
            }

            result = self.supabase.table("logs_activity").insert(record).execute()
            inserted_id = result.data[0]["id"] if result.data else None
            return inserted_id
        except Exception as e:
            logger.error(f"Erreur log_activity: {e}")
            return None

    # ------------------------------------------------------------------
    # Agent Logs (interactions IA)
    # ------------------------------------------------------------------

    async def log_agent(
        self,
        org_id: str,
        correlation_id: str,
        agent_type: str,
        model: str,
        user_prompt: str,
        response_text: Optional[str] = None,
        system_prompt: Optional[str] = None,
        raw_input: Optional[dict] = None,
        raw_output: Optional[dict] = None,
        extracted_data: Optional[dict] = None,
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
        agent_version: str = "",
        parent_correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Enregistre une interaction IA dans logs_agents.
        Archive aussi le payload dans R2 si file_storage est configuré.
        Retourne l'ID de l'enregistrement ou None si erreur.
        """
        try:
            payload_for_blob = {
                "correlation_id": correlation_id,
                "agent_type": agent_type,
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_text": response_text,
                "raw_input": raw_input,
                "raw_output": raw_output,
                "extracted_data": extracted_data,
                "metadata": {
                    "processing_duration_ms": processing_duration_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost_estimate": cost_estimate,
                },
            }

            blob_path = None
            if self.file_storage:
                try:
                    blob_path = await self.file_storage.store_agent_interaction_blob(
                        correlation_id=correlation_id,
                        agent_type=agent_type,
                        data=payload_for_blob,
                        org_id=org_id,
                    )
                except Exception as e:
                    logger.warning(f"Impossible d'archiver le blob R2: {e}")

            record = {
                "org_id": org_id,
                "correlation_id": correlation_id,
                "parent_correlation_id": parent_correlation_id,
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
                "blob_storage_path": blob_path,
            }

            result = self.supabase.table("logs_agents").insert(record).execute()
            inserted_id = result.data[0]["id"] if result.data else None
            return inserted_id
        except Exception as e:
            logger.error(f"Erreur log_agent: {e}")
            return None

    # ------------------------------------------------------------------
    # HITL Feedback
    # ------------------------------------------------------------------

    async def record_hitl_feedback(
        self,
        agent_log_id: str,
        feedback: str,
        user_id: str,
        action: Optional[str] = None,
    ) -> bool:
        """
        Enregistre un feedback humain (HITL) sur une interaction IA.
        Utilisé pour le "Human-In-The-Loop" : lier une validation humaine à un appel IA.
        """
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

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def _compute_delta(self, old: dict, new: dict) -> dict:
        """Calcule les différences entre deux états."""
        changes = {}
        for key in new:
            if key in old:
                if old[key] != new[key]:
                    changes[key] = {"old": old[key], "new": new[key]}
            else:
                changes[key] = {"old": None, "new": new[key]}
        for key in old:
            if key not in new:
                changes[key] = {"old": old[key], "new": None}
        return changes
