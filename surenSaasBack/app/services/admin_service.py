"""Service de gestion des utilisateurs et permissions admin."""
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AdminService:
    """Service pour gérer les utilisateurs autorisés et leurs capabilities."""
    
    def __init__(self):
        self.base_url = f"{settings.supabase_url}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Effectue une requête HTTP vers Supabase REST API."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else None
    
    # ==================== PRE_AUTHORIZED_EMAILS ====================
    
    async def get_pre_authorized_emails(self, org_id: str) -> List[Dict]:
        """RÃ©cupÃ¨re la liste des emails prÃ©-autorisÃ©s pour une organisation avec infos Telegram."""
        try:
            # RÃ©cupÃ©rer les emails prÃ©-autorisÃ©s
            result = await self._request(
                "GET",
                f"/pre_authorized_emails?org_id=eq.{org_id}&order=invited_at.desc"
            )
            emails = result or []
            
            # Pour chaque email, rÃ©cupÃ©rer l'utilisateur associÃ© (mÃªme sans used_at)
            for email_data in emails:
                # RÃ©cupÃ©rer l'utilisateur associÃ© Ã  cet email
                user_result = await self._request(
                    "GET",
                    f"/users?org_id=eq.{org_id}&email=eq.{email_data['email']}&select=id,full_name"
                )
                
                if user_result and len(user_result) > 0:
                    user = user_result[0]
                    email_data['user_id'] = user['id']
                    email_data['full_name'] = user.get('full_name')
                    
                    # VÃ©rifier si l'utilisateur a un compte Telegram liÃ©
                    telegram_result = await self._request(
                        "GET",
                        f"/telegram_users?user_id=eq.{user['id']}&org_id=eq.{org_id}&is_verified=eq.true&select=id"
                    )
                    email_data['telegram_linked'] = bool(telegram_result and len(telegram_result) > 0)
                else:
                    email_data['telegram_linked'] = False
                    email_data['user_id'] = None
                    email_data['full_name'] = None
            
            return emails
        except Exception as e:
            logger.error(f"Erreur rÃ©cupÃ©ration emails autorisÃ©s: {e}")
            raise
    
    async def create_pre_authorized_email(
        self, 
        email: str, 
        org_id: str, 
        role: str = "user",
        invited_by: Optional[str] = None
    ) -> Dict:
        """Ajoute un email à la liste des pré-autorisés."""
        try:
            data = {
                "email": email,
                "org_id": org_id,
                "role": role,
                "invited_by": invited_by,
                "invited_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
            result = await self._request(
                "POST",
                "/pre_authorized_emails",
                json=data
            )
            logger.info(f"Email {email} ajouté aux pré-autorisés pour org {org_id}")
            return result
        except Exception as e:
            logger.error(f"Erreur ajout email pré-autorisé: {e}")
            raise
    
    async def update_pre_authorized_email(
        self,
        email_id: str,
        updates: Dict
    ) -> Dict:
        """Met à jour un email pré-autorisé (activation/désactivation/role)."""
        try:
            result = await self._request(
                "PATCH",
                f"/pre_authorized_emails?id=eq.{email_id}",
                json=updates
            )
            logger.info(f"Email pré-autorisé {email_id} mis à jour: {updates}")
            return result
        except Exception as e:
            logger.error(f"Erreur mise à jour email pré-autorisé: {e}")
            raise
    
    async def delete_pre_authorized_email(self, email_id: str) -> None:
        """Supprime un email de la liste des pré-autorisés."""
        try:
            await self._request(
                "DELETE",
                f"/pre_authorized_emails?id=eq.{email_id}"
            )
            logger.info(f"Email pré-autorisé {email_id} supprimé")
        except Exception as e:
            logger.error(f"Erreur suppression email pré-autorisé: {e}")
            raise
    
    # ==================== ORGANIZATION_CAPABILITIES ====================
    
    async def get_organization_capabilities(self, org_id: str) -> List[Dict]:
        """Récupère les capabilities disponibles pour une organisation."""
        try:
            result = await self._request(
                "GET",
                f"/organization_capabilities?org_id=eq.{org_id}&order=resource.asc,action.asc"
            )
            return result or []
        except Exception as e:
            logger.error(f"Erreur récupération capabilities org: {e}")
            raise
    
    async def create_organization_capability(
        self,
        org_id: str,
        capability_code: str,
        description: str,
        resource: str,
        action: str
    ) -> Dict:
        """Crée une nouvelle capability pour l'organisation."""
        try:
            data = {
                "org_id": org_id,
                "capability_code": capability_code,
                "description": description,
                "resource": resource,
                "action": action
            }
            result = await self._request(
                "POST",
                "/organization_capabilities",
                json=data
            )
            logger.info(f"Capability {capability_code} créée pour org {org_id}")
            return result
        except Exception as e:
            logger.error(f"Erreur création capability: {e}")
            raise
    
    # ==================== USER_CAPABILITIES ====================
    
    async def get_user_capabilities(self, user_id: str, org_id: str) -> List[Dict]:
        """Récupère les capabilities assignées à un utilisateur."""
        try:
            # Utilise la vue user_active_capabilities
            result = await self._request(
                "GET",
                f"/user_active_capabilities?user_id=eq.{user_id}&org_id=eq.{org_id}"
            )
            return result or []
        except Exception as e:
            logger.error(f"Erreur récupération capabilities user: {e}")
            raise
    
    async def assign_capability_to_user(
        self,
        user_id: str,
        org_id: str,
        capability_code: str,
        granted_by: str
    ) -> Dict:
        """Assigne une capability à un utilisateur."""
        try:
            data = {
                "user_id": user_id,
                "org_id": org_id,
                "capability_code": capability_code,
                "granted_by": granted_by,
                "is_active": True
            }
            result = await self._request(
                "POST",
                "/user_capabilities",
                json=data
            )
            logger.info(f"Capability {capability_code} assignée à user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Erreur assignation capability: {e}")
            raise
    
    async def revoke_user_capability(
        self,
        user_id: str,
        org_id: str,
        capability_code: str
    ) -> None:
        """Révoque une capability d'un utilisateur (soft delete)."""
        try:
            updates = {
                "is_active": False,
                "revoked_at": datetime.utcnow().isoformat()
            }
            await self._request(
                "PATCH",
                f"/user_capabilities?user_id=eq.{user_id}&org_id=eq.{org_id}&capability_code=eq.{capability_code}",
                json=updates
            )
            logger.info(f"Capability {capability_code} révoquée pour user {user_id}")
        except Exception as e:
            logger.error(f"Erreur révocation capability: {e}")
            raise
    
    async def update_user_capabilities(
        self,
        user_id: str,
        org_id: str,
        capabilities: List[str],
        granted_by: str
    ) -> None:
        """Met à jour toutes les capabilities d'un utilisateur (remplace les existantes)."""
        try:
            # 1. Désactiver toutes les capabilities existantes
            await self._request(
                "PATCH",
                f"/user_capabilities?user_id=eq.{user_id}&org_id=eq.{org_id}",
                json={"is_active": False, "revoked_at": datetime.utcnow().isoformat()}
            )
            
            # 2. Créer les nouvelles
            for cap_code in capabilities:
                await self.assign_capability_to_user(user_id, org_id, cap_code, granted_by)
            
            logger.info(f"Capabilities mises à jour pour user {user_id}: {capabilities}")
        except Exception as e:
            logger.error(f"Erreur mise à jour capabilities user: {e}")
            raise


# Singleton
admin_service = AdminService()
