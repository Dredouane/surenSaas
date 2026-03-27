"""
Core: Capabilities

Système de vérification des capabilities pour la sécurité.
Les admins bypassent automatiquement les vérifications.
"""

from functools import wraps
from typing import Optional, List, Callable
from fastapi import HTTPException, Request, Depends

from app.core.supabase import get_supabase


class CapabilityChecker:
    """Vérifie les capabilities des utilisateurs."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def has_capability(
        self,
        user_id: str,
        org_id: str,
        capability: str
    ) -> bool:
        """
        Vérifie si un utilisateur a une capability.
        Les admins bypassent automatiquement.
        
        Args:
            user_id: UUID de l'utilisateur
            org_id: UUID de l'organisation
            capability: Code de la capability (ex: 'construction:facturation:read')
            
        Returns:
            True si l'utilisateur a la capability ou est admin
        """
        # Vérifier si admin (bypass) - utilise la table users directement
        user = self.supabase.table('users') \
            .select('role') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if user.data and user.data.get('role') == 'admin':
            return True
        
        # Vérifier la capability
        cap = self.supabase.table('user_capabilities') \
            .select('*') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .eq('capability_code', capability) \
            .eq('is_active', True) \
            .execute()
        
        return len(cap.data) > 0 if cap.data else False
    
    async def has_any_capability(
        self,
        user_id: str,
        org_id: str,
        capabilities: List[str]
    ) -> bool:
        """Vérifie si l'utilisateur a au moins une des capabilities."""
        # Vérifier si admin
        membership = self.supabase.table('users') \
            .select('role') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if membership.data and membership.data.get('role') == 'admin':
            return True
        
        # Vérifier les capabilities
        caps = self.supabase.table('user_capabilities') \
            .select('*') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .in_('capability_code', capabilities) \
            .eq('is_active', True) \
            .execute()
        
        return len(caps.data) > 0 if caps.data else False
    
    async def has_all_capabilities(
        self,
        user_id: str,
        org_id: str,
        capabilities: List[str]
    ) -> bool:
        """Vérifie si l'utilisateur a toutes les capabilities."""
        # Vérifier si admin
        membership = self.supabase.table('users') \
            .select('role') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if membership.data and membership.data.get('role') == 'admin':
            return True
        
        # Vérifier les capabilities
        caps = self.supabase.table('user_capabilities') \
            .select('*') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .in_('capability_code', capabilities) \
            .eq('is_active', True) \
            .execute()
        
        user_caps = set(c['capability_code'] for c in (caps.data or []))
        required_caps = set(capabilities)
        
        return required_caps.issubset(user_caps)
    
    async def get_user_capabilities(
        self,
        user_id: str,
        org_id: str
    ) -> List[str]:
        """Récupère toutes les capabilities d'un utilisateur."""
        # Si admin, retourner toutes les capabilities de l'org
        membership = self.supabase.table('users') \
            .select('role') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if membership.data and membership.data.get('role') == 'admin':
            # Retourner toutes les capabilities de l'org
            all_caps = self.supabase.table('organization_capabilities') \
                .select('capability_code') \
                .eq('org_id', org_id) \
                .execute()
            return [c['capability_code'] for c in (all_caps.data or [])]
        
        # Sinon, retourner les capabilities assignées
        caps = self.supabase.table('user_active_capabilities') \
            .select('capability_code') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .execute()
        
        return [c['capability_code'] for c in (caps.data or [])]


# Dépendance FastAPI pour le checker
def get_capability_checker():
    """Factory pour CapabilityChecker."""
    supabase = get_supabase()
    return CapabilityChecker(supabase)


# Décorateur de vérification pour FastAPI
def require_capability(capability: str):
    """
    Décorateur FastAPI pour exiger une capability.
    
    Usage:
        @router.get("/invoices")
        async def list_invoices(
            user: dict = Depends(get_current_user),
            checker: CapabilityChecker = Depends(get_capability_checker)
        ):
            # Vérification manuelle
            if not await checker.has_capability(user['id'], org_id, 'construction:facturation:read'):
                raise HTTPException(403, "Capability requise")
    
    Ou utiliser le middleware/dependency:
        @router.get("/invoices", dependencies=[Depends(require_capability('construction:facturation:read'))])
    """
    async def checker(
        request: Request,
        capability_checker: CapabilityChecker = Depends(get_capability_checker)
    ):
        user = request.state.user  # Doit être défini par un middleware d'auth
        org_id = request.path_params.get('org')
        
        if not user or not org_id:
            raise HTTPException(401, "Non authentifié")
        
        has_cap = await capability_checker.has_capability(
            user_id=user['id'],
            org_id=org_id,
            capability=capability
        )
        
        if not has_cap:
            raise HTTPException(403, f"Capability requise: {capability}")
        
        return True
    
    return checker


# Constants pour les capabilities construction
CONSTRUCTION_CAPABILITIES = {
    'FACTURATION_READ': 'construction:facturation:read',
    'FACTURATION_WRITE': 'construction:facturation:write',
    'FACTURATION_VALIDATE': 'construction:facturation:validate',
    'FACTURATION_DELETE': 'construction:facturation:delete',
}
