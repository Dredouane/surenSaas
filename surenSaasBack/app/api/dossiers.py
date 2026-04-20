"""
API Endpoints pour les Dossiers (Le Classeur).

Routes:
- GET    /api/v1/{org}/dossiers                 # Liste
- POST   /api/v1/{org}/dossiers                 # Créer
- GET    /api/v1/{org}/dossiers/{id}            # Détail
- PATCH  /api/v1/{org}/dossiers/{id}            # Modifier
- DELETE /api/v1/{org}/dossiers/{id}            # Supprimer
- GET    /api/v1/{org}/dossiers/{id}/emails     # Threads liés
- GET    /api/v1/{org}/dossiers/{id}/documents  # Documents agrégés
- GET    /api/v1/{org}/dossiers/{id}/summary    # Résumé cross-threads
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.logging import get_logger
from app.models.dossiers import (
    DossierCreate, DossierUpdate, DossierDetail, DossierListResponse,
    LinkThreadToDossierRequest, SuggestedDossiersResponse
)
from app.services.dossier_service import dossier_service

logger = get_logger(__name__)
router = APIRouter()

# TODO: Remplacer par vrai auth quand migré
def get_current_org(org: str):
    """Récupère l'org_id depuis le slug."""
    from app.api.auth import get_supabase
    supabase = get_supabase()
    
    org_response = supabase.table("organizations")\
        .select("id")\
        .eq("slug", org)\
        .single()\
        .execute()
    
    if not org_response.data:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return UUID(org_response.data["id"])


@router.get("/{org}/dossiers", response_model=DossierListResponse)
async def list_dossiers(
    org: str,
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    search: Optional[str] = Query(None, description="Recherche textuelle"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    org_id: UUID = Depends(get_current_org)
):
    """
    Liste les dossiers avec filtres et pagination.
    """
    try:
        result = dossier_service.list_dossiers(
            org_id=org_id,
            status=status,
            search=search,
            page=page,
            limit=limit
        )
        return DossierListResponse(**result)
    except Exception as e:
        logger.error(f"Error listing dossiers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{org}/dossiers", response_model=DossierDetail)
async def create_dossier(
    org: str,
    data: DossierCreate,
    org_id: UUID = Depends(get_current_org)
):
    """
    Crée un nouveau dossier.
    """
    try:
        dossier = dossier_service.create_dossier(
            org_id=org_id,
            company_id=None,  # Sera déduit si besoin
            data=data
        )
        return dossier
    except Exception as e:
        logger.error(f"Error creating dossier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{org}/dossiers/{dossier_id}", response_model=DossierDetail)
async def get_dossier(
    org: str,
    dossier_id: UUID,
    org_id: UUID = Depends(get_current_org)
):
    """
    Récupère le détail d'un dossier.
    """
    dossier = dossier_service.get_dossier(dossier_id, org_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return dossier


@router.patch("/{org}/dossiers/{dossier_id}", response_model=DossierDetail)
async def update_dossier(
    org: str,
    dossier_id: UUID,
    data: DossierUpdate,
    org_id: UUID = Depends(get_current_org)
):
    """
    Modifie un dossier.
    """
    try:
        dossier = dossier_service.update_dossier(dossier_id, org_id, data)
        return dossier
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating dossier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{org}/dossiers/{dossier_id}")
async def delete_dossier(
    org: str,
    dossier_id: UUID,
    org_id: UUID = Depends(get_current_org)
):
    """
    Supprime (soft delete) un dossier.
    """
    success = dossier_service.delete_dossier(dossier_id, org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return {"success": True, "message": "Dossier marked as cancelled"}


@router.get("/{org}/dossiers/{dossier_id}/emails")
async def get_dossier_emails(
    org: str,
    dossier_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    org_id: UUID = Depends(get_current_org)
):
    """
    Récupère les threads (emails) liés à un dossier.
    """
    try:
        threads = dossier_service.get_threads_in_dossier(
            dossier_id=dossier_id,
            org_id=org_id,
            page=page,
            limit=limit
        )
        return {"data": threads, "page": page, "limit": limit}
    except Exception as e:
        logger.error(f"Error getting dossier emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{org}/dossiers/{dossier_id}/documents")
async def get_dossier_documents(
    org: str,
    dossier_id: UUID,
    org_id: UUID = Depends(get_current_org)
):
    """
    Récupère les documents (pièces jointes) agrégés d'un dossier.
    """
    try:
        documents = dossier_service.get_documents_in_dossier(dossier_id, org_id)
        return documents
    except Exception as e:
        logger.error(f"Error getting dossier documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{org}/dossiers/{dossier_id}/summary")
async def get_dossier_summary(
    org: str,
    dossier_id: UUID,
    org_id: UUID = Depends(get_current_org)
):
    """
    Génère et retourne le résumé cross-threads d'un dossier.
    """
    try:
        summary = await dossier_service.generate_cross_thread_summary(
            dossier_id=dossier_id,
            org_id=org_id
        )
        return {
            "dossier_id": str(dossier_id),
            "summary": summary,
            "generated_at": "2025-04-12T00:00:00Z"  # TODO: vrai timestamp
        }
    except Exception as e:
        logger.error(f"Error generating dossier summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
