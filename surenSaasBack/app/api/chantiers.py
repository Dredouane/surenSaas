from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.api.auth import get_current_user_from_cookie, get_supabase
from app.core.logging import get_logger
from app.services.tma_auth_service import TmaAuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/chantiers", tags=["chantiers"])

_tma_auth = TmaAuthService()


def check_user_org_access(request: Request, org_id: str):
    """Vérifie l'accès : cookie de session SaaS ou JWT TMA (Authorization Bearer)."""
    # Essayer d'abord le JWT TMA
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.replace("Bearer ", "")
            payload = _tma_auth.verify_jwt(token)
            jwt_org_id = payload.get("org_id", "")
            if jwt_org_id != org_id:
                raise HTTPException(status_code=403, detail="Acces non autorise a cette organisation")
            return payload
        except HTTPException:
            raise
        except Exception:
            pass

    # Fallback : cookie de session SaaS Desktop
    user = get_current_user_from_cookie(request)
    if user["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Acces non autorise a cette organisation")
    return user


def resolve_chantier_uuid(org_id: str, chantier_id: str) -> str:
    """chantier_id may be a UUID or a ref slug. Resolve to actual UUID."""
    import uuid as _uuid
    try:
        _uuid.UUID(chantier_id)
        result = get_supabase().table("chantiers").select("id").eq("id", chantier_id).eq("org_id", org_id).execute()
        if result.data:
            return result.data[0]["id"]
    except ValueError:
        pass
    result = get_supabase().table("chantiers").select("id").eq("ref", chantier_id).eq("org_id", org_id).execute()
    if result.data:
        return result.data[0]["id"]
    raise HTTPException(status_code=404, detail="Chantier non trouve")


# ---------------------------------------------------------------------------
# SCHEMAS PYDANTIC (alignes sur les colonnes SQL 028a_chantiers_tables.sql)
# ---------------------------------------------------------------------------


class ChantierBase(BaseModel):
    ref: str
    nom: str
    adresse: str = ""
    conducteur: str = ""
    commentaires: Optional[str] = None
    montant_base: Optional[float] = 0
    ts_avenants: Optional[float] = 0
    montant_revise: Optional[float] = 0
    situations_facturees: Optional[float] = 0
    pourcentage_facture: Optional[float] = 0
    total_depenses: Optional[float] = 0
    marge_brute: Optional[float] = 0
    solde_a_facturer: Optional[float] = 0
    statut: Optional[str] = "en_cours"
    priorite: Optional[int] = 0
    date_opr_prevue: Optional[str] = None
    date_opr_realisee: Optional[str] = None


class ChantierCreate(ChantierBase):
    pass


class ChantierUpdate(BaseModel):
    nom: Optional[str] = None
    ref: Optional[str] = None
    adresse: Optional[str] = None
    conducteur: Optional[str] = None
    commentaires: Optional[str] = None
    montant_base: Optional[float] = None
    ts_avenants: Optional[float] = None
    montant_revise: Optional[float] = None
    situations_facturees: Optional[float] = None
    pourcentage_facture: Optional[float] = None
    total_depenses: Optional[float] = None
    marge_brute: Optional[float] = None
    solde_a_facturer: Optional[float] = None
    statut: Optional[str] = None
    priorite: Optional[int] = None
    date_opr_prevue: Optional[str] = None
    date_opr_realisee: Optional[str] = None


class ChantierResponse(ChantierBase):
    id: str
    org_id: str
    company_id: Optional[str] = None
    dossier_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class SituationBase(BaseModel):
    date: str
    numero: int
    libelle: str
    montant: float
    reglement_observation: Optional[str] = None
    statut: Optional[str] = None


class SituationCreate(SituationBase):
    pass


class SituationUpdate(BaseModel):
    date: Optional[str] = None
    numero: Optional[int] = None
    libelle: Optional[str] = None
    montant: Optional[float] = None
    reglement_observation: Optional[str] = None


