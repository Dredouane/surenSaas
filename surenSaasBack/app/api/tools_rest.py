import json
import tempfile
import os
import uuid as uuid_mod
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime, date

from app.api.auth import get_supabase
from app.api.chantiers import resolve_chantier_uuid
from app.agents.tools.depense_tools import _create_depense_internal
from app.agents.tools.attendance_tools import _upsert_attendance_internal, _match_resources_internal
from app.agents.generic_extractor import create_invoice_extractor
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tools")


def verify_tools_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    expected = settings.tools_api_key if hasattr(settings, 'tools_api_key') and settings.tools_api_key else "tools-api-key-dev"
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=403, detail="Clé API invalide")
    return x_api_key


class DepenseCreateRequest(BaseModel):
    org_id: str
    chantier_id: str
    description: str
    montant: float = 0.0
    fournisseur: str = "Telegram"
    categorie: str = "autre"
    date_depense: Optional[str] = None
    invoice_id: Optional[str] = None


class PointageUpsertRequest(BaseModel):
    org_id: str
    chantier_id: str
    date_pointage: str
    ressources: list[dict]


class PointageMatchRequest(BaseModel):
    org_id: str
    chantier_id: str
    query: str


class OperationCreateRequest(BaseModel):
    org_id: str
    chantier_id: str
    description: str
    type: str = "autre"
    montant: Optional[float] = None
    quantite: Optional[float] = None
    unite: Optional[str] = None


class ChantierSearchRequest(BaseModel):
    org_id: str
    query: str


class ChantierListRequest(BaseModel):
    org_id: str
    statut: Optional[str] = None


class TacheCreateRequest(BaseModel):
    org_id: str
    chantier_id: str
    action: str  # "create" | "complete"
    titre: Optional[str] = None
    description: Optional[str] = None
    assignee_nom: Optional[str] = None
    priorite: str = "moyenne"
    date_echeance: Optional[str] = None
    tache_id: Optional[str] = None


class AvancementCreateRequest(BaseModel):
    org_id: str
    chantier_id: str
    situation_id: str
    description: str
    avancement_pourcentage: float = 0.0
    quantite: Optional[float] = None
    unite: str = "u"
    prix_unitaire: float = 0.0


# ─── Implémentations internes (copiées des @tool pour éviter la dépendance LangChain) ───

