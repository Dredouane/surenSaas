"""
Routes Hermès — Proxy Chat + Triage.

Relie le Frontend SaaS à l'API Hermès (OpenAI-compatible) sur le VPS.
- POST /api/v1/hermes/chat : proxy de chat avec contexte chantier
- GET /api/v1/triage/summary : synthèse de l'onglet triage
"""

from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["hermes_proxy"])


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    chantier_id: Optional[str] = None
    org_id: Optional[str] = None
    user_role: Optional[str] = None


def _get_hermes_client():
    from app.services.hermes_client import get_hermes_client
    return get_hermes_client()


@router.post("/hermes/chat")
async def hermes_chat(
    body: ChatRequest,
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Proxy de chat intelligent vers Hermès.

    Reçoit les messages du Front SaaS, ajoute le contexte (chantier_id,
    user_role), et transmet à l'API Hermès sur le VPS.
    """
    from app.api.tools_rest import verify_tools_api_key
    verify_tools_api_key(x_api_key)

    if not body.messages:
        raise HTTPException(status_code=400, detail="messages requis")

    client = _get_hermes_client()

    # Ajouter le contexte utilisateur si fourni
    context = {}
    if body.chantier_id:
        context["chantier_id"] = body.chantier_id
    if body.org_id:
        context["org_id"] = body.org_id
    if body.user_role:
        context["user_role"] = body.user_role

    try:
        messages_dict = [{"role": m.role, "content": m.content} for m in body.messages]
        result = await client.chat(messages=messages_dict, context=context if context else None)
        return result
    except Exception as e:
        logger.error(f"[HermesProxy] Erreur chat: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Erreur de communication avec l'assistant: {str(e)}",
        )


@router.get("/triage/summary")
async def triage_summary(
    org_id: str = Query(...),
    chantier_id: str = Query(None),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Génère une synthèse de l'onglet triage via Hermès.

    Hermès analyse les données des threads et emails du chantier
    pour produire un résumé exécutif (retards, tâches, urgences...).
    """
    from app.api.tools_rest import verify_tools_api_key
    verify_tools_api_key(x_api_key)

    client = _get_hermes_client()

    # Récupérer les données de contexte depuis Supabase
    from app.api.auth import get_supabase
    sb = get_supabase()

    context = {"org_id": org_id}
    if chantier_id:
        context["chantier_id"] = chantier_id

        # Stats du chantier
        chantier_resp = sb.table("chantiers").select("nom, ref, statut")\
            .eq("id", chantier_id).maybe_single().execute()
        if chantier_resp.data:
            context["chantier_nom"] = chantier_resp.data.get("nom")
            context["chantier_ref"] = chantier_resp.data.get("ref")
            context["chantier_statut"] = chantier_resp.data.get("statut")

        # Threads du chantier
        threads_resp = sb.table("email_threads")\
            .select("id, subject, status, email_count, last_email_at")\
            .eq("org_id", org_id)\
            .eq("detected_chantier_id", chantier_id)\
            .order("last_email_at", desc=True)\
            .limit(20).execute()

        if threads_resp.data:
            by_status = {}
            for t in threads_resp.data:
                s = t.get("status", "UNKNOWN")
                by_status[s] = by_status.get(s, 0) + 1

            context["threads_total"] = len(threads_resp.data)
            context["threads_par_statut"] = str(by_status)
            context["dernier_email"] = threads_resp.data[0].get("last_email_at") if threads_resp.data else None

        # Analyses en attente
        analysis_resp = sb.table("email_ai_analysis").select("id, detected_urgency, analyzed_at")\
            .eq("email_thread_id", sb.table("email_threads").select("id")\
                .eq("org_id", org_id)\
                .eq("detected_chantier_id", chantier_id))\
            .order("analyzed_at", desc=True)\
            .limit(5).execute()

        if analysis_resp.data:
            context["analyses_en_attente"] = len(analysis_resp.data)

    try:
        result = await client.triage_summary(context=context)
        return result
    except Exception as e:
        logger.error(f"[HermesProxy] Erreur triage summary: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Erreur de génération du résumé: {str(e)}",
        )