class SituationResponse(SituationBase):
    id: str
    chantier_id: str
    org_id: str
    created_by: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class DepenseBase(BaseModel):
    date: str
    fournisseur: str
    categorie: str = "autre"
    description: Optional[str] = None
    montant: float
    facture_ref: Optional[str] = None
    invoice_id: Optional[str] = None


class DepenseCreate(DepenseBase):
    pass


class DepenseUpdate(BaseModel):
    date: Optional[str] = None
    fournisseur: Optional[str] = None
    categorie: Optional[str] = None
    description: Optional[str] = None
    montant: Optional[float] = None
    facture_ref: Optional[str] = None
    invoice_id: Optional[str] = None
    statut: Optional[str] = None


class DepenseResponse(DepenseBase):
    id: str
    chantier_id: str
    org_id: str
    statut: Optional[str] = "validee"
    valide_par: Optional[str] = None
    valide_le: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class OperationHtlBase(BaseModel):
    description: str
    type: str = "autre"
    date: Optional[str] = None
    source: str = "manuel"
    source_details: Optional[str] = None
    statut: str = "en_attente"
    valide_par: Optional[str] = None
    valide_le: Optional[str] = None
    commentaire: Optional[str] = None
    montant: Optional[float] = None
    unite: Optional[str] = None
    quantite: Optional[float] = None


class OperationHtlCreate(OperationHtlBase):
    pass


class OperationHtlUpdate(BaseModel):
    description: Optional[str] = None
    type: Optional[str] = None
    date: Optional[str] = None
    source: Optional[str] = None
    source_details: Optional[str] = None
    statut: Optional[str] = None
    valide_par: Optional[str] = None
    valide_le: Optional[str] = None
    commentaire: Optional[str] = None
    montant: Optional[float] = None
    unite: Optional[str] = None
    quantite: Optional[float] = None


class OperationHtlResponse(OperationHtlBase):
    id: str
    chantier_id: str
    org_id: str
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ReceptionBase(BaseModel):
    date: str
    type: str
    statut: str = "planifiee"
    participants: Optional[List[str]] = None
    ordre_du_jour: Optional[str] = None
    decisions: Optional[str] = None
    points_a_regler: Optional[str] = None
    documents: Optional[List[str]] = None


class ReceptionCreate(ReceptionBase):
    pass


class ReceptionUpdate(BaseModel):
    date: Optional[str] = None
    type: Optional[str] = None
    statut: Optional[str] = None
    participants: Optional[List[str]] = None
    ordre_du_jour: Optional[str] = None
    decisions: Optional[str] = None
    points_a_regler: Optional[str] = None
    documents: Optional[List[str]] = None


class ReceptionResponse(ReceptionBase):
    id: str
    chantier_id: str
    org_id: str
    created_by: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class TacheBase(BaseModel):
    titre: Optional[str] = ""
    description: Optional[str] = None
    type: str = "action"
    source: str = "direction"
    priorite: str = "moyenne"
    statut: str = "en_attente"
    createur_nom: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_nom: Optional[str] = None
    echeance: Optional[str] = None
    reponse: Optional[str] = None
    documents: Optional[List[str]] = None


class TacheCreate(TacheBase):
    pass