def _create_operation_internal(
    org_id: str,
    chantier_id: str,
    description: str,
    op_type: str = "autre",
    montant: Optional[float] = None,
    quantite: Optional[float] = None,
    unite: Optional[str] = None,
) -> dict:
    try:
        uuid = resolve_chantier_uuid(org_id, chantier_id)
        data = {
            "org_id": org_id,
            "chantier_id": uuid,
            "description": description,
            "type": op_type,
            "montant": montant,
            "quantite": quantite,
            "unite": unite,
                "source": "manuel",
            "date": date.today().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
        result = get_supabase().table("chantier_operations_htl").insert(data).execute()
        if result.data:
            return {"success": True, "data": result.data[0], "error": None, "message": "Opération créée"}
        return {"success": False, "data": None, "error": "Échec insertion", "message": None}
    except Exception as e:
        logger.error("[TOOLS_REST] Erreur create_operation: %s", e, exc_info=True)
        return {"success": False, "data": None, "error": str(e), "message": None}


def _search_chantiers_internal(org_id: str, query: str) -> dict:
    try:
        if not org_id:
            return {"success": False, "data": None, "error": "org_id manquant"}
        q = (query or "").strip()
        if len(q) < 2:
            return {"success": False, "data": None, "error": "Requête trop courte (min 2 caractères)"}
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
        return {
            "success": True,
            "data": result.data or [],
            "error": None,
            "message": f"{len(result.data)} chantier(s) trouvé(s) pour '{query}'." if result.data else f"Aucun chantier trouvé pour '{query}'.",
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


def _list_chantiers_internal(org_id: str, statut: Optional[str] = None) -> dict:
    try:
        if not org_id:
            return {"success": False, "data": None, "error": "org_id manquant"}
        query = get_supabase().table("chantiers").select("id, ref, nom, statut").eq("org_id", org_id)
        if statut:
            query = query.eq("statut", statut)
        result = query.execute()
        return {"success": True, "data": result.data or [], "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


# ─── Implémentations internes (suite) ─────────────────────────────

async def _upload_facture_internal(
    org_id: str,
    chantier_id: str,
    file_bytes: bytes,
    filename: str,
) -> dict:
    """OCR + création invoice à partir d'un fichier (PDF ou image)."""
    import uuid as uuid_mod
    tmp_path = None
    try:
        ext = os.path.splitext(filename)[1].lower()
        is_pdf = ext == ".pdf" or file_bytes[:4] == b"%PDF"
        file_type = "pdf" if is_pdf else "image"

        suffix = ".pdf" if is_pdf else os.path.splitext(filename)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        extractor = create_invoice_extractor()
        result = await extractor.extract(tmp_path, file_type=file_type)

        if result.status != "success" or not result.raw_data:
            return {"success": False, "data": None, "error": "L'OCR n'a pas pu extraire les données de cette facture. Vérifie que l'image est lisible.", "besoin_clarification": True}

        extracted = result.raw_data.get("extracted_data", {})
        supplier = extracted.get("supplier", {})
        invoice = extracted.get("invoice", {})
        amounts = extracted.get("amounts", {})
        line_items_raw = extracted.get("line_items", [])

        # Préparer les champs de l'invoice
        supplier_name = (supplier.get("name") or "").strip()
        invoice_number = (invoice.get("number") or "").strip()
        invoice_date = (invoice.get("date") or date.today().isoformat())
        amount_ttc = float(amounts.get("ttc") or 0)
        amount_ht = float(amounts.get("ht") or 0) if amounts.get("ht") else None
        vat_amount = float(amounts.get("vat") or 0) if amounts.get("vat") else None
        vat_rate = float(amounts.get("vat_rate") or 0) if amounts.get("vat_rate") else None
        description = f"Facture {invoice_number}" if invoice_number else f"Facture {supplier_name}"

        # Mapper les line_items
        items_payload = []
        for idx, li in enumerate(line_items_raw or []):
            items_payload.append({
                "id": str(uuid_mod.uuid4()),
                "description": li.get("description", ""),
                "quantity": float(li["quantity"]) if li.get("quantity") else None,
                "unit_price": float(li["unit_price"]) if li.get("unit_price") else None,
                "total_ht": float(li["total_ht"]) if li.get("total_ht") else None,
                "vat_rate": float(li["vat_rate"]) if li.get("vat_rate") else None,
                "sort_order": idx,
            })

        # Créer l'invoice en DB
        sb = get_supabase()
        invoice_id = str(uuid_mod.uuid4())
        now = datetime.utcnow().isoformat()

        # Récupérer company_id pour l'orga
        company_res = sb.table("companies").select("id").eq("slug", "construction").eq("org_id", org_id).execute()
        company_id = company_res.data[0]["id"] if company_res.data else None

        invoice_data = {
            "id": invoice_id,
            "org_id": org_id,
            "company_id": company_id,
            "invoice_number": invoice_number,
            "supplier_name": supplier_name,
            "supplier_address": supplier.get("address"),
            "supplier_siret": supplier.get("siret"),
            "amount_ht": amount_ht,
            "amount_ttc": amount_ttc,
            "vat_amount": vat_amount,
            "vat_rate": vat_rate,
            "invoice_date": invoice_date,
            "due_date": invoice.get("due_date"),
            "description": description,
            "items": items_payload,
            "status": "brouillon",
            "ocr_data": result.raw_data,
            "metadata": {"source": "hermes_api", "original_filename": filename},
            "created_at": now,
            "updated_at": now,
        }

        sb.table("invoices").insert(invoice_data).execute()

        # Créer les invoice_items si présents
        for item in items_payload:
            sb.table("invoice_items").insert({
                "id": item["id"],
                "invoice_id": invoice_id,
                "org_id": org_id,
                "description": item["description"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "total_ht": item["total_ht"],
                "vat_rate": item["vat_rate"],
                "sort_order": item["sort_order"],
                "created_at": now,
                "updated_at": now,
            }).execute()

        logger.info("[TOOLS_REST] Facture créée: %s - %s - %.2f€", invoice_id, supplier_name, amount_ttc)

        return {
            "success": True,
            "data": {
                "invoice_id": invoice_id,
                "supplier_name": supplier_name,
                "amount_ttc": amount_ttc,
                "amount_ht": amount_ht,
                "vat_amount": vat_amount,
                "vat_rate": vat_rate,
                "invoice_date": invoice_date,
                "invoice_number": invoice_number,
                "description": description,
                "line_items": items_payload,
                "chantier_id": chantier_id,
            },
            "error": None,
            "message": f"Facture {supplier_name} - {amount_ttc:.2f}€ extraite et enregistrée (brouillon). Confirme pour créer la dépense.",
            "besoin_clarification": not supplier_name or not amount_ttc,
        }

    except Exception as e:
        logger.error("[TOOLS_REST] Erreur upload-facture: %s", e, exc_info=True)
        return {"success": False, "data": None, "error": str(e), "besoin_clarification": True}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ─── Implémentations internes (suite) ─────────────────────────────

def _manage_taches_internal(
    org_id: str,
    chantier_id: str,
    action: str,
    titre: Optional[str] = None,
    description: Optional[str] = None,
    assignee_nom: Optional[str] = None,
    priorite: str = "moyenne",
    date_echeance: Optional[str] = None,
    tache_id: Optional[str] = None,
) -> dict:
    try:
        uuid = resolve_chantier_uuid(org_id, chantier_id)
        sb = get_supabase()

        if action == "list":
            result = sb.table("chantier_taches").select("*").eq("chantier_id", uuid).execute()
            return {"success": True, "data": result.data or [], "error": None}

        elif action == "create":
            if not titre or len(titre.strip()) < 2:
                return {"success": False, "data": None, "error": "Le titre doit faire au moins 2 caractères"}
            if date_echeance and date_echeance < date.today().isoformat():
                return {"success": False, "data": None, "error": "La date d'échéance ne peut pas être dans le passé (R20)", "suggestion": "Choisis une date future ou aujourd'hui"}
            data = {
                "org_id": org_id,
                "chantier_id": uuid,
                "titre": titre.strip(),
                "description": description or "",
                "priorite": priorite,
                "statut": "en_attente",
                "type": "action",
                "source": "direction",
                "created_at": datetime.utcnow().isoformat(),
            }
            if assignee_nom:
                data["assignee_nom"] = assignee_nom
            if date_echeance:
                data["echeance"] = date_echeance
            result = sb.table("chantier_taches").insert(data).execute()
            if result.data:
                return {"success": True, "data": result.data[0], "error": None, "message": f"Tâche '{titre}' créée"}
            return {"success": False, "data": None, "error": "Échec insertion"}

        elif action == "complete":
            if not tache_id:
                return {"success": False, "data": None, "error": "tache_id requis pour action=complete"}
            result = sb.table("chantier_taches").select("statut").eq("id", tache_id).eq("chantier_id", uuid).execute()
            if not result.data:
                return {"success": False, "data": None, "error": "Tâche non trouvée"}
            if result.data[0].get("statut") == "terminee":
                return {"success": False, "data": None, "error": "Tâche déjà terminée, impossible de la repasser en cours (R21)"}
            sb.table("chantier_taches").update({"statut": "terminee", "updated_at": datetime.utcnow().isoformat()}).eq("id", tache_id).execute()
            return {"success": True, "data": {"id": tache_id}, "error": None, "message": "Tâche marquée comme terminée"}

        else:
            return {"success": False, "data": None, "error": f"Action inconnue: {action}"}

    except Exception as e:
        logger.error("[TOOLS_REST] Erreur taches: %s", e, exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


def _create_avancement_internal(
    org_id: str,
    chantier_id: str,
    situation_id: str,
    description: str,
    avancement_pourcentage: float = 0.0,
    quantite: Optional[float] = None,
    unite: str = "u",
    prix_unitaire: float = 0.0,
) -> dict:
    try:
        # R23 : pourcentage 0-100
        if avancement_pourcentage < 0 or avancement_pourcentage > 100:
            return {"success": False, "data": None, "error": "Le pourcentage doit être entre 0 et 100 (R23)"}

        uuid = resolve_chantier_uuid(org_id, chantier_id)
        sb = get_supabase()

        # R25 : vérifier que la situation existe et est ouverte
        sit = sb.table("chantier_situations").select("id, statut").eq("id", situation_id).eq("chantier_id", uuid).execute()
        if not sit.data:
            return {"success": False, "data": None, "error": "Situation non trouvée"}
        if sit.data[0].get("statut") != "ouverte":
            return {"success": False, "data": None, "error": "La situation doit être ouverte pour accepter des lignes d'avancement (R25)"}

        data = {
            "org_id": org_id,
            "situation_id": situation_id,
            "description": description,
            "quantite": quantite or 1,
            "unite": unite,
            "prix_unitaire": prix_unitaire,
            "avancement_pourcentage": avancement_pourcentage,
            "montant_total": (quantite or 1) * prix_unitaire,
            "remise": 0,
            "facturee": False,
            "approuvee": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        result = sb.table("chantier_situation_lignes").insert(data).execute()
        if result.data:
            return {"success": True, "data": result.data[0], "error": None, "message": f"Avancement ajouté: {avancement_pourcentage}%"}
        return {"success": False, "data": None, "error": "Échec insertion avancement"}

    except Exception as e:
        logger.error("[TOOLS_REST] Erreur avancement: %s", e, exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


# ─── Helpers lecture CRUD ─────────────────────────────────────────

def _check_org_id(org_id: str) -> None:
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id requis")


# ─── Endpoints REST ───────────────────────────────────────────────

@router.post("/depenses", dependencies=[Depends(verify_tools_api_key)])
async def create_depense(req: DepenseCreateRequest):
    return _create_depense_internal(
        org_id=req.org_id,
        chantier_id=req.chantier_id,
        description=req.description,
        montant=req.montant,
        fournisseur=req.fournisseur,
        categorie=req.categorie,
        date_depense=req.date_depense,
        invoice_id=req.invoice_id,
    )


@router.post("/pointages/upsert", dependencies=[Depends(verify_tools_api_key)])
async def upsert_pointage(req: PointageUpsertRequest):
    return _upsert_attendance_internal(
        org_id=req.org_id,
        chantier_id=req.chantier_id,
        date_pointage=req.date_pointage,
        ressources=req.ressources,
    )


@router.post("/pointages/match", dependencies=[Depends(verify_tools_api_key)])
async def match_ressources(req: PointageMatchRequest):
    return _match_resources_internal(
        org_id=req.org_id,
        chantier_id=req.chantier_id,
        query=req.query,
    )


@router.post("/operations", dependencies=[Depends(verify_tools_api_key)])
async def create_operation(req: OperationCreateRequest):
    return _create_operation_internal(
        org_id=req.org_id,
        chantier_id=req.chantier_id,
        description=req.description,
        op_type=req.type,
        montant=req.montant,
        quantite=req.quantite,
        unite=req.unite,
    )


@router.post("/chantiers/search", dependencies=[Depends(verify_tools_api_key)])
async def search_chantiers(req: ChantierSearchRequest):
    return _search_chantiers_internal(org_id=req.org_id, query=req.query)


@router.post("/chantiers/list", dependencies=[Depends(verify_tools_api_key)])
async def list_chantiers(req: ChantierListRequest):
    return _list_chantiers_internal(org_id=req.org_id, statut=req.statut)


@router.post("/taches", dependencies=[Depends(verify_tools_api_key)])
async def manage_taches(req: TacheCreateRequest):
    return _manage_taches_internal(
        org_id=req.org_id,
        chantier_id=req.chantier_id,
        action=req.action,
        titre=req.titre,
        description=req.description,
        assignee_nom=req.assignee_nom,
        priorite=req.priorite,
        date_echeance=req.date_echeance,
        tache_id=req.tache_id,
    )


@router.post("/upload-facture", dependencies=[Depends(verify_tools_api_key)])
async def upload_facture(
    file: UploadFile = File(...),
    org_id: str = Form(...),
    chantier_id: str = Form(...),
):
    return await _upload_facture_internal(
        org_id=org_id,
        chantier_id=chantier_id,
        file_bytes=await file.read(),
        filename=file.filename or "inconnu",
    )


@router.post("/avancements", dependencies=[Depends(verify_tools_api_key)])
async def create_avancement(req: AvancementCreateRequest):
    return _create_avancement_internal(
        org_id=req.org_id,
        chantier_id=req.chantier_id,
        situation_id=req.situation_id,
        description=req.description,
        avancement_pourcentage=req.avancement_pourcentage,
        quantite=req.quantite,
        unite=req.unite,
        prix_unitaire=req.prix_unitaire,
    )


# ─── Endpoints CRUD lecture (délèguent aux routes existantes de chantiers.py via Supabase direct) ─

@router.get("/chantiers/{chantier_id}/depenses", dependencies=[Depends(verify_tools_api_key)])
async def list_depenses(chantier_id: str, org_id: str = Query(...)):
    _check_org_id(org_id)
    uuid = resolve_chantier_uuid(org_id, chantier_id)
    sb = get_supabase()
    result = sb.table("chantier_depenses").select("*").eq("chantier_id", uuid).order("date", desc=True).execute()
    depenses = result.data or []
    invoice_ids = [d.get("invoice_id") for d in depenses if d.get("invoice_id")]
    if invoice_ids:
        inv_ids = [i for i in invoice_ids if i]
        if inv_ids:
            items = sb.table("invoice_items").select("*").in_("invoice_id", inv_ids).execute()
            items_by_invoice = {}
            for item in (items.data or []):
                inv_id = item.get("invoice_id")
                if inv_id not in items_by_invoice:
                    items_by_invoice[inv_id] = []
                items_by_invoice[inv_id].append(item)
            for d in depenses:
                inv_id = d.get("invoice_id")
                if inv_id and inv_id in items_by_invoice:
                    d["invoice_items"] = items_by_invoice[inv_id]
    return {"success": True, "data": depenses}


@router.get("/chantiers/{chantier_id}/operations", dependencies=[Depends(verify_tools_api_key)])
async def list_operations(chantier_id: str, org_id: str = Query(...), statut: Optional[str] = Query(None)):
    _check_org_id(org_id)
    uuid = resolve_chantier_uuid(org_id, chantier_id)
    query = get_supabase().table("chantier_operations_htl").select("*").eq("chantier_id", uuid)
    if statut:
        query = query.eq("statut", statut)
    result = query.order("date", desc=True).execute()
    return {"success": True, "data": result.data or []}


@router.get("/chantiers/{chantier_id}/pointages", dependencies=[Depends(verify_tools_api_key)])
async def list_pointages(chantier_id: str, org_id: str = Query(...)):
    from collections import defaultdict
    _check_org_id(org_id)
    uuid = resolve_chantier_uuid(org_id, chantier_id)
    sb = get_supabase()
    pointages_res = sb.table("chantier_pointages").select("*").eq("chantier_id", uuid).order("date", desc=True).execute()
    pointages = pointages_res.data or []
    if pointages:
        pointage_ids = [p["id"] for p in pointages]
        pr_res = sb.table("chantier_pointage_ressources").select("*").in_("pointage_id", pointage_ids).execute()
        pr_rows = pr_res.data or []
        ressource_ids = list(set(r["ressource_id"] for r in pr_rows))
        cr_lookup = {}
        if ressource_ids:
            cr_res = sb.table("chantier_ressources").select("id, nom, type").in_("id", ressource_ids).execute()
            cr_lookup = {cr["id"]: cr for cr in (cr_res.data or [])}
        pr_by_pointage = defaultdict(list)
        for r in pr_rows:
            cr = cr_lookup.get(r["ressource_id"], {})
            meta = r.get("metadata", {})
            meta_nom = ""
            if isinstance(meta, dict):
                meta_nom = meta.get("nom", "")
            nom = meta_nom or cr.get("nom", "")
            pr_by_pointage[r["pointage_id"]].append({
                "ressource_id": r["ressource_id"],
                "nom": nom,
                "type": cr.get("type", "homme"),
                "periode": r["periode"],
                "heures_prevues": r.get("heures_prevues"),
            })
        for p in pointages:
            p["ressources"] = pr_by_pointage.get(p["id"], [])
    return {"success": True, "data": pointages}


@router.get("/chantiers/{chantier_id}/taches", dependencies=[Depends(verify_tools_api_key)])
async def list_taches(chantier_id: str, org_id: str = Query(...), statut: Optional[str] = Query(None)):
    _check_org_id(org_id)
    uuid = resolve_chantier_uuid(org_id, chantier_id)
    query = get_supabase().table("chantier_taches").select("*").eq("chantier_id", uuid)
    if statut:
        query = query.eq("statut", statut)
    result = query.order("echeance", desc=True).execute()
    return {"success": True, "data": result.data or []}


@router.get("/chantiers/{chantier_id}/ressources", dependencies=[Depends(verify_tools_api_key)])
async def list_ressources(chantier_id: str, org_id: str = Query(...), type_ressource: Optional[str] = Query(None)):
    _check_org_id(org_id)
    uuid = resolve_chantier_uuid(org_id, chantier_id)
    sb = get_supabase()
    q = sb.table("chantier_ressources").select("*").eq("org_id", org_id).eq("chantier_id", uuid)
    if type_ressource:
        q = q.eq("type", type_ressource)
    result = q.order("nom", desc=False).execute()
    ressources = result.data or []
    if not ressources:
        q2 = sb.table("chantier_ressources").select("*").eq("org_id", org_id)
        if type_ressource:
            q2 = q2.eq("type", type_ressource)
        r2 = q2.order("nom", desc=False).execute()
        ressources = r2.data or []
    return {"success": True, "data": ressources}


@router.get("/chantiers/{chantier_id}/situations", dependencies=[Depends(verify_tools_api_key)])
async def list_situations(chantier_id: str, org_id: str = Query(...)):
    _check_org_id(org_id)
    uuid = resolve_chantier_uuid(org_id, chantier_id)
    result = get_supabase().table("chantier_situations").select("*").eq("chantier_id", uuid).order("numero", desc=True).execute()
    return {"success": True, "data": result.data or []}


# ============================================================================
# Endpoints Hermès : Recherche chantier + Budget
# ============================================================================


@router.post("/chantiers/search")
async def search_chantiers(
    query: str = Query(...),
    org_id: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Recherche sémantique de chantiers par texte (keyword + vector).

    Hermès envoie un texte (sujet + corps d'email) et récupère les chantiers
    les plus pertinents. Deux passes : keyword SQL puis RAG vectoriel.
    """
    verify_tools_api_key(x_api_key)

    sb = get_supabase()

    # 1. Passe keyword : ILIKE sur nom / ref
    keyword_results = sb.table("chantiers")\
        .select("id, nom, ref, adresse, statut")\
        .eq("org_id", org_id)\
        .in_("statut", ["en_cours", "en_attente"])\
        .or_(f"nom.ilike.%{query}%,ref.ilike.%{query}%")\
        .limit(limit)\
        .execute()

    seen = set()
    merged = []

    for c in (keyword_results.data or []):
        seen.add(c["id"])
        merged.append({
            "chantier_id": c["id"],
            "nom": c.get("nom"),
            "ref": c.get("ref"),
            "adresse": c.get("adresse"),
            "method": "keyword",
            "score": 1.0,
        })

    # 2. Passe vectorielle : RPC match_chantiers
    try:
        from app.services.emails.embedding_service import embedding_service
        import asyncio

        vector = await embedding_service.generate_embedding(query)
        loop = asyncio.get_event_loop()

        def _rpc():
            return sb.rpc("match_chantiers", {
                "query_embedding": vector,
                "org_id_filter": org_id,
                "match_threshold": 0.65,
                "match_count": limit,
            }).execute()

        vector_results = await loop.run_in_executor(None, _rpc)

        for c in (vector_results.data or []):
            cid = str(c["chantier_id"])
            if cid not in seen:
                seen.add(cid)
                merged.append({
                    "chantier_id": cid,
                    "nom": c.get("content", ""),
                    "ref": None,
                    "adresse": None,
                    "method": "vector",
                    "score": round(c.get("similarity", 0), 4),
                })
    except Exception as e:
        logger.warning(f"[search_chantiers] Passe vectorielle ignorée: {e}")

    return {"success": True, "count": len(merged[:limit]), "data": merged[:limit]}


@router.get("/chantiers/{chantier_id}/budget")
async def get_chantier_budget(
    chantier_id: str,
    org_id: str = Query(...),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Retourne l'enveloppe financière complète d'un chantier.

    Hermès utilise ces infos pour vérifier les montants disponibles
    avant de créer une dépense.
    """
    verify_tools_api_key(x_api_key)

    sb = get_supabase()
    uuid = resolve_chantier_uuid(org_id, chantier_id)

    c_resp = sb.table("chantiers").select(
        "id, ref, nom, montant_base, ts_avenants, montant_revise, "
        "situations_facturees, total_depenses, marge_brute"
    ).eq("id", uuid).single().execute()

    if not c_resp.data:
        raise HTTPException(status_code=404, detail="Chantier non trouvé")

    chantier = c_resp.data

    # Dépenses validées
    dep_resp = sb.table("chantier_depenses")\
        .select("montant")\
        .eq("chantier_id", uuid)\
        .execute()

    total_depenses = sum(d.get("montant", 0) or 0 for d in (dep_resp.data or []))
    montant_base = chantier.get("montant_base", 0) or 0
    montant_revise = chantier.get("montant_revise", 0) or 0
    ts_avenants = chantier.get("ts_avenants", 0) or 0
    situations_facturees = chantier.get("situations_facturees", 0) or 0
    marge_brute = chantier.get("marge_brute", 0) or 0

    budget_total = montant_revise or montant_base
    budget_disponible = budget_total - total_depenses

    return {
        "success": True,
        "data": {
            "chantier_id": chantier["id"],
            "ref": chantier.get("ref"),
            "nom": chantier.get("nom"),
            "montant_base": montant_base,
            "ts_avenants": ts_avenants,
            "montant_revise": montant_revise,
            "budget_total": budget_total,
            "total_depenses_engagees": total_depenses,
            "budget_disponible": budget_disponible,
            "situations_facturees": situations_facturees,
            "marge_brute": marge_brute,
        },
    }
