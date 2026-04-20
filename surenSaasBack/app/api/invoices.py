from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.api.auth import get_current_user_from_cookie, get_supabase, AuthenticationError, clear_session_cookie
from app.core.logging import get_logger
from app.services.file_storage_service import file_storage_service
from fastapi.responses import RedirectResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/invoices", tags=["invoices"])

# Schémas Pydantic - Alignés avec la structure de la table existante (migration 008)
class InvoiceItem(BaseModel):
    """Ligne de détail d'une facture"""
    id: Optional[str] = None
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_ht: Optional[float] = None
    vat_rate: Optional[float] = None
    sort_order: Optional[int] = 0

class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    supplier_name: str
    amount_ttc: float
    amount_ht: Optional[float] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    status: str = "brouillon"
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[str] = None
    company_id: Optional[str] = None  # Pour compatibilité avec la structure existante

class InvoiceCreate(BaseModel):
    invoice_number: Optional[str] = None
    supplier_name: str
    amount_ttc: float
    amount_ht: Optional[float] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[str] = None
    company_id: Optional[str] = None
    items: Optional[List[InvoiceItem]] = None  # Nouveau: lignes de détail

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    supplier_name: Optional[str] = None
    amount_ttc: Optional[float] = None
    amount_ht: Optional[float] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[str] = None
    items: Optional[List[InvoiceItem]] = None  # Nouveau: lignes de détail

class InvoiceResponse(InvoiceBase):
    id: str
    org_id: str
    created_by: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    validated_by: Optional[str] = None
    validated_at: Optional[str] = None
    original_file_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    items: Optional[List[InvoiceItem]] = None  # Nouveau: lignes de détail

    class Config:
        from_attributes = True

def check_user_org_access(request: Request, org_id: str):
    """Vérifie que l'utilisateur a accès à cette organisation."""
    try:
        user = get_current_user_from_cookie(request)
        if user["org_id"] != org_id:
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette organisation")
        return user
    except AuthenticationError as e:
        # Ajouter un header pour indiquer au frontend qu'il faut rediriger
        raise HTTPException(
            status_code=401, 
            detail=e.detail,
            headers={"X-Auth-Redirect": "/login", "X-Auth-Error": "session_expired"}
        )

@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    request: Request,
    org_id: str,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Liste toutes les factures d'une organisation."""
    logger.info(f"📋 GET /invoices appelé - org_id: {org_id}, status: {status}, client_id: {client_id}")
    try:
        user = check_user_org_access(request, org_id)
        logger.info(f"👤 Accès autorisé pour user: {user.get('email', 'unknown')}")
        
        # Utilise select sans jointure pour éviter les problèmes avec la structure existante
        query = get_supabase().table('invoices') \
            .select('*') \
            .eq('org_id', org_id) \
            .order('created_at', desc=True)
        
        if status:
            query = query.eq('status', status)
        
        if client_id:
            query = query.eq('client_id', client_id)
        
        if search:
            query = query.or_(f"invoice_number.ilike.%{search}%,supplier_name.ilike.%{search}%")
        
        query = query.limit(limit)
        logger.info(f"🔍 Exécution requête Supabase pour org_id: {org_id}")
        result = query.execute()
        
        count = len(result.data) if result.data else 0
        logger.info(f"✅ {count} factures trouvées pour org_id: {org_id}")
        
        return result.data or []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste factures: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des factures: {str(e)}")