class TacheUpdate(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    source: Optional[str] = None
    priorite: Optional[str] = None
    statut: Optional[str] = None
    createur_nom: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_nom: Optional[str] = None
    echeance: Optional[str] = None
    reponse: Optional[str] = None
    documents: Optional[List[str]] = None


class TacheResponse(TacheBase):
    id: str
    chantier_id: Optional[str] = None
    org_id: str
    reception_id: Optional[str] = None
    createur_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class RessourceBase(BaseModel):
    nom: str
    type: str = "homme"
    specialite: Optional[str] = None
    disponible: Optional[bool] = True
    indisponible_jusquau: Optional[str] = None
    raison_indisponibilite: Optional[str] = None


class RessourceCreate(RessourceBase):
    pass


class RessourceUpdate(BaseModel):
    nom: Optional[str] = None
    type: Optional[str] = None
    specialite: Optional[str] = None
    disponible: Optional[bool] = None
    indisponible_jusquau: Optional[str] = None
    raison_indisponibilite: Optional[str] = None


class RessourceResponse(RessourceBase):
    id: str
    org_id: str
    chantier_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PointageBase(BaseModel):
    date: str
    commentaires: Optional[str] = None
    conducteur_id: Optional[str] = None
    valide_par: Optional[str] = None
    valide_le: Optional[str] = None


class PointageCreate(PointageBase):
    pass


class PointageUpdate(BaseModel):
    date: Optional[str] = None
    commentaires: Optional[str] = None
    conducteur_id: Optional[str] = None
    valide_par: Optional[str] = None
    valide_le: Optional[str] = None


class PointageRessourceDetail(BaseModel):
    ressource_id: str
    nom: str = ""
    type: str = "homme"
    periode: str = "journee"
    heures_prevues: Optional[float] = None


class PointageResponse(PointageBase):
    id: str
    chantier_id: str
    org_id: str
    created_at: str
    updated_at: Optional[str] = None
    ressources: List[PointageRessourceDetail] = []

    class Config:
        from_attributes = True


class PointageRessourceBase(BaseModel):
    ressource_id: str
    periode: str = "journee"
    heures_prevues: Optional[float] = None
    presence: Optional[bool] = True


class PointageRessourceCreate(PointageRessourceBase):
    pass


class PointageRessourceResponse(PointageRessourceBase):
    id: str
    pointage_id: str
    org_id: str
    created_at: str

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    type: str = "info"
    titre: str
    message: Optional[str] = None
    url: Optional[str] = None
    statut: str = "envoyee"
    telegram_message_id: Optional[str] = None


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    statut: Optional[str] = None


class NotificationResponse(NotificationBase):
    id: str
    chantier_id: Optional[str] = None
    org_id: str
    user_id: str
    created_at: str

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------------
# ENDPOINTS CHANTIERS
# ---------------------------------------------------------------------------


@router.get("", response_model=List[ChantierResponse])
async def list_chantiers(
    request: Request,
    org_id: str = Query(...),
    statut: Optional[str] = None,
    priorite: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    try:
        check_user_org_access(request, org_id)
        query = get_supabase().table("chantiers").select("*").eq("org_id", org_id).order("created_at", desc=True)
        if statut:
            query = query.eq("statut", statut)
        if priorite is not None:
            query = query.eq("priorite", priorite)
        if search:
            query = query.or_(f"nom.ilike.%{search}%,ref.ilike.%{search}%,conducteur.ilike.%{search}%")
        result = query.limit(limit).offset(offset).execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste chantiers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ChantierResponse)
async def create_chantier(request: Request, org_id: str = Query(...), chantier: ChantierCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        data = chantier.dict(exclude_none=True)
        data["org_id"] = org_id
        data["created_by"] = user["sub"]
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantiers").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation chantier")
        logger.info(f"Chantier cree: {result.data[0]['id']} par {user['email']}")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation chantier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chantier_id}", response_model=ChantierResponse)
