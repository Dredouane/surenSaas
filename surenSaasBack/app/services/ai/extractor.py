"""
Module d'extraction pour les workflows Telegram.

Point d'entrée unique vers le système agentique.
Tous les workflows (avancement, opération, dépense, tâche, pointage)
utilisent WorkflowExtractor depuis agents/workflow_extractor.py.
"""

import logging
from typing import Dict, Any, Optional

from app.agents.workflow_extractor import WorkflowExtractor

logger = logging.getLogger(__name__)

_extractor: Optional[WorkflowExtractor] = None


def _get_extractor() -> WorkflowExtractor:
    global _extractor
    if _extractor is None:
        _extractor = WorkflowExtractor()
    return _extractor


async def extract_avancement(text: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    result = _get_extractor().extract(text, "avancement", file_path)
    if hasattr(result, '__await__'):
        return await result
    return result


async def extract_and_refine_avancement(text: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    raw = _get_extractor().extract(text, "avancement", file_path)
    if hasattr(raw, '__await__'):
        raw = await raw
    if raw.get("_fallback"):
        return raw
    d = raw.get("extracted_data") or raw
    qte = d.get("quantite") or 0
    pu = d.get("prix_unitaire") or 0
    pct = d.get("avancement_pourcentage") or 0
    try:
        qte_f = float(qte)
        pu_f = float(pu)
        pct_f = float(pct)
    except (ValueError, TypeError):
        qte_f = pu_f = pct_f = 0
    mt = qte_f * pu_f
    am = mt * pct_f / 100 if pct_f > 0 else 0
    return {
        "description": raw.get("description") or text,
        "quantite": qte_f,
        "prix_unitaire": pu_f,
        "avancement_pourcentage": pct_f,
        "montant_total": mt,
        "avancement_montant": am,
    }


async def extract_operation(text: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    result = _get_extractor().extract(text, "operation", file_path)
    if hasattr(result, '__await__'):
        return await result
    return result


async def extract_depense(text: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    result = _get_extractor().extract(text, "depense", file_path)
    if hasattr(result, '__await__'):
        return await result
    return result
