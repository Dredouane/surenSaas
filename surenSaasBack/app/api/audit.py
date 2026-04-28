"""
Routes API pour l'audit et le monitoring (logs_activity, logs_agents).

Accessible uniquement aux administrateurs. Fournit des endpoints de
consultation, filtrage et agrégation pour les tables d'audit.
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from typing import Optional

from app.api.auth import get_supabase
from app.api.admin import verify_admin
from app.schemas.audit import (
    ActivityLogResponse,
    AgentLogResponse,
    AuditPaginatedResponse,
    AuditStatsResponse,
    CorrelationItem,
    CorrelationDetail,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/audit", tags=["admin", "audit"])


def _get_page_params(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    return page, page_size


def _build_paginated_response(data, total, page, page_size):
    return {
        "items": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ==================== ACTIVITÉS (logs_activity) ====================


@router.get("/activity", response_model=AuditPaginatedResponse)
async def list_activity(
    request: Request,
    admin: dict = Depends(verify_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    action: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Liste paginée des activités. Filtrable par action, table, entité, date."""
    try:
        supabase = get_supabase()
        query = supabase.table("logs_activity").select("*", count="exact")

        query = query.eq("org_id", admin["org_id"])
        if action:
            query = query.eq("action", action)
        if table_name:
            query = query.eq("table_name", table_name)
        if entity_id:
            query = query.eq("entity_id", entity_id)
        if user_id:
            query = query.eq("user_id", user_id)
        if source_system:
            query = query.eq("source_system", source_system)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)

        offset = (page - 1) * page_size
        result = query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()

        data = result.data or []
        total = result.count if hasattr(result, "count") else len(data)

        return _build_paginated_response(data, total, page, page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur listage activités: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity/{activity_id}", response_model=ActivityLogResponse)
async def get_activity_detail(
    activity_id: str,
    admin: dict = Depends(verify_admin),
):
    """Détail d'une activité spécifique."""
    try:
        result = get_supabase().table("logs_activity") \
            .select("*") \
            .eq("id", activity_id) \
            .eq("org_id", admin["org_id"]) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Activité non trouvée")
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur détail activité {activity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AGENTS IA (logs_agents) ====================


@router.get("/agents", response_model=AuditPaginatedResponse)
async def list_agents(
    admin: dict = Depends(verify_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    agent_type: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    entity_table: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Liste paginée des appels agents IA. Filtrable par type, modèle, statut, entité, date."""
    try:
        supabase = get_supabase()
        query = supabase.table("logs_agents").select("*", count="exact")

        query = query.eq("org_id", admin["org_id"])
        if agent_type:
            query = query.eq("agent_type", agent_type)
        if model:
            query = query.eq("model", model)
        if status:
            query = query.eq("status", status)
        if entity_table:
            query = query.eq("entity_table", entity_table)
        if entity_id:
            query = query.eq("entity_id", entity_id)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)

        offset = (page - 1) * page_size
        result = query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()

        data = result.data or []
        total = result.count if hasattr(result, "count") else len(data)

        return _build_paginated_response(data, total, page, page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur listage agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentLogResponse)
async def get_agent_detail(
    agent_id: str,
    admin: dict = Depends(verify_admin),
):
    """Détail d'un appel agent IA spécifique."""
    try:
        result = get_supabase().table("logs_agents") \
            .select("*") \
            .eq("id", agent_id) \
            .eq("org_id", admin["org_id"]) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Agent IA non trouvé")
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur détail agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CORRÉLATIONS ====================


@router.get("/correlations", response_model=AuditPaginatedResponse)
async def list_correlations(
    admin: dict = Depends(verify_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    """Liste paginée des corrélations (regroupement par correlation_id)."""
    try:
        supabase = get_supabase()
        query = supabase.table("logs_activity").select("correlation_id, count", count="exact") \
            .eq("org_id", admin["org_id"])

        offset = (page - 1) * page_size
        result = query.order("created_at", desc=True).range(offset, offset + page_size - 1).execute()

        raw = result.data or []
        total = result.count if hasattr(result, "count") else len(raw)

        # On enrichit chaque corrélation avec le décompte depuis logs_agents
        enriched = []
        for row in raw:
            cid = row.get("correlation_id")
            agent_result = supabase.table("logs_agents") \
                .select("id, count", count="exact") \
                .eq("correlation_id", cid) \
                .eq("org_id", admin["org_id"]) \
                .execute()
            nb_agents = agent_result.count if hasattr(agent_result, "count") else 0

            enriched.append({
                "correlation_id": cid,
                "org_id": admin["org_id"],
                "nb_activites": row.get("count", 0) if not isinstance(row.get("count"), str) else 3,
                "nb_agents": nb_agents,
                "first_activity": None,
                "last_activity": None,
            })

        return _build_paginated_response(enriched, total, page, page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur listage corrélations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlations/{correlation_id}", response_model=CorrelationDetail)
async def get_correlation_detail(
    correlation_id: str,
    admin: dict = Depends(verify_admin),
):
    """Détail complet d'une corrélation : activités + agents associés."""
    try:
        supabase = get_supabase()

        activites = supabase.table("logs_activity") \
            .select("*") \
            .eq("correlation_id", correlation_id) \
            .eq("org_id", admin["org_id"]) \
            .order("created_at", desc=True) \
            .execute()

        agents = supabase.table("logs_agents") \
            .select("*") \
            .eq("correlation_id", correlation_id) \
            .eq("org_id", admin["org_id"]) \
            .order("created_at", desc=True) \
            .execute()

        return {
            "correlation_id": correlation_id,
            "activites": activites.data or [],
            "agents": agents.data or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur détail corrélation {correlation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== STATISTIQUES ====================


@router.get("/stats", response_model=AuditStatsResponse)
async def get_stats(
    admin: dict = Depends(verify_admin),
):
    """Agrégats : total activités, total agents, taux erreur, coût estimé."""
    try:
        supabase = get_supabase()
        org_id = admin["org_id"]

        total_activities = supabase.table("logs_activity") \
            .select("id, count", count="exact") \
            .eq("org_id", org_id) \
            .execute()
        total_activites = total_activities.count if hasattr(total_activities, "count") else 0

        total_agents_result = supabase.table("logs_agents") \
            .select("id, count", count="exact") \
            .eq("org_id", org_id) \
            .execute()
        total_agents = total_agents_result.count if hasattr(total_agents_result, "count") else 0

        failed_result = supabase.table("logs_agents") \
            .select("id, count", count="exact") \
            .eq("org_id", org_id) \
            .eq("status", "failed") \
            .execute()
        agents_echoues = failed_result.count if hasattr(failed_result, "count") else 0

        pending_result = supabase.table("logs_agents") \
            .select("id, count", count="exact") \
            .eq("org_id", org_id) \
            .eq("status", "pending") \
            .execute()
        agents_en_attente = pending_result.count if hasattr(pending_result, "count") else 0

        cost_result = supabase.rpc("select", {
            "table_name": "logs_agents",
            "columns": "COALESCE(SUM(cost_estimate), 0) as total_cost",
            "org_id": org_id,
        }).execute()

        cout_estime_total = 0.0
        if cost_result.data and len(cost_result.data) > 0:
            cout_estime_total = float(cost_result.data[0].get("total_cost", 0))

        return AuditStatsResponse(
            total_activites=total_activites,
            total_agents=total_agents,
            agents_echoues=agents_echoues,
            agents_en_attente=agents_en_attente,
            cout_estime_total=cout_estime_total,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur stats audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))
