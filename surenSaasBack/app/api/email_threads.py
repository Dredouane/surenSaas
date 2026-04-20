"""
API Routes pour la gestion des threads email.

Base URL: /api/v1/{org}/email-threads
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.logging import get_logger
from app.api.auth import get_supabase
from app.services.email_thread_service import thread_service
from app.models.email_threads import (
    ThreadListResponse,
    ThreadDetail,
    ThreadChatResponse,
    SendChatMessageRequest,
    SendChatMessageResponse,
    UpdateThreadRequest,
    UpdateThreadResponse,
    ChatMessage
)

logger = get_logger(__name__)
router = APIRouter()

# TODO: Remplacer par le vrai require_capability quand migré
def require_capability(capability: str):
    """Dépendance temporaire pour les capabilities."""
    async def _require_capability(current_user: dict = Depends(lambda: {"id": "test", "org_id": "test"})):
        # Pour l'instant, permissif
        return current_user
    return _require_capability


def _format_thread_list_item(thread: dict) -> dict:
    """Formate un thread pour la liste."""
    return {
        "id": thread["id"],
        "gmail_thread_id": thread["gmail_thread_id"],
        "subject": thread.get("subject", ""),
        "subject_cleaned": thread.get("subject_cleaned"),
        "participants": {
            "emails": thread.get("participant_emails", []),
            "names": thread.get("participant_names", [])
        },
        "ai_summary": thread.get("ai_summary"),
        "ai_urgency": thread.get("ai_urgency", "medium"),
        "ai_status": thread.get("ai_status", "new"),
        "metrics": {
            "email_count": thread.get("email_count", 0),
            "attachment_count": thread.get("attachment_count", 0),
            "first_email_at": thread.get("first_email_at"),
            "last_email_at": thread.get("last_email_at")
        },
        "flags": {
            "is_archived": thread.get("is_archived", False),
            "is_starred": thread.get("is_starred", False)
        },
        "is_historical_partial": thread.get("is_historical_partial", False),
        "created_at": thread["created_at"],
        "updated_at": thread["updated_at"]
    }


def _format_email_in_thread(email: dict) -> dict:
    """Formate un email pour l'affichage dans un thread."""
    # Déterminer le rôle (client ou toi) basé sur l'email expéditeur
    sender_email = email.get("sender_email", "")
    # TODO: Comparer avec l'email de l'entreprise pour déterminer "toi" vs "client"
    role = "client"  # Par défaut, on considère que c'est le client
    
    return {
        "id": email["id"],
        "role": role,
        "sender": {
            "email": sender_email,
            "name": email.get("sender_name")
        },
        "subject": email.get("subject", ""),
        "content": {
            "text": email.get("content_text"),
            "html": email.get("content_html")
        },
        "sent_at": email.get("sent_at"),
        "has_attachments": email.get("has_attachments", False),
        "attachments": []  # TODO: Récupérer les PJ si nécessaire
    }


def _format_chat_session(session: dict) -> dict:
    """Formate une session de chat."""
    if not session:
        return None
    return {
        "id": session.get("id"),
        "name": session.get("name", "Chat"),
        "message_count": session.get("message_count", 0),
        "last_message_at": session.get("last_message_at"),
        "is_default": session.get("is_default", False)
    }


def _format_chat_message(message: dict) -> dict:
    """Formate un message de chat."""
    return {
        "id": message["id"],
        "role": message["role"],
        "content": message["content"],
        "metadata": message.get("metadata", {}),
        "created_at": message["created_at"]
    }


# ============================================================================
# Liste des threads
# ============================================================================

