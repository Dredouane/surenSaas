from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.api.auth import get_current_user_from_cookie, get_supabase
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/clients", tags=["clients"])

# Schémas Pydantic
class ClientBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    siret: Optional[str] = None
    notes: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    siret: Optional[str] = None
    notes: Optional[str] = None

class ClientResponse(ClientBase):
    id: str
    org_id: str
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

def check_user_org_access(request: Request, org_id: str):
    """Vérifie que l'utilisateur a accès à cette organisation."""
    user = get_current_user_from_cookie(request)
    if user["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Accès non autorisé à cette organisation")
    return user

@router.get("", response_model=List[ClientResponse])
async def list_clients(
    request: Request,
    org_id: str,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Liste tous les clients d'une organisation."""
    try:
        check_user_org_access(request, org_id)
        
        query = get_supabase().table('clients') \
            .select('*') \
            .eq('org_id', org_id) \
            .order('created_at', desc=True)
        
        if search:
            query = query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%")
        
        query = query.limit(limit)
        result = query.execute()
        
        return result.data or []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur liste clients: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des clients: {str(e)}")

@router.post("", response_model=ClientResponse)
async def create_client(request: Request, org_id: str, client: ClientCreate):
    """Crée un nouveau client."""
    try:
        user = check_user_org_access(request, org_id)
        
        client_data = {
            'org_id': org_id,
            'name': client.name,
            'email': client.email,
            'phone': client.phone,
            'address': client.address,
            'siret': client.siret,
            'notes': client.notes,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = get_supabase().table('clients').insert(client_data).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Erreur lors de la création du client")
        
        logger.info(f"Client créé: {result.data[0]['id']} par {user['email']}")
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du client: {str(e)}")

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(request: Request, org_id: str, client_id: str):
    """Récupère les détails d'un client."""
    try:
        check_user_org_access(request, org_id)
        
        result = get_supabase().table('clients') \
            .select('*') \
            .eq('id', client_id) \
            .eq('org_id', org_id) \
             \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du client: {str(e)}")

@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(request: Request, org_id: str, client_id: str, client: ClientUpdate):
    """Met à jour un client."""
    try:
        user = check_user_org_access(request, org_id)
        
        # Vérifier que le client existe
        existing = get_supabase().table('clients') \
            .select('id') \
            .eq('id', client_id) \
            .eq('org_id', org_id) \
             \
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        
        # Filtrer les champs non null
        update_data = {k: v for k, v in client.dict().items() if v is not None}
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        result = get_supabase().table('clients') \
            .update(update_data) \
            .eq('id', client_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")
        
        logger.info(f"Client mis à jour: {client_id} par {user['email']}")
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour du client: {str(e)}")

@router.delete("/{client_id}")
async def delete_client(request: Request, org_id: str, client_id: str):
    """Supprime un client."""
    try:
        user = check_user_org_access(request, org_id)
        
        # Vérifier que le client existe
        existing = get_supabase().table('clients') \
            .select('id') \
            .eq('id', client_id) \
            .eq('org_id', org_id) \
             \
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        
        get_supabase().table('clients').delete().eq('id', client_id).execute()
        
        logger.info(f"Client supprimé: {client_id} par {user['email']}")
        return {"success": True, "message": "Client supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression du client: {str(e)}")
