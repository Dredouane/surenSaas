"""
API Endpoints pour le téléchargement de fichiers.

Routes:
- GET /api/v1/{org}/files/download : Téléchargement générique par storage_path
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.core.logging import get_logger
from app.core.config import get_settings
from app.services.file_storage_service import file_storage_service
from app.api.auth import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/{org}/files", tags=["files"])


@router.get("/download")
async def download_file(
    org: str,
    storage_path: str = Query(..., description="Chemin de stockage R2 complet (ex: test/org/xxx/invoices/20250115_143022_123456_facture.pdf)"),
    filename: Optional[str] = Query(None, description="Nom de fichier suggéré pour le téléchargement"),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint générique de téléchargement par storage_path.
    
    Vérifie que l'utilisateur a accès au fichier (même org_id),
    puis génère une URL signée et redirige vers R2.
    
    Args:
        org: Slug de l'organisation (ex: REDACTED_ORG_SLUG)
        storage_path: Clé S3 complète du fichier
        filename: Nom de fichier optionnel pour le Content-Disposition
        current_user: Utilisateur authentifié (via cookie)
        
    Returns:
        302 Redirect vers l'URL signée R2
        
    Raises:
        403: Si l'utilisateur n'a pas accès au fichier
        404: Si le fichier n'existe pas
    """
    settings = get_settings()
    environment = settings.environment.lower()
    
    # Récupérer l'org_id de l'utilisateur
    user_org_id = current_user.get('org_id')
    if not user_org_id:
        logger.warning(f"❌ Utilisateur sans org_id: {current_user.get('id')}")
        raise HTTPException(status_code=403, detail="Organisation non définie pour l'utilisateur")
    
    # Vérifier que le storage_path appartient à l'environnement et org corrects
    expected_prefix = f"{environment}/org/{user_org_id}/"
    
    if not storage_path.startswith(expected_prefix):
        logger.warning(
            f"🚫 Tentative d'accès non autorisé au fichier\n"
            f"   User: {current_user.get('email')} (org: {user_org_id})\n"
            f"   Storage path: {storage_path}\n"
            f"   Expected prefix: {expected_prefix}"
        )
        raise HTTPException(status_code=403, detail="Accès non autorisé à ce fichier")
    
    # Vérifier que le fichier existe
    exists = await file_storage_service.file_exists(storage_path)
    if not exists:
        logger.warning(f"⚠️ Fichier non trouvé sur R2: {storage_path}")
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    
    # Générer URL signée (valide 1 heure)
    try:
        download_url = await file_storage_service.get_presigned_url(
            key=storage_path,
            filename=filename,
            expires=3600
        )
        
        logger.info(
            f"📥 Téléchargement fichier\n"
            f"   User: {current_user.get('email')}\n"
            f"   File: {storage_path}"
        )
        
        # Rediriger vers l'URL signée R2
        return RedirectResponse(url=download_url)
        
    except Exception as e:
        logger.error(f"❌ Erreur génération URL signée: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du lien de téléchargement")
