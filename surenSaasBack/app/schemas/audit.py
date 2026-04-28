"""
Schémas Pydantic pour les endpoints d'audit (logs_activity, logs_agents).
"""

from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class ActivityLogResponse(BaseModel):
    id: str
    org_id: str
    correlation_id: str
    action: str
    table_name: str
    entity_id: Optional[str] = None
    entity_ref: Optional[str] = None
    previous_state: Optional[dict[str, Any]] = None
    new_state: Optional[dict[str, Any]] = None
    delta: Optional[dict[str, Any]] = None
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    source_system: Optional[str] = None
    source_details: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    created_at: Optional[str] = None


class AgentLogResponse(BaseModel):
    id: str
    org_id: str
    correlation_id: str
    parent_correlation_id: Optional[str] = None
    agent_type: str
    agent_version: Optional[str] = None
    model: str
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    raw_input: Optional[dict[str, Any]] = None
    raw_output: Optional[dict[str, Any]] = None
    response_text: Optional[str] = None
    extracted_data: Optional[dict[str, Any]] = None
    status: str
    processing_duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_estimate: Optional[float] = None
    input_validated: Optional[bool] = None
    output_validated: Optional[bool] = None
    validation_result: Optional[dict[str, Any]] = None
    guardrail_issues: Optional[list[Any]] = None
    entity_table: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class AuditPaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class AuditStatsResponse(BaseModel):
    total_activites: int = 0
    total_agents: int = 0
    agents_echoues: int = 0
    agents_en_attente: int = 0
    cout_estime_total: float = 0.0


class CorrelationItem(BaseModel):
    correlation_id: str
    org_id: str
    nb_activites: int
    nb_agents: int
    first_activity: Optional[str] = None
    last_activity: Optional[str] = None


class CorrelationDetail(BaseModel):
    correlation_id: str
    activites: list[ActivityLogResponse]
    agents: list[AgentLogResponse]