@router.get("/{org}/email-threads", response_model=ThreadListResponse)
async def list_threads(
    org: str,
    company_id: Optional[UUID] = Query(None, description="Filtrer par entreprise"),
    status: Optional[str] = Query(None, description="Filtrer par statut IA (new, in_progress, waiting, resolved)"),
    urgency: Optional[str] = Query(None, description="Filtrer par urgence (low, medium, high)"),
    search: Optional[str] = Query(None, description="Recherche textuelle"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'items par page"),
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Liste les threads email avec filtres et pagination.
    
    Les threads sont triés par date du dernier email (plus récent d'abord).
    """
    try:
        # Récupérer l'org_id depuis le slug
        supabase = get_supabase()
        try:
            org_response = supabase.table("organizations")\
                .select("id")\
                .eq("slug", org)\
                .single()\
                .execute()
        except Exception:
            raise HTTPException(status_code=404, detail="Organization not found")

        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        org_id = UUID(org_response.data["id"])

        # Récupérer les threads
        result = thread_service.list_threads(
            org_id=org_id,
            company_id=company_id,
            status=status,
            urgency=urgency,
            search=search,
            page=page,
            limit=limit
        )
        
        # Formater les threads
        formatted_threads = [_format_thread_list_item(t) for t in result["data"]]
        
        return {
            "data": formatted_threads,
            "pagination": result["pagination"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Détail d'un thread
# ============================================================================

@router.get("/{org}/email-threads/{thread_id}", response_model=ThreadDetail)
async def get_thread(
    org: str,
    thread_id: UUID,
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Récupère le détail d'un thread avec tous ses emails.
    
    Retourne:
    - Les métadonnées du thread (sujet, participants, analyse IA)
    - La liste des emails formatés (style chat)
    - Les métriques (nombre d'emails, PJ)
    - La session de chat associée
    """
    try:
        # Récupérer l'org_id depuis le slug
        supabase = get_supabase()
        try:
            org_response = supabase.table("organizations")\
                .select("id")\
                .eq("slug", org)\
                .single()\
                .execute()
        except Exception:
            raise HTTPException(status_code=404, detail="Organization not found")

        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        org_id = UUID(org_response.data["id"])

        # Récupérer le thread
        thread = thread_service.get_thread(thread_id, org_id)

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Formater la réponse
        formatted_thread = {
            "id": thread["id"],
            "gmail_thread_id": thread["gmail_thread_id"],
            "subject": thread.get("subject", ""),
            "subject_cleaned": thread.get("subject_cleaned"),
            "participants": {
                "emails": thread.get("participant_emails", []),
                "names": thread.get("participant_names", [])
            },
            "ai_summary": thread.get("ai_summary"),
            "ai_context": thread.get("ai_context"),
            "ai_urgency": thread.get("ai_urgency", "medium"),
            "ai_status": thread.get("ai_status", "new"),
            "flags": {
                "is_archived": thread.get("is_archived", False),
                "is_starred": thread.get("is_starred", False)
            },
            "emails": [_format_email_in_thread(e) for e in thread.get("emails", [])],
            "metrics": {
                "email_count": thread.get("email_count", 0),
                "attachment_count": thread.get("attachment_count", 0),
                "first_email_at": thread.get("first_email_at"),
                "last_email_at": thread.get("last_email_at")
            },
            "chat_session": _format_chat_session(thread["chat_session"]) if thread.get("chat_session") else None,
            "is_historical_partial": thread.get("is_historical_partial", False),
            "historical_notes": thread.get("historical_notes"),
            "created_at": thread["created_at"],
            "updated_at": thread["updated_at"]
        }
        
        return formatted_thread
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Chat d'un thread
# ============================================================================

@router.get("/{org}/email-threads/{thread_id}/chat", response_model=ThreadChatResponse)
async def get_thread_chat(
    org: str,
    thread_id: UUID,
    session_id: Optional[UUID] = Query(None, description="ID de session (optionnel, prend la défaut)"),
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Récupère le chat d'un thread avec tous ses messages.

    Si aucune session_id n'est fournie, retourne la session par défaut
    (en crée une si nécessaire).
    """
    try:
        # Récupérer l'org_id depuis le slug
        supabase = get_supabase()
        try:
            org_response = supabase.table("organizations")\
                .select("id")\
                .eq("slug", org)\
                .single()\
                .execute()
        except Exception:
            raise HTTPException(status_code=404, detail="Organization not found")

        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org_id = UUID(org_response.data["id"])
        
        # Vérifier que le thread existe
        thread = thread_service.get_thread(thread_id, org_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Récupérer le chat
        chat_data = thread_service.get_chat_session(thread_id, org_id, session_id)
        
        if not chat_data:
            # Créer une session par défaut
            chat_data = thread_service.get_chat_session(thread_id, org_id, None)
        
        session = chat_data["session"]
        messages = chat_data["messages"]
        
        return {
            "session": {
                "id": session["id"],
                "name": session.get("name", "Chat"),
                "message_count": session.get("message_count", 0),
                "last_message_at": session.get("last_message_at"),
                "is_default": session.get("is_default", False),
                "rag_context": session.get("rag_context", {}),
                "created_at": session["created_at"]
            },
            "messages": [_format_chat_message(m) for m in messages]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread chat {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{org}/email-threads/{thread_id}/chat", response_model=SendChatMessageResponse)
async def send_chat_message(
    org: str,
    thread_id: UUID,
    request: SendChatMessageRequest,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """
    Envoie un message au chat d'un thread.
    
    Crée automatiquement une session de chat si nécessaire.
    Retourne le message utilisateur et la réponse de l'IA (mockée pour l'instant).
    """
    try:
        # Récupérer l'org_id depuis le slug
        supabase = get_supabase()
        try:
            org_response = supabase.table("organizations")\
                .select("id")\
                .eq("slug", org)\
                .single()\
                .execute()
        except Exception:
            raise HTTPException(status_code=404, detail="Organization not found")

        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        org_id = UUID(org_response.data["id"])

        # Vérifier que le thread existe
        thread = thread_service.get_thread(thread_id, org_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Envoyer le message
        result = thread_service.send_chat_message(
            thread_id=thread_id,
            org_id=org_id,
            message=request.message,
            session_id=request.session_id
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to send message")
        
        return {
            "user_message": _format_chat_message(result["user_message"]),
            "assistant_message": _format_chat_message(result["assistant_message"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Actions sur un thread
# ============================================================================

@router.patch("/{org}/email-threads/{thread_id}", response_model=UpdateThreadResponse)
async def update_thread(
    org: str,
    thread_id: UUID,
    request: UpdateThreadRequest,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """
    Met à jour un thread (statut, favori, archivage).
    """
    try:
        # Récupérer l'org_id depuis le slug
        supabase = get_supabase()
        try:
            org_response = supabase.table("organizations")\
                .select("id")\
                .eq("slug", org)\
                .single()\
                .execute()
        except Exception:
            raise HTTPException(status_code=404, detail="Organization not found")

        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        org_id = UUID(org_response.data["id"])

        # Mettre à jour
        updated = thread_service.update_thread(
            thread_id=thread_id,
            org_id=org_id,
            ai_status=request.ai_status,
            is_starred=request.is_starred,
            is_archived=request.is_archived
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return {
            "id": updated["id"],
            "ai_status": updated.get("ai_status"),
            "is_starred": updated.get("is_starred"),
            "is_archived": updated.get("is_archived"),
            "updated_at": updated["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Drafting Sandbox - Génération de réponses
# ============================================================================

from app.models.dossiers import DraftGenerationRequest, DraftIterationRequest, DraftSmartChipAction
from app.services.drafting_service import drafting_service

@router.post("/{org}/email-threads/{thread_id}/draft")
async def generate_draft(
    org: str,
    thread_id: UUID,
    request: DraftGenerationRequest,
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Génère un draft de réponse à un thread (Drafting Sandbox).
    
    Cet endpoint ne pollue pas le chat - c'est un espace isolé pour rédiger.
    """
    try:
        supabase = get_supabase()
        org_response = supabase.table("organizations")\
            .select("id")\
            .eq("slug", org)\
            .single()\
            .execute()
        
        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org_id = UUID(org_response.data["id"])
        
        draft = await drafting_service.generate_draft(
            thread_id=thread_id,
            org_id=org_id,
            request=request
        )
        
        return draft
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{org}/email-threads/{thread_id}/draft/{draft_id}")
async def iterate_draft(
    org: str,
    thread_id: UUID,
    draft_id: str,
    request: DraftIterationRequest,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """
    Itère sur un draft existant (Petit Prompt).
    
    Modifie le contenu selon l'instruction utilisateur sans créer 
    de nouveau message dans le chat.
    """
    try:
        result = await drafting_service.iterate_draft(request)
        return result
        
    except Exception as e:
        logger.error(f"Error iterating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{org}/email-threads/{thread_id}/draft/{draft_id}/smart-chip")
async def apply_smart_chip(
    org: str,
    thread_id: UUID,
    draft_id: str,
    action: DraftSmartChipAction,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """
    Applique une action Smart Chip (Plus court, Plus poli, etc.).
    """
    try:
        result = await drafting_service.apply_smart_chip(action)
        return result
        
    except Exception as e:
        logger.error(f"Error applying smart chip: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Liaison Thread ↔ Dossier
# ============================================================================

from app.models.dossiers import LinkThreadToDossierRequest, SuggestedDossier
from app.services.dossier_service import dossier_service

@router.get("/{org}/email-threads/{thread_id}/suggested-dossiers")
async def get_suggested_dossiers(
    org: str,
    thread_id: UUID,
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Suggère des dossiers existants pour ce thread (IA).
    
    Retourne les dossiers similaires basés sur client, adresse, contexte.
    """
    try:
        supabase = get_supabase()
        org_response = supabase.table("organizations")\
            .select("id")\
            .eq("slug", org)\
            .single()\
            .execute()
        
        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org_id = UUID(org_response.data["id"])
        
        suggestions = await dossier_service.suggest_dossiers_for_thread(
            thread_id=thread_id,
            org_id=org_id
        )
        
        return {
            "thread_id": str(thread_id),
            "suggestions": [s.dict() for s in suggestions],
            "has_match": len([s for s in suggestions if s.confidence > 0.7]) > 0
        }
        
    except Exception as e:
        logger.error(f"Error suggesting dossiers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{org}/email-threads/{thread_id}/link-to-dossier")
async def link_thread_to_dossier(
    org: str,
    thread_id: UUID,
    request: LinkThreadToDossierRequest,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """
    Lie un thread à un dossier (existant ou nouveau).
    """
    try:
        supabase = get_supabase()
        org_response = supabase.table("organizations")\
            .select("id")\
            .eq("slug", org)\
            .single()\
            .execute()
        
        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org_id = UUID(org_response.data["id"])
        
        dossier = dossier_service.link_thread_to_dossier(
            thread_id=thread_id,
            org_id=org_id,
            request=request
        )
        
        return {
            "success": True,
            "dossier": dossier,
            "message": f"Thread lié au dossier '{dossier.name}'"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking thread to dossier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{org}/email-threads/{thread_id}/unlink-from-dossier")
async def unlink_thread_from_dossier(
    org: str,
    thread_id: UUID,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """
    Délie un thread de son dossier.
    """
    try:
        supabase = get_supabase()
        org_response = supabase.table("organizations")\
            .select("id")\
            .eq("slug", org)\
            .single()\
            .execute()
        
        if not org_response or not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org_id = UUID(org_response.data["id"])
        
        success = dossier_service.unlink_thread_from_dossier(thread_id, org_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return {
            "success": True,
            "message": "Thread délié de son dossier"
        }
        
    except Exception as e:
        logger.error(f"Error unlinking thread from dossier: {e}")
        raise HTTPException(status_code=500, detail=str(e))
