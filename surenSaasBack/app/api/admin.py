"""Routes API pour l'administration (gestion des utilisateurs et permissions)."""
import os
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from app.api.auth import get_current_user_from_cookie, get_supabase
from app.services.admin_service import admin_service
from app.services.telegram_invitation_service import telegram_invitation_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ==================== MODÈLES ====================

class PreAuthorizedEmailCreate(BaseModel):
    email: EmailStr
    role: str = "user"

class PreAuthorizedEmailUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

class PreAuthorizedEmailResponse(BaseModel):
    id: str
    email: str
    org_id: str
    role: str
    invited_by: Optional[str]
    invited_at: str
    used_at: Optional[str]
    is_active: bool
    user_id: Optional[str] = None  # ID réel de l'utilisateur (table users)
    full_name: Optional[str] = None  # Nom complet de l'utilisateur
    telegram_linked: Optional[bool] = False  # Compte Telegram lié ?

class CapabilityAssignment(BaseModel):
    capability_code: str

class UserCapabilitiesUpdate(BaseModel):
    capabilities: List[str]

class OrganizationCapabilityCreate(BaseModel):
    capability_code: str
    description: str
    resource: str
    action: str


# ==================== DÉPENDANCES ====================

async def verify_admin(request: Request):
    """Vérifie que l'utilisateur est admin de l'organisation."""
    try:
        user = get_current_user_from_cookie(request)
        user_id = user["sub"]
        org_id = user.get("org_id")
        
        if not org_id:
            raise HTTPException(status_code=403, detail="Organisation non définie")
        
        # Vérifier le rôle dans la table users (pas user_org_membership)
        result = get_supabase().table('users') \
            .select('role') \
            .eq('id', user_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=403, detail="Utilisateur non trouvé")
        
        role = result.data[0].get('role')
        if role != 'admin':
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        
        return {"user_id": user_id, "org_id": org_id, "role": role}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur vérification admin: {e}")
        raise HTTPException(status_code=500, detail="Erreur d'authentification")


# ==================== ROUTES PRE_AUTHORIZED_EMAILS ====================

@router.get("/pre-authorized-emails", response_model=List[PreAuthorizedEmailResponse])
async def list_pre_authorized_emails(
    request: Request,
    admin: dict = Depends(verify_admin)
):
    """Liste tous les emails pré-autorisés pour l'organisation."""
    try:
        logger.info(f"📋 Récupération des emails pré-autorisés pour org_id: {admin['org_id']}")
        emails = await admin_service.get_pre_authorized_emails(admin["org_id"])
        logger.info(f"✅ {len(emails)} emails trouvés")
        return emails
    except Exception as e:
        logger.error(f"❌ Erreur listage emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pre-authorized-emails", response_model=PreAuthorizedEmailResponse)
async def create_pre_authorized_email(
    data: PreAuthorizedEmailCreate,
    request: Request,
    admin: dict = Depends(verify_admin)
):
    """Ajoute un email à la liste des pré-autorisés."""
    try:
        result = await admin_service.create_pre_authorized_email(
            email=data.email,
            org_id=admin["org_id"],
            role=data.role,
            invited_by=admin["user_id"]
        )
        return result
    except Exception as e:
        logger.error(f"Erreur création email pré-autorisé: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/pre-authorized-emails/{email_id}")
async def update_pre_authorized_email(
    email_id: str,
    data: PreAuthorizedEmailUpdate,
    admin: dict = Depends(verify_admin)
):
    """Met à jour un email pré-autorisé (rôle ou statut)."""
    try:
        updates = {}
        if data.role is not None:
            updates["role"] = data.role
        if data.is_active is not None:
            updates["is_active"] = data.is_active
        
        result = await admin_service.update_pre_authorized_email(email_id, updates)
        return {"success": True, "message": "Email mis à jour"}
    except Exception as e:
        logger.error(f"Erreur mise à jour email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pre-authorized-emails/{email_id}")
