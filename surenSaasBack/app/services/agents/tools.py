
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.api.auth import get_supabase
from app.api.chantiers import resolve_chantier_uuid

# --- SCHEMAS DES ARGUMENTS ---

class GetChantiersSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    statut: Optional[str] = Field(None, description="Filtrer par statut (en_cours, termine, en_attente, cloture)")

class GetChantierDetailsSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    chantier_id: str = Field(description="L'ID ou la référence du chantier")

class CreateDepenseSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    chantier_id: str = Field(description="L'ID ou la référence du chantier")
    fournisseur: str = Field(description="Nom du fournisseur")
    montant: float = Field(description="Montant de la dépense")
    categorie: str = Field("autre", description="Catégorie (sous_traitant, fournisseur, autre)")
    description: Optional[str] = Field(None, description="Description de la dépense")
    date: Optional[str] = Field(None, description="Date de la dépense (YYYY-MM-DD)")

class CreateOperationSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    chantier_id: str = Field(description="L'ID ou la référence du chantier")
    description: str = Field(description="Description de l'opération")
    type: str = Field("autre", description="Type d'opération (demolition, nettoyage, pose_bso, commande, achat_materiel, sous_traitance, autre)")
    montant: Optional[float] = Field(None, description="Montant estimé ou réel")
    quantite: Optional[float] = Field(None, description="Quantité")
    unite: Optional[str] = Field(None, description="Unité de mesure")

class ManageAttendanceSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    chantier_id: str = Field(description="L'ID ou la référence du chantier")
    date: str = Field(description="Date du pointage (YYYY-MM-DD)")
    ressources: List[Dict[str, Any]] = Field(description="Liste des pointages : [{'ressource_id': str, 'presence': bool, 'heures': float}]")

class ReportProgressSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    chantier_id: str = Field(description="L'ID ou la référence du chantier")
    situation_id: str = Field(description="ID de la situation de facturation")
    description: str = Field(description="Description de l'avancement")
    avancement_pourcentage: float = Field(description="Pourcentage d'avancement (0-100)")
    quantite: Optional[float] = Field(None, description="Quantité réalisée")
    unite: str = Field("u", description="Unité")
    prix_unitaire: float = Field(0.0, description="Prix unitaire")

class ManageTasksSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    chantier_id: str = Field(description="L'ID ou la référence du chantier")
    action: str = Field(description="Action à effectuer : 'list', 'create', 'complete'")
    tache_id: Optional[str] = Field(None, description="ID de la tâche (pour complete)")
    titre: Optional[str] = Field(None, description="Titre de la tâche")
    description: Optional[str] = Field(None, description="Description")
    priorite: str = Field("moyenne", description="basse, moyenne, haute")

# --- HELPER DE RÉPONSE STANDARDISÉE ---

def standard_response(success: bool, data: Any = None, error: str = None, suggestion: str = None, message: str = None) -> Dict[str, Any]:
    return {
        "success": success,
        "data": data,
        "error": error,
        "suggestion": suggestion,
        "message": message
    }

# --- TOOLS ---

@tool("get_user_chantiers", args_schema=GetChantiersSchema)
def get_user_chantiers(org_id: str, statut: Optional[str] = None, context_summary: str = "") -> Dict[str, Any]:
    """Récupère la liste des chantiers accessibles pour une organisation."""
    try:
        if not org_id:
            return standard_response(False, error="org_id manquant", suggestion="Veuillez sélectionner une organisation.")
        query = get_supabase().table("chantiers").select("id, ref, nom, statut").eq("org_id", org_id)
        if statut:
            query = query.eq("statut", statut)
        result = query.execute()
        if not result.data:
            return standard_response(True, [], suggestion="Aucun chantier trouvé pour ces critères.")
        return standard_response(True, result.data)
    except Exception as e:
        return standard_response(False, error=str(e))

@tool("get_chantier_details", args_schema=GetChantierDetailsSchema)
def get_chantier_details(org_id: str, chantier_id: str, context_summary: str = "") -> Dict[str, Any]:
    """Récupère les détails financiers complets d'un chantier spécifique."""
    try:
        uuid = resolve_chantier_uuid(org_id, chantier_id)
        result = get_supabase().table("chantiers").select("*").eq("id", uuid).single().execute()
        if not result.data:
            return standard_response(False, error="Chantier non trouvé")
        return standard_response(True, result.data)
    except Exception as e:
        return standard_response(False, error=str(e))

