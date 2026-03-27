from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.api.auth import get_current_user_from_cookie, get_supabase
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

class UserProfileResponse(BaseModel):
    id: str
    email: str
    org_id: str
    org_slug: str
    org_name: str
    role: str
    created_at: Optional[str] = None

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(request: Request):
    """
    Récupère le profil de l'utilisateur connecté.
    Version robuste avec multiples fallbacks.
    """
    try:
        # 1. Récupérer l'utilisateur depuis le cookie
        user = get_current_user_from_cookie(request)
        user_id = user.get("sub")
        user_email = user.get("email")
        
        if not user_id or not user_email:
            logger.error("Token invalide: sub ou email manquant")
            raise HTTPException(status_code=401, detail="Session invalide")
        
        logger.info(f"🔍 Récupération profil pour {user_email} (ID: {user_id})")
        
        # Valeurs par défaut depuis le token
        org_id = user.get("org_id")
        org_slug = user.get("org_slug", "")
        role = user.get("role", "user")
        
        # 2. Essayer de récupérer depuis la table users
        try:
            user_data_result = get_supabase().table('users') \
                .select('*') \
                .eq('id', user_id) \
                .maybe_single() \
                .execute()
            
            if user_data_result.data:
                user_data = user_data_result.data
                org_id = user_data.get('org_id', org_id)
                role = user_data.get('role', role)
                logger.info(f"✅ Profil trouvé dans table users pour {user_email}")
            else:
                logger.warning(f"⚠️ Utilisateur {user_id} non trouvé dans table users")
        except Exception as e:
            logger.warning(f"⚠️ Erreur récupération table users: {e}")
        
        # 3. Récupérer les infos de l'organisation
        if org_id:
            try:
                org_result = get_supabase().table('organizations') \
                    .select('slug, name') \
                    .eq('id', org_id) \
                    .maybe_single() \
                    .execute()
                
                if org_result.data:
                    org_slug = org_result.data.get('slug', org_slug)
                    org_name = org_result.data.get('name', '')
                    logger.info(f"✅ Org trouvée: {org_slug}")
                else:
                    org_name = org_slug or "Mon Organisation"
            except Exception as e:
                logger.warning(f"⚠️ Erreur récupération org: {e}")
                org_name = org_slug or "Mon Organisation"
        else:
            logger.error(f"❌ org_id manquant pour {user_email}")
            raise HTTPException(status_code=500, detail="Configuration utilisateur incomplète")
        
        # 4. Construire la réponse
        response_data = UserProfileResponse(
            id=user_id,
            email=user_email,
            org_id=org_id,
            org_slug=org_slug,
            org_name=org_name,
            role=role,
            created_at=user.get("created_at")
        )
        
        logger.info(f"✅ Profil retourné pour {user_email}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique récupération profil: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la récupération du profil: {str(e)}"
        )
