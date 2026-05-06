# Phase 2 — Workflow Pointage (Tools DB)

## Objective
Créer 2 tools LangGraph pour le workflow Pointage :
1. `match_resources(query, chantier_id)` — fuzzy search sur les ressources
2. `upsert_attendance(date, chantier_id, org_id, ressources[])` — persistance des présences

---

## Tool 1: `match_resources`

**Fichier :** `/opt/projects/suren/saas/surenSaas/surenSaasBack/app/agents/tools/attendance_tools.py`

```python
from typing import List, Optional
import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.api.auth import get_supabase

logger = logging.getLogger(__name__)

class MatchResourcesSchema(BaseModel):
    org_id: str = Field(description="UUID de l'organisation")
    chantier_id: str = Field(description="UUID ou ref du chantier")
    query: str = Field(description="Prénom ou nom partiel à rechercher")

@tool("match_resources", args_schema=MatchResourcesSchema)
def match_resources(org_id: str, chantier_id: str, query: str) -> dict:
    """
    Cherche des ressources par fuzzy matching sur le champ 'nom'.
    Utilise ILIKE %query% sur la table chantier_ressources.
    Retourne les matchs avec un score de confiance (0.0 à 1.0).
    
    - Si le nom est très court (< 3 chars), se contenter des prénoms complets
    - Retourner max 5 résultats, triés par confiance décroissante
    """
    # Récupérer le vrai UUID du chantier
    try:
        from uuid import UUID
        uuid = UUID(chantier_id)
    except (ValueError, TypeError):
        # Si c'est une ref (CH-001), la résoudre d'abord
        from app.api.chantiers import resolve_chantier_uuid
        uuid = resolve_chantier_uuid(org_id, chantier_id)
    
    # Récupérer toutes les ressources du chantier
    result = get_supabase().table("chantier_ressources")\
        .select("id, nom, type")\
        .eq("org_id", org_id)\
        .execute()
    
    if not result.data:
        return {"success": True, "data": [], "count": 0}
    
    # Fuzzy matching côté Python (pour compatibilité sans pg_trgm)
    import re
    query_lower = query.lower().strip()
    query_tokens = set(re.findall(r'\w+', query_lower))
    
    scored = []
    for res in result.data:
        nom_lower = (res.get("nom") or "").lower()
        # Score basé sur:
        # 1. Correspondance exacte (1.0)
        # 2. Le query est contenu dans le nom (0.8)
        # 3. Un des tokens du nom correspond au query (0.7)
        # 4. Le query contient un token du nom (0.5)
        
        score = 0.0
        if nom_lower == query_lower:
            score = 1.0
        elif query_lower in nom_lower:
            score = 0.8
        else:
            nom_tokens = set(re.findall(r'\w+', nom_lower))
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
                "confiance": "haute" if score >= 0.8 else "moyenne" if score >= 0.5 else "faible"
            })
    
    # Trier par score décroissant
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "success": True,
        "data": scored[:5],
        "count": len(scored),
        "message": f"{len(scored)} correspondance(s) trouvée(s) pour '{query}'"
    }
```

---

## Tool 2: `upsert_attendance`

**Fichier :** `/opt/projects/suren/saas/surenSaas/surenSaasBack/app/agents/tools/attendance_tools.py` (same file, add after match_resources)