@router.post("", response_model=InvoiceResponse)
async def create_invoice(request: Request, org_id: str, invoice: InvoiceCreate):
    """Crée une nouvelle facture."""
    try:
        user = check_user_org_access(request, org_id)
        
        invoice_data = {
            'org_id': org_id,
            'created_by': user['sub'],
            'invoice_number': invoice.invoice_number,
            'supplier_name': invoice.supplier_name,
            'amount_ttc': invoice.amount_ttc,
            'amount_ht': invoice.amount_ht,
            'vat_amount': invoice.vat_amount,
            'vat_rate': invoice.vat_rate,
            'status': 'brouillon',
            'invoice_date': invoice.invoice_date,
            'due_date': invoice.due_date,
            'description': invoice.description,
            'client_id': invoice.client_id,
            'company_id': invoice.company_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Filtrer les valeurs None
        invoice_data = {k: v for k, v in invoice_data.items() if v is not None}
        
        result = get_supabase().table('invoices').insert(invoice_data).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Erreur lors de la création de la facture")
        
        invoice = result.data[0]
        invoice_id = invoice['id']
        
        # Insérer les items si présents
        if invoice.items and len(invoice.items) > 0:
            try:
                items_data = []
                for idx, item in enumerate(invoice.items):
                    item_data = {
                        'invoice_id': invoice_id,
                        'org_id': org_id,
                        'description': item.description,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'total_ht': item.total_ht,
                        'vat_rate': item.vat_rate,
                        'sort_order': idx
                    }
                    items_data.append(item_data)
                
                get_supabase().table('invoice_items').insert(items_data).execute()
                logger.info(f"✅ {len(items_data)} item(s) créé(s) pour la facture {invoice_id}")
            except Exception as e:
                logger.error(f"❌ Erreur création items: {e}")
        
        logger.info(f"Facture créée: {invoice_id} par {user['email']}")
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création facture: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la facture: {str(e)}")

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(request: Request, org_id: str, invoice_id: str):
    """Récupère les détails d'une facture."""
    try:
        check_user_org_access(request, org_id)
        
        # Récupérer la facture
        result = get_supabase().table('invoices') \
            .select('*') \
            .eq('id', invoice_id) \
            .eq('org_id', org_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Facture non trouvée")
        
        invoice = result.data[0]
        
        # Récupérer les items de la facture
        try:
            items_result = get_supabase().table('invoice_items') \
                .select('*') \
                .eq('invoice_id', invoice_id) \
                .eq('org_id', org_id) \
                .order('sort_order') \
                .execute()
            
            if items_result.data:
                invoice['items'] = items_result.data
        except Exception as e:
            logger.warning(f"⚠️ Erreur récupération items: {e}")
            invoice['items'] = []
        
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération facture: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de la facture: {str(e)}")

@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(request: Request, org_id: str, invoice_id: str, invoice: InvoiceUpdate):
    """Met à jour une facture (uniquement si en brouillon)."""
    try:
        user = check_user_org_access(request, org_id)
        
        # Vérifier que la facture existe et est en brouillon
        existing = get_supabase().table('invoices') \
            .select('id, status') \
            .eq('id', invoice_id) \
            .eq('org_id', org_id) \
             \
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Facture non trouvée")
        
        if existing.data[0]['status'] != 'brouillon':
            raise HTTPException(status_code=400, detail="Seules les factures en brouillon peuvent être modifiées")
        
        # Filtrer les champs non null
        update_data = {k: v for k, v in invoice.dict().items() if v is not None}
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        result = get_supabase().table('invoices') \
            .update(update_data) \
            .eq('id', invoice_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")
        
        invoice = result.data[0]
        
        # Mettre à jour les items si fournis
        if invoice.items is not None:
            try:
                # Supprimer les anciens items
                get_supabase().table('invoice_items') \
                    .delete() \
                    .eq('invoice_id', invoice_id) \
                    .eq('org_id', org_id) \
                    .execute()
                
                # Insérer les nouveaux items
                if len(invoice.items) > 0:
                    items_data = []
                    for idx, item in enumerate(invoice.items):
                        item_data = {
                            'invoice_id': invoice_id,
                            'org_id': org_id,
                            'description': item.description,
                            'quantity': item.quantity,
                            'unit_price': item.unit_price,
                            'total_ht': item.total_ht,
                            'vat_rate': item.vat_rate,
                            'sort_order': idx
                        }
                        items_data.append(item_data)
                    
                    get_supabase().table('invoice_items').insert(items_data).execute()
                    logger.info(f"✅ {len(items_data)} item(s) mis à jour pour la facture {invoice_id}")
                
                # Récupérer les items mis à jour
                items_result = get_supabase().table('invoice_items') \
                    .select('*') \
                    .eq('invoice_id', invoice_id) \
                    .eq('org_id', org_id) \
                    .order('sort_order') \
                    .execute()
                invoice['items'] = items_result.data if items_result.data else []
                
            except Exception as e:
                logger.error(f"❌ Erreur mise à jour items: {e}")
                invoice['items'] = []
        
        logger.info(f"Facture mise à jour: {invoice_id} par {user['email']}")
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour facture: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour de la facture: {str(e)}")

@router.post("/{invoice_id}/validate")
async def validate_invoice(request: Request, org_id: str, invoice_id: str, action: str):
    """Valide ou rejette une facture."""
    try:
        user = check_user_org_access(request, org_id)
        
        # Vérifier que la facture existe
        existing = get_supabase().table('invoices') \
            .select('id, status') \
            .eq('id', invoice_id) \
            .eq('org_id', org_id) \
             \
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Facture non trouvée")
        
        if existing.data[0]['status'] != 'en_attente_validation':
            raise HTTPException(status_code=400, detail="La facture doit être en attente de validation")
        
        new_status = 'validee' if action == 'validate' else 'rejetee'
        
        update_data = {
            'status': new_status,
            'validated_by': user['sub'],
            'validated_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = get_supabase().table('invoices') \
            .update(update_data) \
            .eq('id', invoice_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Erreur lors de la validation")
        
        # Ajouter à l'historique
        get_supabase().table('invoice_status_history').insert({
            'invoice_id': invoice_id,
            'org_id': org_id,
            'previous_status': 'en_attente_validation',
            'new_status': new_status,
            'changed_by': user['sub'],
            'change_reason': f"Facture {'validée' if action == 'validate' else 'rejetée'} via API"
        }).execute()
        
        logger.info(f"Facture {action}ée: {invoice_id} par {user['email']}")
        return {"success": True, "message": f"Facture {'validée' if action == 'validate' else 'rejetée'} avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur validation facture: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la validation: {str(e)}")

@router.delete("/{invoice_id}")
async def delete_invoice(request: Request, org_id: str, invoice_id: str):
    """Supprime une facture (uniquement si en brouillon)."""
    try:
        user = check_user_org_access(request, org_id)
        
        # Vérifier que la facture existe et est en brouillon
        existing = get_supabase().table('invoices') \
            .select('id, status') \
            .eq('id', invoice_id) \
            .eq('org_id', org_id) \
             \
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Facture non trouvée")
        
        if existing.data[0]['status'] != 'brouillon':
            raise HTTPException(status_code=400, detail="Seules les factures en brouillon peuvent être supprimées")
        
        get_supabase().table('invoices').delete().eq('id', invoice_id).execute()
        
        logger.info(f"Facture supprimée: {invoice_id} par {user['email']}")
        return {"success": True, "message": "Facture supprimée avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression facture: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression de la facture: {str(e)}")


@router.get("/{invoice_id}/download")
async def download_invoice_file(
    request: Request,
    org_id: str,
    invoice_id: str
):
    """
    Télécharge le fichier original d'une facture.
    
    Retourne une redirection 302 vers une URL signée R2 valide 1 heure.
    """
    try:
        user = check_user_org_access(request, org_id)
        
        # Récupérer la facture avec son storage_path
        result = get_supabase().table('invoices')\
            .select('original_file_url, org_id, invoice_number')\
            .eq('id', invoice_id)\
            .eq('org_id', org_id)\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Facture non trouvée")
        
        invoice = result.data
        storage_path = invoice.get('original_file_url')
        
        if not storage_path:
            raise HTTPException(status_code=404, detail="Fichier original non disponible pour cette facture")
        
        # Vérifier que le fichier existe sur R2
        exists = await file_storage_service.file_exists(storage_path)
        if not exists:
            logger.warning(f"⚠️ Fichier facture non trouvé sur R2: {storage_path}")
            raise HTTPException(status_code=404, detail="Fichier non trouvé sur le stockage")
        
        # Générer URL signée
        filename = f"facture_{invoice.get('invoice_number', invoice_id)}.pdf"
        download_url = await file_storage_service.get_presigned_url(
            key=storage_path,
            filename=filename,
            expires=3600
        )
        
        logger.info(
            f"📥 Téléchargement facture\n"
            f"   User: {user.get('email')}\n"
            f"   Invoice: {invoice_id}\n"
            f"   File: {filename}"
        )
        
        # Rediriger vers l'URL signée R2
        return RedirectResponse(url=download_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement facture: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du téléchargement: {str(e)}")
