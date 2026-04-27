"""
Base Telegram Workflow Service - Moteur générique pour tous les domaines.
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import uuid
import logging
import httpx

logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    status: str
    data: Dict[str, Any]
    confidence: float = 0.0
    errors: Optional[List[str]] = None

class BaseTelegramWorkflow:
    def __init__(self, supabase_client, audit_service, notification_service):
        self.supabase = supabase_client
        self.audit = audit_service
        self.notifications = notification_service

    async def start_workflow(
        self,
        telegram_id: int,
        org_id: str,
        chantier_id: str,
        message: Dict[str, Any],
        table_name: str,
        workflow_type: str
    ) -> Dict[str, Any]:
        """Workflow: Extraction IA -> Preview User (Validation) -> Brouillon."""
        
        # 1. Extraction (Simulation de l'agent)
        extracted = await self._run_ai_extraction(message, workflow_type)
        
        # 2. Retourner les données pour présentation (ne pas insérer encore)
        return {"success": True, "extracted_data": extracted.data, "table": table_name}

    async def finalize_workflow(
        self,
        org_id: str,
        chantier_id: str,
        table_name: str,
        data: Dict[str, Any]
    ) -> str:
        """Validation finale et insertion en base."""
        record = {
            'id': str(uuid.uuid4()),
            'chantier_id': chantier_id,
            'org_id': org_id,
            'status': 'en_attente_validation',
            'ocr_data': data,
            'created_by_telegram': True
        }
        self.supabase.table(table_name).insert(record).execute()
        return record['id']

    async def _run_ai_extraction(self, message: Dict[str, Any], workflow_type: str) -> ExtractionResult:
        """
        Gère Gemini pour extraire des entités.
        Chaque domaine (pointage, opération) aura son prompt dans app/services/ai/prompts.py
        """
        # Placeholder pour l'agent LLM générique
        return ExtractionResult(status="success", data={"raw": message})