async def get_chantier(request: Request, org_id: str = Query(...), chantier_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        result = get_supabase().table("chantiers").select("*").eq("id", chantier_uuid).eq("org_id", org_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Chantier non trouve")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recuperation chantier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}", response_model=ChantierResponse)
async def update_chantier(request: Request, org_id: str = Query(...), chantier_id: str = None, chantier: ChantierUpdate = None):
    try:
        user = check_user_org_access(request, org_id)
        actual_id = resolve_chantier_uuid(org_id, chantier_id)
        update_data = chantier.dict(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantiers").update(update_data).eq("id", actual_id).execute()
        logger.info(f"Chantier mis a jour: {actual_id} par {user['email']}")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour chantier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}")
async def delete_chantier(request: Request, org_id: str = Query(...), chantier_id: str = None):
    try:
        user = check_user_org_access(request, org_id)
        actual_id = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantiers").delete().eq("id", actual_id).execute()
        logger.info(f"Chantier supprime: {actual_id} par {user['email']}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression chantier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# ENDPOINTS SITUATIONS
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/situations", response_model=List[SituationResponse])
async def list_situations(request: Request, org_id: str = Query(...), chantier_id: str = None, statut: Optional[str] = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        query = get_supabase().table("chantier_situations").select("*").eq("chantier_id", chantier_uuid)
        if statut:
            query = query.eq("statut", statut)
        query = query.order("numero", desc=True)
        result = query.execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste situations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/situations", response_model=SituationResponse)
async def create_situation(request: Request, org_id: str = Query(...), chantier_id: str = None, situation: SituationCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = situation.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        data["created_by"] = user["sub"]
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_situations").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation situation")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation situation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/situations/{situation_id}", response_model=SituationResponse)
async def update_situation(request: Request, org_id: str = Query(...), chantier_id: str = None, situation_id: str = None, situation: SituationUpdate = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = situation.dict(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_situations").update(update_data).eq("id", situation_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Situation non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour situation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/situations/{situation_id}")
async def delete_situation(request: Request, org_id: str = Query(...), chantier_id: str = None, situation_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_situations").delete().eq("id", situation_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression situation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/situations/{situation_id}/statut", response_model=Dict[str, Any])
async def update_situation_statut(request: Request, org_id: str = Query(...), chantier_id: str = None, situation_id: str = None, statut: str = Query(...)):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        result = get_supabase().table("chantier_situations").update({"statut": statut, "updated_at": datetime.utcnow().isoformat()}).eq("id", situation_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Situation non trouvee")
        return {"success": True, "statut": statut}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour statut situation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chantier_id}/situations/{situation_id}/lignes", response_model=List[Dict[str, Any]])
async def list_situation_lignes(request: Request, org_id: str = Query(...), chantier_id: str = None, situation_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        result = get_supabase().table("chantier_situation_lignes").select("*").eq("situation_id", situation_id).order("created_at", desc=False).execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste lignes situation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/situations/{situation_id}/lignes", response_model=Dict[str, Any])
async def create_situation_ligne(request: Request, org_id: str = Query(...), chantier_id: str = None, situation_id: str = None, ligne: Dict[str, Any] = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = ligne.dict() if hasattr(ligne, 'dict') else ligne
        data["situation_id"] = situation_id
        data["org_id"] = org_id
        data["created_by"] = user["sub"]
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_situation_lignes").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation ligne")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation ligne situation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/situations/{situation_id}/lignes/{ligne_id}/approuver", response_model=Dict[str, Any])
async def approuver_situation_ligne(request: Request, org_id: str = Query(...), chantier_id: str = None, situation_id: str = None, ligne_id: str = None, approuver: bool = Query(True), avancement: Optional[float] = Query(None)):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = {"approuvee": approuver, "approuvee_par": user["sub"], "approuvee_le": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat()}
        if avancement is not None:
            update_data["avancement_pourcentage"] = avancement
        result = get_supabase().table("chantier_situation_lignes").update(update_data).eq("id", ligne_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Ligne non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur approbation ligne: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# ENDPOINTS DEPENSES
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/depenses", response_model=List[DepenseResponse])
async def list_depenses(request: Request, org_id: str = Query(...), chantier_id: str = None, categorie: Optional[str] = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        query = get_supabase().table("chantier_depenses").select("*").eq("chantier_id", chantier_uuid).order("date", desc=True)
        if categorie:
            query = query.eq("categorie", categorie)
        result = query.execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste depenses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/depenses", response_model=DepenseResponse)
async def create_depense(request: Request, org_id: str = Query(...), chantier_id: str = None, depense: DepenseCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = depense.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        data["created_by"] = user["sub"]
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_depenses").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation depense")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation depense: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/depenses/{depense_id}", response_model=DepenseResponse)
async def update_depense(request: Request, org_id: str = Query(...), chantier_id: str = None, depense_id: str = None, depense: DepenseUpdate = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = depense.dict(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_depenses").update(update_data).eq("id", depense_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Depense non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour depense: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/depenses/{depense_id}")
async def delete_depense(request: Request, org_id: str = Query(...), chantier_id: str = None, depense_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_depenses").delete().eq("id", depense_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression depense: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# ENDPOINTS OPERATIONS HTL
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/operations", response_model=List[OperationHtlResponse])
async def list_operations(request: Request, org_id: str = Query(...), chantier_id: str = None, statut: Optional[str] = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        query = get_supabase().table("chantier_operations_htl").select("*").eq("chantier_id", chantier_uuid).order("date", desc=True)
        if statut:
            query = query.eq("statut", statut)
        result = query.execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste operations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/operations", response_model=OperationHtlResponse)
async def create_operation(request: Request, org_id: str = Query(...), chantier_id: str = None, operation: OperationHtlCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = operation.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        if "date" not in data or not data["date"]:
            data["date"] = datetime.utcnow().isoformat()
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_operations_htl").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation operation")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/operations/{operation_id}", response_model=OperationHtlResponse)
async def update_operation(request: Request, org_id: str = Query(...), chantier_id: str = None, operation_id: str = None, operation: OperationHtlUpdate = None):
    try:
        user = check_user_org_access(request, org_id)
        # Nettoyage automatique des champs invalides pour PostgREST
        update_data = operation.dict(exclude_none=True)
        
        # Liste des champs qui sont des UUIDs stricts en DB
        uuid_fields = ["valide_par"]
        for field in uuid_fields:
            if field in update_data:
                val = update_data[field]
                # Si la valeur n'est pas un UUID valide, on la supprime de l'update
                import uuid
                try:
                    uuid.UUID(str(val))
                except (ValueError, TypeError, AttributeError):
                    del update_data[field]
                    logger.warning(f"Champ {field} ignoré car invalide (non-UUID): {val}")
             
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = get_supabase().table("chantier_operations_htl").update(update_data).eq("id", operation_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Operation non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/operations/{operation_id}")
async def delete_operation(request: Request, org_id: str = Query(...), chantier_id: str = None, operation_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_operations_htl").delete().eq("id", operation_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
# ---------------------------------------------------------------------------
# ENDPOINTS RECEPTIONS
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/receptions", response_model=List[ReceptionResponse])
async def list_receptions(request: Request, org_id: str = Query(...), chantier_id: str = None, statut: Optional[str] = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        query = get_supabase().table("chantier_receptions").select("*").eq("chantier_id", chantier_uuid).order("date", desc=True)
        if statut:
            query = query.eq("statut", statut)
        result = query.execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste receptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/receptions", response_model=ReceptionResponse)
async def create_reception(request: Request, org_id: str = Query(...), chantier_id: str = None, reception: ReceptionCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = reception.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        data["created_by"] = user["sub"]
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_receptions").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation reception")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation reception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/receptions/{reception_id}", response_model=ReceptionResponse)
async def update_reception(request: Request, org_id: str = Query(...), chantier_id: str = None, reception_id: str = None, reception: ReceptionUpdate = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = reception.dict(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_receptions").update(update_data).eq("id", reception_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Reception non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour reception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/receptions/{reception_id}")
async def delete_reception(request: Request, org_id: str = Query(...), chantier_id: str = None, reception_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_receptions").delete().eq("id", reception_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression reception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# ENDPOINTS TACHES
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/taches", response_model=List[TacheResponse])
async def list_taches(request: Request, org_id: str = Query(...), chantier_id: str = None, statut: Optional[str] = None, priorite: Optional[str] = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        query = get_supabase().table("chantier_taches").select("*").eq("chantier_id", chantier_uuid).order("echeance", desc=True)
        if statut:
            query = query.eq("statut", statut)
        if priorite:
            query = query.eq("priorite", priorite)
        result = query.execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste taches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/taches", response_model=TacheResponse)
async def create_tache(request: Request, org_id: str = Query(...), chantier_id: str = None, tache: TacheCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = tache.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        data["createur_id"] = user["sub"]
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_taches").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation tache")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation tache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/taches/{tache_id}", response_model=TacheResponse)
async def update_tache(request: Request, org_id: str = Query(...), chantier_id: str = None, tache_id: str = None, tache: TacheUpdate = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = tache.dict(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_taches").update(update_data).eq("id", tache_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Tache non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour tache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/taches/{tache_id}")
async def delete_tache(request: Request, org_id: str = Query(...), chantier_id: str = None, tache_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_taches").delete().eq("id", tache_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression tache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
# ---------------------------------------------------------------------------
# ENDPOINTS RESSOURCES
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/ressources", response_model=List[RessourceResponse])
async def list_ressources(request: Request, org_id: str = Query(...), chantier_id: str = None, type_ressource: Optional[str] = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        logger.info(f"list_ressources: chantier_uuid={chantier_uuid}, chantier_id_original={chantier_id}")
        from app.api.auth import get_supabase as get_sb
        sb = get_supabase()
        query = sb.table("chantier_ressources").select("*").eq("org_id", org_id).eq("chantier_id", chantier_uuid).order("nom", desc=False)
        if type_ressource:
            query = query.eq("type", type_ressource)
        result = query.execute()
        logger.info(f"list_ressources: {len(result.data or [])} ressources trouvees")
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste ressources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/ressources", response_model=RessourceResponse)
async def create_ressource(request: Request, org_id: str = Query(...), chantier_id: str = None, ressource: RessourceCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = ressource.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_ressources").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation ressource")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation ressource: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/ressources/{ressource_id}", response_model=RessourceResponse)
async def update_ressource(request: Request, org_id: str = Query(...), chantier_id: str = None, ressource_id: str = None, ressource: RessourceUpdate = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = ressource.dict(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_ressources").update(update_data).eq("id", ressource_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Ressource non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour ressource: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/ressources/{ressource_id}")
async def delete_ressource(request: Request, org_id: str = Query(...), chantier_id: str = None, ressource_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_ressources").delete().eq("id", ressource_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression ressource: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# ENDPOINTS POINTAGES
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/pointages", response_model=List[PointageResponse])
async def list_pointages(request: Request, org_id: str = Query(...), chantier_id: str = None):
    try:
        from collections import defaultdict
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)

        pointages_res = get_supabase().table("chantier_pointages").select("*").eq("chantier_id", chantier_uuid).order("date", desc=True).execute()
        pointages = pointages_res.data or []

        if pointages:
            pointage_ids = [p["id"] for p in pointages]
            pr_res = get_supabase().table("chantier_pointage_ressources").select("*").in_("pointage_id", pointage_ids).execute()
            pr_rows = pr_res.data or []

            ressource_ids = list(set(r["ressource_id"] for r in pr_rows))
            if ressource_ids:
                cr_res = get_supabase().table("chantier_ressources").select("id, nom, type").in_("id", ressource_ids).execute()
                cr_lookup = {cr["id"]: cr for cr in (cr_res.data or [])}
            else:
                cr_lookup = {}

            pr_by_pointage = defaultdict(list)
            for r in pr_rows:
                cr = cr_lookup.get(r["ressource_id"], {})
                pr_by_pointage[r["pointage_id"]].append({
                    "ressource_id": r["ressource_id"],
                    "nom": cr.get("nom", ""),
                    "type": cr.get("type", "homme"),
                    "periode": r["periode"],
                    "heures_prevues": r.get("heures_prevues"),
                })

            for p in pointages:
                p["ressources"] = pr_by_pointage.get(p["id"], [])

        return pointages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste pointages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/pointages", response_model=PointageResponse)
async def create_pointage(request: Request, org_id: str = Query(...), chantier_id: str = None, pointage: PointageCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = pointage.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        data["valide_par"] = user["sub"]
        data["valide_le"] = datetime.utcnow().isoformat()
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_pointages").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation pointage")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation pointage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/pointages/{pointage_id}", response_model=PointageResponse)
async def update_pointage(request: Request, org_id: str = Query(...), chantier_id: str = None, pointage_id: str = None, pointage: PointageUpdate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = pointage.dict(exclude_none=True)
        update_data["valide_par"] = user["sub"]
        update_data["valide_le"] = datetime.utcnow().isoformat()
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_pointages").update(update_data).eq("id", pointage_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Pointage non trouve")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour pointage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/pointages/{pointage_id}")
async def delete_pointage(request: Request, org_id: str = Query(...), chantier_id: str = None, pointage_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_pointages").delete().eq("id", pointage_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression pointage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
# ---------------------------------------------------------------------------
# ENDPOINTS POINTAGE RESSOURCES
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/pointages/{pointage_id}/ressources", response_model=List[PointageRessourceResponse])
async def list_pointage_ressources(request: Request, org_id: str = Query(...), chantier_id: str = None, pointage_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        result = get_supabase().table("chantier_pointage_ressources").select("*").eq("pointage_id", pointage_id).execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste ressources pointage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/pointages/{pointage_id}/ressources", response_model=PointageRessourceResponse)
async def create_pointage_ressource(request: Request, org_id: str = Query(...), chantier_id: str = None, pointage_id: str = None, pr: PointageRessourceCreate = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = pr.dict(exclude_none=True)
        data["pointage_id"] = pointage_id
        data["org_id"] = org_id
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_pointage_ressources").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation ressource pointage")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation ressource pointage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# ENDPOINTS NOTIFICATIONS
# ---------------------------------------------------------------------------


@router.get("/{chantier_id}/notifications", response_model=List[NotificationResponse])
async def list_notifications(request: Request, org_id: str = Query(...), chantier_id: str = None, statut: Optional[str] = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        query = get_supabase().table("chantier_notifications").select("*").eq("chantier_id", chantier_uuid).order("created_at", desc=True)
        if statut:
            query = query.eq("statut", statut)
        result = query.execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/notifications", response_model=NotificationResponse)
async def create_notification(request: Request, org_id: str = Query(...), chantier_id: str = None, notification: NotificationCreate = None):
    try:
        user = check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = notification.dict(exclude_none=True)
        data["chantier_id"] = chantier_uuid
        data["org_id"] = org_id
        data["user_id"] = user["sub"]
        data["created_at"] = datetime.utcnow().isoformat()
        result = get_supabase().table("chantier_notifications").insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Erreur creation notification")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur creation notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chantier_id}/notifications/{notification_id}", response_model=NotificationResponse)
async def update_notification(request: Request, org_id: str = Query(...), chantier_id: str = None, notification_id: str = None, notification: NotificationUpdate = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        update_data = notification.dict(exclude_none=True)
        result = get_supabase().table("chantier_notifications").update(update_data).eq("id", notification_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Notification non trouvee")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise a jour notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chantier_id}/recalculer")
async def recalculer_metriques(request: Request, org_id: str = Query(...), chantier_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().rpc("recalculer_metriques_chantier", {"p_chantier_id": chantier_uuid}).execute()
        return {"success": True, "message": "Métriques recalculées"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recalcul métriques: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chantier_id}/notifications/{notification_id}")
async def delete_notification(request: Request, org_id: str = Query(...), chantier_id: str = None, notification_id: str = None):
    try:
        check_user_org_access(request, org_id)
        chantier_uuid = resolve_chantier_uuid(org_id, chantier_id)
        get_supabase().table("chantier_notifications").delete().eq("id", notification_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))