async def delete_pre_authorized_email(
    email_id: str,
    admin: dict = Depends(verify_admin)
):
    """Supprime un email de la liste des pré-autorisés."""
    try:
        await admin_service.delete_pre_authorized_email(email_id)
        return {"success": True, "message": "Email supprimé"}
    except Exception as e:
        logger.error(f"Erreur suppression email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ROUTES CAPABILITIES ====================

@router.get("/organization-capabilities")
async def list_organization_capabilities(
    admin: dict = Depends(verify_admin)
):
    """Liste toutes les capabilities disponibles pour l'organisation."""
    try:
        capabilities = await admin_service.get_organization_capabilities(admin["org_id"])
        # Grouper par resource pour faciliter l'affichage frontend
        grouped = {}
        for cap in capabilities:
            resource = cap.get("resource", "other")
            if resource not in grouped:
                grouped[resource] = []
            grouped[resource].append(cap)
        return {"capabilities": capabilities, "grouped": grouped}
    except Exception as e:
        logger.error(f"Erreur listage capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organization-capabilities")
async def create_organization_capability(
    data: OrganizationCapabilityCreate,
    admin: dict = Depends(verify_admin)
):
    """Crée une nouvelle capability pour l'organisation."""
    try:
        result = await admin_service.create_organization_capability(
            org_id=admin["org_id"],
            capability_code=data.capability_code,
            description=data.description,
            resource=data.resource,
            action=data.action
        )
        return result
    except Exception as e:
        logger.error(f"Erreur création capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/capabilities")
async def get_user_capabilities(
    user_id: str,
    admin: dict = Depends(verify_admin)
):
    """Récupère les capabilities assignées à un utilisateur."""
    try:
        capabilities = await admin_service.get_user_capabilities(
            user_id=user_id,
            org_id=admin["org_id"]
        )
        return {"user_id": user_id, "capabilities": capabilities}
    except Exception as e:
        logger.error(f"Erreur récupération capabilities user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/capabilities")
async def assign_capability_to_user(
    user_id: str,
    data: CapabilityAssignment,
    request: Request,
    admin: dict = Depends(verify_admin)
):
    """Assigne une capability à un utilisateur."""
    try:
        result = await admin_service.assign_capability_to_user(
            user_id=user_id,
            org_id=admin["org_id"],
            capability_code=data.capability_code,
            granted_by=admin["user_id"]
        )
        return {"success": True, "message": "Capability assignée"}
    except Exception as e:
        logger.error(f"Erreur assignation capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/capabilities")
async def update_user_capabilities(
    user_id: str,
    data: UserCapabilitiesUpdate,
    request: Request,
    admin: dict = Depends(verify_admin)
):
    """Met à jour toutes les capabilities d'un utilisateur."""
    try:
        await admin_service.update_user_capabilities(
            user_id=user_id,
            org_id=admin["org_id"],
            capabilities=data.capabilities,
            granted_by=admin["user_id"]
        )
        return {"success": True, "message": "Capabilities mises à jour"}
    except Exception as e:
        logger.error(f"Erreur mise à jour capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}/capabilities/{capability_code}")
async def revoke_user_capability(
    user_id: str,
    capability_code: str,
    admin: dict = Depends(verify_admin)
):
    """Révoque une capability d'un utilisateur."""
    try:
        await admin_service.revoke_user_capability(
            user_id=user_id,
            org_id=admin["org_id"],
            capability_code=capability_code
        )
        return {"success": True, "message": "Capability révoquée"}
    except Exception as e:
        logger.error(f"Erreur révocation capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ROUTES TELEGRAM INVITATIONS ====================

@router.get("/telegram/bots")
async def list_telegram_bots(
    request: Request,
    admin: dict = Depends(verify_admin)
):
    """
    Liste tous les bots Telegram configurés pour l'organisation depuis Supabase.
    """
    try:
        # Récupérer les bots depuis Supabase (pas depuis le registry en mémoire)
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        org_id = admin["org_id"]
        logger.info(f"🔍 Recherche bots Telegram pour org_id: {org_id} (type: {type(org_id)})")
        
        # Essayer sans filtre org_id d'abord pour debug
        all_result = supabase.table('telegram_bots') \
            .select('bot_id, bot_username, org_id, is_active') \
            .execute()
        logger.info(f"📊 Total bots dans DB: {len(all_result.data or [])}")
        if all_result.data:
            for b in all_result.data:
                logger.info(f"  - Bot org_id: {b.get('org_id')} (type: {type(b.get('org_id'))}), is_active: {b.get('is_active')}")
        
        result = supabase.table('telegram_bots') \
            .select('bot_id, bot_username, description, welcome_message, is_active, allowed_roles') \
            .eq('org_id', org_id) \
            .execute()
        
        # Filtrer côté Python pour éviter les problèmes de type avec is_active
        all_bots = result.data or []
        bots_data = [bot for bot in all_bots if bot.get('is_active') == True or bot.get('is_active') == 'true' or str(bot.get('is_active')).lower() == 'true']
        logger.info(f"✅ {len(bots_data)} bot(s) trouvé(s) sur {len(all_bots)} total")
        
        # Formater pour le frontend
        bots = []
        for bot in bots_data:
            bot_id = str(bot.get('bot_id', 'Bot'))
            bots.append({
                'bot_id': bot_id,
                'bot_name': bot_id.replace('_', ' ').title(),
                'description': bot.get('description', 'Bot Telegram'),
                'icon': '🤖',
                'username': bot.get('bot_username', ''),
                'configured': True
            })
        
        return {
            "bots": bots,
            "environment": os.getenv("ENVIRONMENT", "test")
        }
    except Exception as e:
        logger.error(f"Erreur listage bots Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/telegram-invitation")
async def create_telegram_invitation(
    user_id: str,
    request: Request,
    admin: dict = Depends(verify_admin)
):
    """
    Génère un lien d'invitation Telegram pour un utilisateur vers un bot spécifique.
    
    Body JSON:
        - bot_id: ID du bot (e.g., 'construction', 'audit', 'nettoyage')
        - expires_in_hours: Durée de validité (défaut: 168h = 7 jours)
    """
    try:
        # Récupérer les paramètres du body
        body = await request.json()
        bot_id = body.get("bot_id")
        expires_in_hours = body.get("expires_in_hours", 168)
        
        if not bot_id:
            raise HTTPException(status_code=400, detail="bot_id requis")
        
        # Vérifier que le bot existe dans Supabase
        bot_result = get_supabase().table('telegram_bots') \
            .select('*') \
            .eq('bot_id', bot_id) \
            .eq('org_id', admin["org_id"]) \
            .eq('is_active', True) \
            .single() \
            .execute()
        
        if not bot_result.data:
            raise HTTPException(status_code=400, detail=f"Bot '{bot_id}' non configuré pour cette organisation")
        
        bot_config = bot_result.data
        
        # Générer le lien d'invitation (user_id peut être de pre_authorized_emails)
        invitation = telegram_invitation_service.generate_invitation_link(
            user_id=user_id,
            org_id=admin["org_id"],
            bot_id=bot_id,
            expires_in_hours=expires_in_hours,
            bot_config=bot_config
        )
        
        logger.info(f"Invitation Telegram générée par admin {admin['user_id']} "
                   f"pour user {user_id} vers bot '{bot_id}'")
        
        return invitation
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur génération invitation Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))
