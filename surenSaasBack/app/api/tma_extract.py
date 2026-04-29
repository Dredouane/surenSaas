"""
TMA Extract — Endpoint d'extraction IA pour la Telegram Mini App.

POST /api/v1/tma/extract
  body: { text: string, workflow: string, file?: File }
  return: { is_valid: bool, data: dict, guardrail_issues?: string[], error?: string }

Workflows supportés : avancement, operation, depense, tache
"""

from typing import Dict, Any, Optional
import logging

import app.services.ai.extractor as _extractor_mod
from app.services.ai.validators import (
    AvancementSchema,
    OperationSchema,
    DepenseSchema,
)

logger = logging.getLogger(__name__)

WORKFLOW_MAP = {
    "avancement": {
        "extract_fn": "tma_extract_and_refine_avancement",
        "validate": AvancementSchema.validate,
    },
    "operation": {
        "extract_fn": "tma_extract_operation",
        "validate": OperationSchema.validate,
    },
    "depense": {
        "extract_fn": "tma_extract_depense",
        "validate": DepenseSchema.validate,
    },
}


async def _resolve_extract(extract_fn: str):
    """Résout dynamiquement le nom de la fonction pour permettre le mocking."""
    return getattr(_extractor_mod, extract_fn)


async def extract_workflow(
    workflow: str,
    text: str,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Extrait et valide les données pour un workflow donné."""
    wf_config = WORKFLOW_MAP.get(workflow)
    if not wf_config:
        return {
            "is_valid": False,
            "data": {},
            "error": f"Workflow inconnu: {workflow}",
        }

    try:
        extract_fn = await _resolve_extract(wf_config["extract_fn"])
        raw = await extract_fn(text, file_path)

        if raw.get("_fallback") or raw.get("warning"):
            return {
                "is_valid": True,
                "data": raw.get("data") or raw.get("extracted_data") or {"description": text},
                "warning": "Extraction IA indisponible, données brutes",
            }

        data = raw.get("extracted_data") or raw
        validation = wf_config["validate"](data)

        return {
            "is_valid": validation.is_valid,
            "data": validation.sanitized_data if validation.is_valid else data,
            "guardrail_issues": validation.errors if not validation.is_valid else [],
            "errors": validation.errors if not validation.is_valid else None,
        }

    except Exception as e:
        logger.error(f"Erreur extraction {workflow}: {e}")
        return {
            "is_valid": False,
            "data": {},
            "error": str(e),
        }
