from typing import List, Optional
from datetime import date as _date
import logging
import re
from uuid import UUID
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.api.auth import get_supabase

logger = logging.getLogger(__name__)


# ─── Schémas ─────────────────────────────────────────────────────

class MatchResourcesSchema(BaseModel):
    org_id: str = Field(description="UUID de l'organisation")
    chantier_id: str = Field(description="UUID ou ref du chantier")
    query: str = Field(description="Prénom ou nom partiel à rechercher")


class UpsertAttendanceSchema(BaseModel):
    org_id: str = Field(description="UUID de l'organisation")
    chantier_id: str = Field(description="UUID ou ref du chantier")
    date_pointage: str = Field(description="Date du pointage (YYYY-MM-DD)")
    ressources: List[dict] = Field(
        description='Liste des présences : [{\"ressource_id\": \"uuid\", \"present\": bool, \"nom\": \"...\"}]'
    )


# ─── Implémentations internes (testables directement) ─────────────

def _resolve_chantier_uuid(org_id: str, chantier_id: str) -> str:
    """Résout un chantier_id (UUID ou ref comme 'CH-001') en UUID string."""
    try:
        return str(UUID(chantier_id))
    except (ValueError, TypeError):
        from app.api.chantiers import resolve_chantier_uuid
        return resolve_chantier_uuid(org_id, chantier_id)


def _match_resources_internal(org_id: str, chantier_id: str, query: str, _supabase=None) -> dict:
    """Implémentation réelle de match_resources."""
    uuid = _resolve_chantier_uuid(org_id, chantier_id)
    sb = _supabase or get_supabase()

    result = (
        sb
        .table("chantier_ressources")
        .select("id, nom, type")
        .eq("org_id", org_id)
        .execute()
    )

    if not result.data:
        return {"success": True, "data": [], "count": 0}

    query_lower = query.lower().strip()
    query_tokens = set(re.findall(r"\w+", query_lower))

    scored = []
    for res in result.data:
        nom_lower = (res.get("nom") or "").lower()
        score = 0.0
        if nom_lower == query_lower:
            score = 1.0
        elif query_lower in nom_lower:
            score = 0.8
        else:
            nom_tokens = set(re.findall(r"\w+", nom_lower))
            if query_lower in nom_tokens:
                score = 0.7
            elif nom_tokens & query_tokens:
                score = 0.5

        if score > 0:
            scored.append({
                "id": res["id"],
                "nom": res.get("nom", ""),
                "type": res.get("type", "homme"),
                "score": round(score, 2),
                "confiance": "haute" if score >= 0.8 else "moyenne" if score >= 0.5 else "faible",
            })

    scored.sort(key=lambda x: x["score"], reverse=True)

    return {
        "success": True,
        "data": scored[:5],
        "count": len(scored),
        "message": f"{len(scored)} correspondance(s) trouvée(s) pour '{query}'",
    }


def _upsert_attendance_internal(
    org_id: str,
    chantier_id: str,
    date_pointage: str,
    ressources: List[dict],
    _supabase=None,
) -> dict:
    """Implémentation réelle de upsert_attendance."""
    # Date future
    today = _date.today().isoformat()
    if date_pointage > today:
        return {
            "success": False,
            "data": None,
            "error": f"Date pointage {date_pointage} dans le futur. Impossible.",
            "suggestion": "Utilise une date passée ou aujourd'hui.",
            "message": None,
        }

    uuid = _resolve_chantier_uuid(org_id, chantier_id)
    sb = _supabase or get_supabase()

    # 1. Créer ou récupérer le pointage parent
    pt_result = (
        sb.table("chantier_pointages")
        .select("id, status")
        .eq("chantier_id", uuid)
        .eq("date", date_pointage)
        .execute()
    )

    if pt_result.data:
        pt_id = pt_result.data[0]["id"]
        pt_statut = pt_result.data[0].get("status")
        if pt_statut in ("en_attente_validation", "valide"):
            return {
                "success": False,
                "data": None,
                "error": f"Pointage déjà {pt_statut}. Impossible de modifier.",
                "suggestion": "Contacte le gérant pour modifier un pointage validé.",
                "message": None,
            }
    else:
        pt_create = (
            sb.table("chantier_pointages")
            .insert({
                "org_id": org_id,
                "chantier_id": uuid,
                "date": date_pointage,
                "status": "brouillon",
            })
            .execute()
        )
        pt_id = pt_create.data[0]["id"] if pt_create.data else None
        if not pt_id:
            return {"success": False, "data": None, "error": "Échec création pointage parent"}

    # 2. Upsert les lignes de présence
    upserted = []
    for r in ressources:
        res_id = r.get("ressource_id") or r.get("id") or ""
        present = bool(r.get("present", r.get("presence", True)))
        nom = r.get("nom", res_id)

        existing = (
            sb.table("chantier_pointage_ressources")
            .select("id")
            .eq("pointage_id", pt_id)
            .eq("ressource_id", res_id)
            .execute()
        )

        line_data = {
            "pointage_id": pt_id,
            "ressource_id": res_id,
            "presence": present,
            "periode": "journee",
            "metadata": {"nom": nom},
        }

        if existing.data:
            existing_id = existing.data[0]["id"]
            # Préserver les metadata existantes
            existing_meta = sb.table("chantier_pointage_ressources").select("metadata").eq("id", existing_id).execute()
            old_meta = existing_meta.data[0].get("metadata", {}) if existing_meta.data else {}
            if isinstance(old_meta, dict) and not old_meta.get("nom"):
                old_meta["nom"] = nom
                line_data["metadata"] = old_meta
            sb.table("chantier_pointage_ressources").update(line_data).eq(
                "id", existing_id
            ).execute()
        else:
            line_data["org_id"] = org_id
            sb.table("chantier_pointage_ressources").insert(line_data).execute()

        upserted.append({"ressource_id": res_id, "nom": nom, "present": present})

    logger.info("[ATTENDANCE_TOOL] Pointage %s: %d ressources", date_pointage, len(upserted))
    return {
        "success": True,
        "data": {"pointage_id": pt_id, "ressources": upserted},
        "error": None,
        "suggestion": None,
        "message": (
            f"Pointage du {date_pointage} mis à jour : "
            f"{sum(1 for u in upserted if u['present'])} présent(s), "
            f"{sum(1 for u in upserted if not u['present'])} absent(s)."
        ),
    }


# ─── Tools LangGraph (décorés) ──────────────────────────────────

@tool("match_resources", args_schema=MatchResourcesSchema)
def match_resources(org_id: str, chantier_id: str, query: str, context_summary: str = "") -> dict:
    """Cherche des ressources par fuzzy matching sur le champ 'nom'."""
    return _match_resources_internal(org_id=org_id, chantier_id=chantier_id, query=query)


@tool("upsert_attendance", args_schema=UpsertAttendanceSchema)
def upsert_attendance(
    org_id: str,
    chantier_id: str,
    date_pointage: str,
    ressources: List[dict],
    context_summary: str = "",
) -> dict:
    """Enregistre ou met à jour les présences pour un pointage à une date donnée."""
    return _upsert_attendance_internal(
        org_id=org_id,
        chantier_id=chantier_id,
        date_pointage=date_pointage,
        ressources=ressources,
    )