@tool("create_operation", args_schema=CreateOperationSchema)
def create_operation(
    org_id: str,
    chantier_id: str,
    description: str,
    type: str = "autre",
    montant: Optional[float] = None,
    quantite: Optional[float] = None,
    unite: Optional[str] = None,
    context_summary: str = ""
) -> Dict[str, Any]:
    """Enregistre une opération terrain (HTL) pour un chantier."""
    try:
        uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = {
            "org_id": org_id,
            "chantier_id": uuid,
            "description": description,
            "type": type,
            "montant": montant,
            "quantite": quantite,
            "unite": unite,
            "source": "telegram_text",
            "date": datetime.utcnow().date().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        result = get_supabase().table("chantier_operations_htl").insert(data).execute()
        return standard_response(True, result.data[0]) if result.data else standard_response(False, error="Échec insertion")
    except Exception as e:
        return standard_response(False, error=str(e))

@tool("manage_attendance", args_schema=ManageAttendanceSchema)
def manage_attendance(org_id: str, chantier_id: str, date: str, ressources: List[Dict[str, Any]], context_summary: str = "") -> Dict[str, Any]:
    """Gère les pointages de présence pour un chantier à une date donnée."""
    try:
        uuid = resolve_chantier_uuid(org_id, chantier_id)
        # 1. Créer ou récupérer le pointage parent
        pt_res = get_supabase().table("chantier_pointages").select("id").eq("chantier_id", uuid).eq("date", date).execute()
        if pt_res.data:
            pt_id = pt_res.data[0]["id"]
        else:
            pt_create = get_supabase().table("chantier_pointages").insert({
                "org_id": org_id,
                "chantier_id": uuid,
                "date": date,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            pt_id = pt_create.data[0]["id"]

        # 2. Insérer les lignes
        import logging as _logging
        _log = _logging.getLogger(__name__)
        for r in ressources:
            if not isinstance(r, dict):
                _log.warning(f"manage_attendance: ressource ignorée (pas un dict): {r}")
                continue
            _log.debug(f"manage_attendance ressource: {r}")
            ressource_id = r.get("ressource_id") or r.get("name") or r.get("id") or r.get("nom") or ""
            get_supabase().table("chantier_pointage_ressources").insert({
                "org_id": org_id,
                "pointage_id": pt_id,
                "ressource_id": ressource_id,
                "presence": r.get("presence", True),
                "heures_prevues": r.get("heures") or r.get("heures_prevues") or r.get("hours"),
                "periode": r.get("periode", "journee")
            }).execute()
            
        return standard_response(True, {"pointage_id": pt_id}, message=f"Pointage enregistré pour le {date}")
    except Exception as e:
        return standard_response(False, error=str(e))

@tool("report_progress", args_schema=ReportProgressSchema)
def report_progress(
    org_id: str, 
    chantier_id: str, 
    situation_id: str, 
    description: str, 
    avancement_pourcentage: float,
    quantite: Optional[float] = None,
    unite: str = "u",
    prix_unitaire: float = 0.0,
    context_summary: str = ""
) -> Dict[str, Any]:
    """Ajoute un avancement de travaux sur une ligne de situation."""
    try:
        uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = {
            "org_id": org_id,
            "situation_id": situation_id,
            "description": description,
            "quantite": quantite or 1,
            "unite": unite,
            "prix_unitaire": prix_unitaire,
            "avancement_pourcentage": avancement_pourcentage,
            "montant_total": (quantite or 1) * prix_unitaire,
            "created_at": datetime.utcnow().isoformat()
        }
        result = get_supabase().table("chantier_situation_lignes").insert(data).execute()
        return standard_response(True, result.data[0]) if result.data else standard_response(False, error="Échec insertion")
    except Exception as e:
        return standard_response(False, error=str(e))

@tool("manage_tasks", args_schema=ManageTasksSchema)
def manage_tasks(
    org_id: str,
    chantier_id: str,
    action: str,
    tache_id: Optional[str] = None,
    titre: Optional[str] = None,
    description: Optional[str] = None,
    priorite: str = "moyenne",
    context_summary: str = ""
) -> Dict[str, Any]:
    """Gère les tâches du chantier (lister, créer, terminer)."""
    try:
        uuid = resolve_chantier_uuid(org_id, chantier_id)
        sb = get_supabase()
        if action == "list":
            res = sb.table("chantier_taches").select("*").eq("chantier_id", uuid).execute()
            return standard_response(True, res.data)
        elif action == "create":
            res = sb.table("chantier_taches").insert({
                "org_id": org_id,
                "chantier_id": uuid,
                "titre": titre,
                "description": description,
                "priorite": priorite,
                "statut": "en_attente",
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            return standard_response(True, res.data[0])
        elif action == "complete":
            res = sb.table("chantier_taches").update({"statut": "terminee"}).eq("id", tache_id).execute()
            return standard_response(True, res.data[0])
        return standard_response(False, error="Action inconnue")
    except Exception as e:
        return standard_response(False, error=str(e))


# ─── SEARCH CHANTIER ─────────────────────────────────────────────

class SearchChantierSchema(BaseModel):
    org_id: str = Field(description="L'ID de l'organisation (UUID)")
    query: str = Field(description="Recherche par référence (ref) ou nom du chantier")


@tool("search_chantiers", args_schema=SearchChantierSchema)
def search_chantiers(org_id: str, query: str, context_summary: str = "") -> Dict[str, Any]:
    """Cherche un chantier par référence (ref) ou nom avec ILIKE.
    Usage : quand l'utilisateur donne un nom ou ref de chantier (ex: 'CRF', 'CH-016', 'Bureaux').
    Retourne les chantiers correspondants, maximum 5 résultats.
    """
    try:
        if not org_id:
            return standard_response(False, error="org_id manquant")
        q = (query or "").strip()
        if len(q) < 2:
            return standard_response(False, error="Requête trop courte (min 2 caractères)")
        # Normaliser les tirets : CH-016 ou CH016 doivent matcher CH-016
        search_q = q.replace("-", "%")

        result = (
            get_supabase()
            .table("chantiers")
            .select("id, ref, nom, statut")
            .eq("org_id", org_id)
            .or_(f"ref.ilike.%{search_q}%,nom.ilike.%{search_q}%")
            .limit(5)
            .execute()
        )
        if not result.data:
            return standard_response(True, [], message=f"Aucun chantier trouvé pour '{query}'.")
        
        return standard_response(
            True, result.data,
            message=f"{len(result.data)} chantier(s) trouvé(s) pour '{query}'."
        )
    except Exception as e:
        return standard_response(False, error=str(e))