```python
from datetime import date as _date

class UpsertAttendanceSchema(BaseModel):
    org_id: str = Field(description="UUID de l'organisation")
    chantier_id: str = Field(description="UUID ou ref du chantier")
    date_pointage: str = Field(description="Date du pointage (YYYY-MM-DD)")
    ressources: List[dict] = Field(
        description=(
            "Liste des présences : [{\"ressource_id\": \"uuid\", "
            "\"present\": true/false, \"nom\": \"en option pour log\"}]"
        )
    )

@tool("upsert_attendance", args_schema=UpsertAttendanceSchema)
def upsert_attendance(
    org_id: str,
    chantier_id: str,
    date_pointage: str,
    ressources: List[dict],
) -> dict:
    """
    Enregistre ou met à jour les présences pour un pointage à une date donnée.
    Crée le pointage parent si inexistant.
    Upsert les lignes de présence (remplace si existe déjà).
    
    Cette fonction NE vérifie PAS les règles métier (R8-R13).
    Elle persiste ce qu'on lui donne — la validation est faite en amont par le LLM.
    """
    # Vérifier date future
    today = _date.today().isoformat()
    if date_pointage > today:
        return {
            "success": False,
            "data": None,
            "error": f"Date pointage {date_pointage} dans le futur. Impossible.",
            "suggestion": "Utilise une date passée ou aujourd'hui.",
            "message": None
        }
    
    try:
        from uuid import UUID
        uuid = UUID(chantier_id) if chantier_id else None
    except:
        from app.api.chantiers import resolve_chantier_uuid
        uuid = resolve_chantier_uuid(org_id, chantier_id)
    
    sb = get_supabase()
    
    # 1. Créer ou récupérer le pointage parent
    pt_result = sb.table("chantier_pointages")\
        .select("id, statut")\
        .eq("chantier_id", str(uuid))\
        .eq("date", date_pointage)\
        .execute()
    
    if pt_result.data:
        pt_id = pt_result.data[0]["id"]
        # Vérifier que le pointage n'est pas déjà validé
        if pt_result.data[0].get("statut") in ("en_attente_validation", "valide"):
            return {
                "success": False,
                "data": None,
                "error": "Pointage déjà validé. Impossible de modifier.",
                "suggestion": "Contacte le gérant pour modifier un pointage validé.",
                "message": None
            }
    else:
        # Créer le pointage parent
        pt_create = sb.table("chantier_pointages").insert({
            "org_id": org_id,
            "chantier_id": str(uuid),
            "date": date_pointage,
            "statut": "brouillon",
        }).execute()
        pt_id = pt_create.data[0]["id"] if pt_create.data else None
        if not pt_id:
            return {"success": False, "data": None, "error": "Échec création pointage parent", "suggestion": None, "message": None}
    
    # 2. Upsert les lignes de présence
    upserted = []
    for r in ressources:
        res_id = r.get("ressource_id") or r.get("id") or ""
        present = bool(r.get("present", r.get("presence", True)))
        nom = r.get("nom", res_id)
        
        # Vérifier si une ligne existe déjà
        existing = sb.table("chantier_pointage_ressources")\
            .select("id")\
            .eq("pointage_id", pt_id)\
            .eq("ressource_id", res_id)\
            .execute()
        
        line_data = {
            "pointage_id": pt_id,
            "ressource_id": res_id,
            "presence": present,
            "periode": "journee",
        }
        
        if existing.data:
            sb.table("chantier_pointage_ressources")\
                .update(line_data)\
                .eq("id", existing.data[0]["id"])\
                .execute()
        else:
            line_data["org_id"] = org_id
            sb.table("chantier_pointage_ressources")\
                .insert(line_data)\
                .execute()
        
        upserted.append({"ressource_id": res_id, "nom": nom, "present": present})
    
    logger.info("[ATTENDANCE_TOOL] Pointage %s: %d ressources", date_pointage, len(upserted))
    return {
        "success": True,
        "data": {"pointage_id": pt_id, "ressources": upserted},
        "error": None,
        "suggestion": None,
        "message": f"Pointage du {date_pointage} mis à jour : {sum(1 for u in upserted if u['present'])} présent(s), {sum(1 for u in upserted if not u['present'])} absent(s)."
    }
```

---

## Constraints
- Écrire les DEUX tools dans le MÊME fichier `app/agents/tools/attendance_tools.py`
- Utiliser `from app.api.auth import get_supabase` pour le client DB
- Respecter le format `standard_response` (success/data/error/suggestion/message)
- Ne PAS inclure de logique Telegram (pas de send_message)
- Logger avec préfixe `[ATTENDANCE_TOOL]`

## Expected Outcome
- `app/agents/tools/attendance_tools.py` créé avec `match_resources()` et `upsert_attendance()`
- Les 2 tools sont décorés `@tool` avec Pydantic schema → compatibles LangGraph/ToolNode
- `match_resources("Momo")` trouve "Mohammed" si le nom est "Mohammed ..."
- `upsert_attendance(...)` crée le pointage parent si absent, upsert les lignes
