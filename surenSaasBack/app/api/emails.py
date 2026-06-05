"""
Contrôleurs API pour le module Emails.

Routes:
- POST /{org}/emails/sync : Déclencher la synchro
- GET /{org}/emails/sync-status : Statut de la synchro
- GET /{org}/emails : Lister les emails
- GET /{org}/emails/{id} : Détails d'un email
"""

import os
import json
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel, Field

from app.services.email_database_service import email_db
from app.services.emails.sync_service import sync_service
from app.services.file_storage_service import file_storage_service
from app.api.auth import get_supabase
from app.core.logging import get_logger
from fastapi.responses import RedirectResponse

logger = get_logger(__name__)

# TODO: Implémenter require_capability quand le système de capabilities sera migré
def require_capability(capability: str):
    """Dépendance temporaire pour les capabilities."""
    async def _require_capability():
        # Pour l'instant, permissif - retourner un utilisateur mock
        return {"id": "test-user", "role": "admin", "org_id": "test"}
    return _require_capability

# get_current_user n'est plus utilisé dans ce fichier
# def get_current_user():
#     """Récupère l'utilisateur courant."""
#     async def _get_current_user():
#         return {"id": "test-user", "role": "admin", "org_id": "test"}
#     return _get_current_user

router = APIRouter(prefix="/{org}/emails", tags=["emails"])


# Schemas
class EmailSyncRequest(BaseModel):
    """Requête de synchronisation des emails."""
    account_id: str = Field(..., description="ID du compte Gmail à synchroniser")
    sync_mode: str = Field(default="incremental", description="Mode: incremental ou historical")
    date_range: Optional[dict] = Field(None, description="{start_date, end_date} si mode=historical")
    max_emails: int = Field(default=1000, description="Nombre max d'emails à traiter")


class EmailSyncResponse(BaseModel):
    """Réponse de synchronisation."""
    account_id: str
    synced: int
    ignored: int
    ignored_breakdown: dict
    vectorized: int
    errors: int
    last_uid: int
    duration_seconds: int
    completed_at: datetime


class EmailSyncSingleRequest(BaseModel):
    """Requête de synchronisation d'un seul email."""
    account_id: str = Field(..., description="ID du compte Gmail")
    gmail_message_id: str = Field(..., description="ID du message Gmail à synchroniser")


class EmailSyncSingleResponse(BaseModel):
    """Réponse de synchronisation d'un seul email."""
    account_id: str
    gmail_message_id: str
    success: bool
    email_id: Optional[str] = None
    chain_email_ids: Optional[list[str]] = None
    chain_length: Optional[int] = None
    error: Optional[str] = None
    processing_status: Optional[str] = None
    duration_seconds: int
    completed_at: datetime


class EmailSyncStatus(BaseModel):
    """Statut de la synchronisation."""
    account_id: str
    status: str  # idle, syncing, error
    last_sync: Optional[datetime]
    last_sync_uid: int
    stats: dict


class EmailListParams(BaseModel):
    """Paramètres de liste des emails."""
    account_id: Optional[str] = None
    company_id: Optional[str] = None
    thread_id: Optional[str] = None
    status: Optional[str] = None
    sender: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


# Routes
@router.post("/sync", response_model=EmailSyncResponse)
async def sync_emails(
    org: str,
    request: EmailSyncRequest,
    current_user: dict = Depends(require_capability("emails:sync"))
):
    """
    Déclenche la synchronisation des emails.
    
    Lance le polling synchrone Gmail jusqu'à la vectorisation complète.
    Traitement incrémental (depuis last_uid) ou historique par période.
    """
    try:
        logger.info(f"Starting email sync for account {request.account_id}")
        
        result = await sync_service.sync_account(
            account_id=request.account_id,
            sync_mode=request.sync_mode,
            date_range=request.date_range,
            max_emails=request.max_emails
        )
        
        result["completed_at"] = datetime.utcnow()
        
        logger.info(f"Email sync completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Email sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-single", response_model=EmailSyncSingleResponse)
async def sync_single_email(
    org: str,
    request: EmailSyncSingleRequest,
    current_user: dict = Depends(require_capability("emails:sync"))
):
    """
    Synchronise un seul email spécifique par son ID Gmail.
    
    Utile pour rejouer le traitement d'un email qui a échoué.
    """
    start_time = datetime.utcnow()
    try:
        logger.info(f"Starting single email sync for message {request.gmail_message_id}")
        
        from app.services.emails.sync_service import sync_service
        from app.services.emails.gmail_client import create_gmail_client
        from app.services.emails.alias_router import alias_router
        from app.services.emails.content_cleaner import content_cleaner
        from app.services.email_database_service import email_db
        from app.services.emails.embedding_service import embedding_service
        import asyncio
        
        # 1. Récupérer les infos du compte
        account = await email_db.get_email_account(request.account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {request.account_id} not found")
        
        refresh_token = account["oauth_refresh_token"]
        
        # 2. Connecter le client Gmail
        gmail_client = create_gmail_client(refresh_token)
        await gmail_client.connect()
        
        # 3. Récupérer le message spécifique
        try:
            message = await gmail_client.get_message(request.gmail_message_id)
        except Exception as e:
            logger.error(f"Failed to fetch message {request.gmail_message_id}: {e}")
            raise HTTPException(status_code=404, detail=f"Message {request.gmail_message_id} not found or inaccessible")
        
        # 4. Extraire les headers
        headers = gmail_client.parse_headers(message)
        delivered_to = headers.get("Delivered-To", "")
        
        # 5. Routing par alias
        routing = await alias_router.route(delivered_to)
        
        if routing.routing_status != "routed":
            logger.warning(f"Message {request.gmail_message_id} ignored: {routing.routing_status}")
            duration = (datetime.utcnow() - start_time).total_seconds()
            return {
                "account_id": request.account_id,
                "gmail_message_id": request.gmail_message_id,
                "success": False,
                "error": f"Email ignored: {routing.routing_status}",
                "duration_seconds": int(duration),
                "completed_at": datetime.utcnow()
            }
        
        # 6. Vérifier si l'email existe déjà
        existing = await email_db.get_email_by_message_id(request.gmail_message_id)
        
        if existing:
            logger.info(f"Message {request.gmail_message_id} already exists, retraitement complet")
            old_email_id = existing["id"]
            
            # Supprimer l'email existant pour un retraitement complet
            await email_db.delete_email(old_email_id)
            logger.info(f"Email {old_email_id} supprimé pour retraitement")
        
        # 7. Extraire le contenu
        raw_body = gmail_client.get_body_text(message)
        raw_subject = headers.get("Subject", "")
        
        logger.info(f"🔧 Extraction email (sync-single) - Sujet: {raw_subject[:50]}...")
        
        # Détecter si c'est une chaîne de forwards
        is_chain = False
        de_count = raw_body.count("De :") + raw_body.count("From :")
        if de_count > 1:
            is_chain = True
            logger.info(f"🔗 Détecté comme CHAÎNE de forwards (sync-single): {de_count} blocs")
        
        # Utiliser le parsing .eml pour les chaînes
        if is_chain:
            logger.info("🔗 Utilisation du parsing .eml pour la chaîne (sync-single)...")
            try:
                from app.services.emails.email_chain_service import email_chain_service
                
                result = await email_chain_service.process_chain(
                    gmail_client=gmail_client,
                    gmail_message_id=request.gmail_message_id,
                    gmail_thread_id=message.get("threadId"),
                    account_id=request.account_id,
                    org_id=str(routing.org_id),
                    company_id=str(routing.company_id) if routing.company_id else None,
                    delivered_to=delivered_to,
                    routing_status=routing.routing_status,
                )
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                return {
                    "account_id": request.account_id,
                    "gmail_message_id": request.gmail_message_id,
                    "success": result["stored"],
                    "email_id": result["email_ids"][0] if result.get("email_ids") else None,
                    "chain_email_ids": result.get("email_ids", []),
                    "chain_length": result.get("chain_length", 0),
                    "duration_seconds": int(duration),
                    "completed_at": datetime.utcnow()
                }
            except Exception as chain_error:
                logger.error(f"❌ Extraction chaîne .eml échouée (sync-single): {chain_error}", exc_info=True)
                logger.info("🔧 Fallback vers extraction simple après échec chaîne .eml")
        
        # Extraction simple (pas une chaîne ou échec chaîne)
        logger.info("🔧 Utilisation du content_cleaner (regex) (sync-single)...")
        extracted = content_cleaner.extract_original(raw_body, raw_subject)
        
        logger.info(f"🔧 FIN extraction (sync-single) - Sujet extrait: {extracted.subject[:50]}...")
        
        # 8. Stocker l'email
        email_data = {
            "org_id": str(routing.org_id),
            "company_id": str(routing.company_id),
            "email_account_id": request.account_id,
            "delivered_to_alias": delivered_to,
            "routing_status": routing.routing_status,
            "gmail_thread_id": message.get("threadId"),
            "gmail_message_id": request.gmail_message_id,
            "gmail_history_id": int(message.get("historyId", 0)),
            "subject": extracted.subject if extracted.subject else raw_subject,
            "subject_cleaned": extracted.subject if extracted.subject else raw_subject,
            "sender_email": extracted.from_email or headers.get("From", ""),
            "sender_name": extracted.from_name,
            "recipient_emails": extracted.to_emails or [delivered_to],
            "sent_at": extracted.date or headers.get("Date"),
            "received_at": datetime.utcnow().isoformat(),
            "content_text": extracted.body_cleaned if extracted.body_cleaned else raw_body,
            "content_text_raw": extracted.body if extracted.body else raw_body,
            "content_html": raw_body,
            "content_cleaned_at": datetime.utcnow().isoformat(),
            "processing_status": "pending",
            "in_reply_to": extracted.in_reply_to or headers.get("In-Reply-To"),
            "references": extracted.references or ([headers["References"]] if "References" in headers else None),
            "has_attachments": False,
            "attachments_count": 0,
            "total_size_bytes": int(message.get("sizeEstimate", 0)),
            "headers": headers
        }
        
        email = await email_db.create_email(email_data)
        email_id = email["id"]
        
        # 9. Lancer la vectorisation async
        asyncio.create_task(embedding_service.vectorize_email_async(email_id))
        
        # 10. Récupérer le statut final
        updated_email = await email_db.get_email_by_id(email_id)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "account_id": request.account_id,
            "gmail_message_id": request.gmail_message_id,
            "success": True,
            "email_id": email_id,
            "processing_status": updated_email.get("processing_status", "pending"),
            "duration_seconds": int(duration),
            "completed_at": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single email sync failed: {e}")
        duration = (datetime.utcnow() - start_time).total_seconds() if 'start_time' in locals() else 0
        raise HTTPException(status_code=500, detail={
            "account_id": request.account_id,
            "gmail_message_id": request.gmail_message_id,
            "success": False,
            "error": str(e),
            "duration_seconds": int(duration),
            "completed_at": datetime.utcnow().isoformat()
        })


@router.get("/sync-status", response_model=EmailSyncStatus)
async def get_sync_status(
    org: str,
    account_id: str = Query(..., description="ID du compte email"),
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Récupère le statut de la dernière synchronisation.
    """
    try:
        # Récupérer les infos du compte
        account = await email_db.get_email_account(account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Compter les emails par statut
        emails = await email_db.list_emails({"account_id": account_id}, limit=1000)
        
        # Calculer les stats manuellement
        from collections import Counter
        status_counts = Counter(e.get("processing_status") for e in emails)
        
        # Calculer les stats
        stats = {
            "total_synced": 0,
            "total_ignored": 0,
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "vectorized": status_counts.get("vectorized", 0),
            "error": status_counts.get("error", 0)
        }
        stats["total_synced"] = stats["vectorized"] + stats["error"]
        
        # Déterminer le statut
        status = "idle"
        if stats["processing"] > 0:
            status = "syncing"
        elif stats["error"] > stats["vectorized"]:
            status = "error"
        
        return {
            "account_id": account_id,
            "status": status,
            "last_sync": account.get("last_sync_at"),
            "last_sync_uid": account.get("last_sync_uid", 0),
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_emails(
    org: str,
    account_id: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    thread_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, enum=["pending", "processing", "vectorized", "error"]),
    sender: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Liste les emails synchronisés.
    
    Filtres disponibles:
    - company_id: Filtrer par entreprise
    - thread_id: Filtrer par conversation
    - status: pending/processing/vectorized/error
    - sender: Email de l'expéditeur
    - date_from/date_to: Plage de dates
    - search: Recherche textuelle (sujet + contenu)
    """
    try:
        # Construire les filtres
        filters = {"org_id": org}
        if account_id:
            filters["account_id"] = account_id
        if company_id:
            filters["company_id"] = company_id
        if thread_id:
            filters["thread_id"] = thread_id
        if status:
            filters["status"] = status
        
        # Récupérer les emails (pour l'instant sans filtre sender/date/search)
        # Ces filtres pourraient être ajoutés au service plus tard
        emails = await email_db.list_emails(filters, limit=limit, offset=offset)
        
        # Filtrer manuellement pour sender et search si nécessaire
        if sender:
            emails = [e for e in emails if e.get("sender_email") == sender]
        if search:
            search_lower = search.lower()
            emails = [e for e in emails if search_lower in e.get("subject", "").lower() or search_lower in e.get("content_text", "").lower()]
        if date_from:
            emails = [e for e in emails if e.get("sent_at") and e["sent_at"] >= date_from]
        if date_to:
            emails = [e for e in emails if e.get("sent_at") and e["sent_at"] <= date_to]
        
        return {
            "emails": emails,
            "total": len(emails),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{email_id}")
async def get_email(
    org: str,
    email_id: str,
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Récupère les détails d'un email avec ses pièces jointes et statut d'embedding.
    """
    try:
        # Email
        email = await email_db.get_email_by_id(email_id)
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Pièces jointes
        attachments = await email_db.get_attachments_by_email(email_id)
        email["attachments"] = attachments
        
        # Statut embeddings
        embeddings = await email_db.get_embeddings_by_email(email_id)
        
        body_vectorized = any(
            e["source_type"] == "email_body" for e in embeddings
        )
        attachments_vectorized = sum(
            1 for e in embeddings if e["source_type"] == "attachment"
        )
        
        email["embeddings_status"] = {
            "total_chunks": sum(e.get("chunk_total", 1) for e in embeddings),
            "body_vectorized": body_vectorized,
            "attachments_vectorized": attachments_vectorized
        }
        
        # Thread (autres emails du même thread)
        if email.get("gmail_thread_id"):
            thread_emails = await email_db.get_emails_by_thread(
                email["gmail_thread_id"], 
                email["org_id"]
            )
            # Filtrer l'email courant
            email["thread_emails"] = [
                {
                    "id": e["id"],
                    "subject": e["subject"],
                    "sender_email": e["sender_email"],
                    "sent_at": e["sent_at"],
                    "processing_status": e["processing_status"]
                }
                for e in thread_emails if e["id"] != email_id
            ]
        
        # Pour l'affichage frontend, utiliser content_text (nettoyé) comme contenu principal
        # et garder content_html comme référence
        formatted_email = dict(email)
        
        # Si content_text existe et est différent de content_html, l'utiliser pour l'affichage
        if formatted_email.get("content_text") and formatted_email.get("content_html"):
            # Garder les deux mais indiquer quel est le contenu d'affichage
            formatted_email["display_content"] = formatted_email["content_text"]
            formatted_email["raw_html_content"] = formatted_email["content_html"]
        elif formatted_email.get("content_text"):
            formatted_email["display_content"] = formatted_email["content_text"]
        elif formatted_email.get("content_html"):
            formatted_email["display_content"] = formatted_email["content_html"]
        
        return formatted_email
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Routes pour les comptes email
@router.get("/accounts")
async def list_email_accounts(
    org: str,
    current_user: dict = Depends(require_capability("emails:read"))
):
    """Liste les comptes Gmail configurés."""
    try:
        # Récupérer l'org_id depuis le slug via le service legacy
        from app.api.auth import get_supabase
        supabase = get_supabase()
        org_response = supabase.table("organizations")\
            .select("id")\
            .eq("slug", org)\
            .single()\
            .execute()
        
        if not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org_id = org_response.data["id"]
        
        accounts = await email_db.get_email_accounts_by_org(org_id)
        
        # Filtrer les champs retournés
        return [
            {
                "id": a["id"],
                "email_address": a["email_address"],
                "email_address_display": a.get("email_address_display"),
                "is_active": a["is_active"],
                "sync_enabled": a["sync_enabled"],
                "last_sync_at": a.get("last_sync_at"),
                "created_at": a["created_at"]
            }
            for a in accounts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts")
async def create_email_account(
    org: str,
    email: str,
    oauth_code: str,
    redirect_uri: str,
    email_address_display: Optional[str] = None,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """
    Connecte un compte Gmail (OAuth2).
    
    Échange le code d'autorisation contre un refresh token.
    """
    try:
        # TODO: Implémenter le flux OAuth2 complet
        # Pour l'instant, retourner une erreur
        raise HTTPException(
            status_code=501, 
            detail="OAuth2 flow not yet implemented. Use manual token setup."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{account_id}")
async def delete_email_account(
    org: str,
    account_id: str,
    current_user: dict = Depends(require_capability("emails:write"))
):
    """Déconnecte un compte Gmail."""
    try:
        # Vérifier que le compte existe et appartient à l'org
        account_response = supabase_client.table("email_accounts")\
            .select("*")\
            .eq("id", account_id)\
            .single()\
            .execute()
        
        if not account_response.data:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Soft delete (désactiver)
        supabase_client.table("email_accounts")\
            .update({"is_active": False})\
            .eq("id", account_id)\
            .execute()
        
        return {"status": "deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Recherche Sémantique
# ============================================================================

@router.post("/search")
async def search_emails(
    org: str,
    query: str,
    company_id: Optional[str] = None,
    match_threshold: float = Query(0.7, ge=0.0, le=1.0),
    match_count: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Recherche sémantique dans les emails via embeddings.
    
    Args:
        query: Texte de recherche
        company_id: Filtrer par company (optionnel)
        match_threshold: Seuil de similarité (0.0-1.0)
        match_count: Nombre max de résultats
        
    Returns:
        Liste d'emails similaires avec score
    """
    try:
        from app.services.emails.embedding_service import embedding_service
        
        # 1. Générer l'embedding de la query
        query_embedding = await embedding_service.generate_embedding(query)
        
        # 2. Récupérer l'org_id depuis le slug
        supabase = get_supabase()
        org_response = supabase.table("organizations")\
            .select("id")\
            .eq("slug", org)\
            .single()\
            .execute()
        
        if not org_response.data:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org_id = org_response.data["id"]
        
        # 3. Recherche vectorielle
        results = await email_db.search_similar_emails(
            query_embedding=query_embedding,
            org_id=org_id,
            company_id=company_id,
            match_threshold=match_threshold,
            match_count=match_count
        )
        
        # 3. Formater les résultats
        formatted_results = []
        for r in results:
            formatted_results.append({
                "email_id": r.get("email_id"),
                "subject": r.get("subject"),
                "sender_email": r.get("sender_email"),
                "content_preview": r.get("content_chunk", "")[:200] + "...",
                "similarity_score": r.get("similarity"),
                "sent_at": r.get("sent_at"),
                "source_type": r.get("source_type")  # email_body ou attachment
            })
        
        return {
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Téléchargement des pièces jointes
# ============================================================================

@router.get("/{email_id}/attachments/{attachment_id}/download")
async def download_email_attachment(
    org: str,
    email_id: str,
    attachment_id: str,
    current_user: dict = Depends(require_capability("emails:read"))
):
    """
    Télécharge une pièce jointe d'email.
    
    Retourne une redirection 302 vers une URL signée R2 valide 1 heure.
    """
    try:
        # Récupérer l'attachment depuis la DB
        supabase = get_supabase()
        
        # Récupérer l'attachment avec vérification qu'il appartient bien à l'email
        attachment_result = supabase.table("email_attachments")\
            .select("*, emails!inner(org_id)")\
            .eq("id", attachment_id)\
            .eq("email_id", email_id)\
            .single()\
            .execute()
        
        if not attachment_result.data:
            raise HTTPException(status_code=404, detail="Pièce jointe non trouvée")
        
        attachment = attachment_result.data
        
        # Vérifier que l'email appartient à l'org de l'utilisateur
        # Note: org_id vient de la table emails via la jointure
        attachment_org_id = attachment.get("emails", {}).get("org_id")
        user_org_id = current_user.get("org_id")
        
        if str(attachment_org_id) != str(user_org_id):
            logger.warning(
                f"🚫 Tentative d'accès non autorisé à la PJ\n"
                f"   User: {current_user.get('email')} (org: {user_org_id})\n"
                f"   Attachment org: {attachment_org_id}"
            )
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette pièce jointe")
        
        # Récupérer le storage_path
        storage_path = attachment.get("storage_path")
        if not storage_path:
            raise HTTPException(status_code=404, detail="Fichier non disponible (storage_path manquant)")
        
        # Vérifier que le fichier existe sur R2
        exists = await file_storage_service.file_exists(storage_path)
        if not exists:
            logger.warning(f"⚠️ Fichier R2 non trouvé: {storage_path}")
            raise HTTPException(status_code=404, detail="Fichier non trouvé sur le stockage")
        
        # Générer URL signée avec nom de fichier original
        filename = attachment.get("filename")
        download_url = await file_storage_service.get_presigned_url(
            key=storage_path,
            filename=filename,
            expires=3600
        )
        
        logger.info(
            f"📥 Téléchargement PJ email\n"
            f"   User: {current_user.get('email')}\n"
            f"   Attachment: {filename}\n"
            f"   Email: {email_id}"
        )
        
        # Rediriger vers l'URL signée R2
        return RedirectResponse(url=download_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement PJ: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du téléchargement: {str(e)}")


# ============================================================================
# Endpoint Hermès : emails non dispatchés
# ============================================================================

hermes_router = APIRouter(prefix="/api/v1", tags=["hermes"])


@hermes_router.get("/emails/unread")
async def get_unread_emails(
    org_id: str = Query(...),
    x_api_key: str = Header(None, alias="X-API-Key"),
    limit: int = Query(20, ge=1, le=100),
):
    """Retourne les emails vectorisés non encore dispatchés par Hermès.

    Format attendu par Hermès :
    [{ "id": "...", "from": "...", "subject": "...", "body": "...", "date": "...", "attachments": [...] }]
    """
    from app.api.tools_rest import verify_tools_api_key
    verify_tools_api_key(x_api_key)

    sb = get_supabase()

    result = sb.table("emails").select(
        "id, gmail_message_id, subject, sender_email, sender_name, "
        "content_text, content_text_raw, sent_at, received_at, "
        "has_attachments, attachments_count, gmail_thread_id"
    ).eq("org_id", org_id).eq("processing_status", "vectorized")\
     .order("received_at", desc=True).limit(limit).execute()

    emails = result.data or []

    # Filtrer ceux qui ont déjà un log dans hermes_dispatch_log
    email_ids = [e["id"] for e in emails]
    dispatched = set()
    if email_ids:
        log_resp = sb.table("hermes_dispatch_log")\
            .select("email_id")\
            .in_("email_id", email_ids)\
            .execute()
        dispatched = {r["email_id"] for r in (log_resp.data or [])}

    unread = [e for e in emails if e["id"] not in dispatched]

    # Récupérer les pièces jointes pour chaque email
    attachment_ids = [e["id"] for e in unread]
    attachments_map = {}
    if attachment_ids:
        att_resp = sb.table("email_attachments")\
            .select("id, email_id, filename, mime_type, file_size_bytes, ocr_text")\
            .in_("email_id", attachment_ids)\
            .execute()
        for att in (att_resp.data or []):
            eid = att["email_id"]
            if eid not in attachments_map:
                attachments_map[eid] = []
            attachments_map[eid].append({
                "id": att["id"],
                "filename": att["filename"],
                "mime_type": att["mime_type"],
                "size": att.get("file_size_bytes"),
                "ocr_text": att.get("ocr_text"),
            })

    formatted = []
    for e in unread:
        formatted.append({
            "id": e["id"],
            "from": e.get("sender_email", ""),
            "from_name": e.get("sender_name", ""),
            "subject": e.get("subject", ""),
            "body": e.get("content_text_raw") or e.get("content_text", ""),
            "date": e.get("sent_at") or e.get("received_at", ""),
            "thread_id": e.get("gmail_thread_id"),
            "has_attachments": e.get("has_attachments", False),
            "attachments": attachments_map.get(e["id"], []),
        })

    return {"success": True, "count": len(formatted), "data": formatted}


# ============================================================================
# Endpoints Hermès V2 : ready-for-analysis + analysis + execute
# ============================================================================


@hermes_router.get("/emails/ready-for-analysis")
async def get_ready_for_analysis(
    org_id: str = Query(...),
    company_id: str = Query(None),
    limit: int = Query(20, ge=1, le=50),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Retourne les threads prêts pour Hermès (status = READY_FOR_AI).

    Hermès récupère les threads avec leur contexte complet :
    chantier_id, emails, pièces jointes, embeddings RAG.
    """
    from app.api.tools_rest import verify_tools_api_key
    verify_tools_api_key(x_api_key)

    sb = get_supabase()

    query = sb.table("email_threads").select(
        "id, subject, detected_chantier_id, hermes_confidence, "
        "email_count, participant_emails, first_email_at, last_email_at"
    ).eq("org_id", org_id).eq("status", "READY_FOR_AI").not_.is_("detected_chantier_id", "null")

    if company_id:
        query = query.eq("company_id", company_id)

    threads_resp = query.order("last_email_at", desc=True).limit(limit).execute()
    threads = threads_resp.data or []

    result = []
    for t in threads:
        chantier = None
        if t.get("detected_chantier_id"):
            c_resp = sb.table("chantiers").select("id, nom, ref")\
                .eq("id", t["detected_chantier_id"]).maybe_single().execute()
            if c_resp.data:
                chantier = c_resp.data

        emails_resp = sb.table("emails").select(
            "id, subject, sender_email, sender_name, content_text, sent_at, "
            "has_attachments, attachments_count"
        ).eq("gmail_thread_id", t["id"])\
         .eq("org_id", org_id)\
         .order("sent_at", desc=False)\
         .limit(20).execute()

        emails_data = []
        for e in (emails_resp.data or []):
            att_resp = sb.table("email_attachments").select(
                "id, filename, mime_type, file_size_bytes, ocr_text"
            ).eq("email_id", e["id"]).execute()

            emails_data.append({
                "id": e["id"],
                "from": e.get("sender_email", ""),
                "from_name": e.get("sender_name", ""),
                "subject": e.get("subject", ""),
                "body": e.get("content_text", ""),
                "date": e.get("sent_at", ""),
                "has_attachments": e.get("has_attachments", False),
                "attachments": [
                    {"id": a["id"], "filename": a["filename"],
                     "mime_type": a["mime_type"], "size": a.get("file_size_bytes"),
                     "ocr_text": a.get("ocr_text")}
                    for a in (att_resp.data or [])
                ],
            })

        result.append({
            "thread_id": t["id"],
            "subject": t.get("subject"),
            "chantier_id": t.get("detected_chantier_id"),
            "chantier_nom": chantier.get("nom") if chantier else None,
            "chantier_ref": chantier.get("ref") if chantier else None,
            "email_count": t.get("email_count", len(emails_data)),
            "participants": t.get("participant_emails", []),
            "first_email_at": t.get("first_email_at"),
            "last_email_at": t.get("last_email_at"),
            "emails": emails_data,
        })

    return {"success": True, "count": len(result), "data": result}


class HermesAnalysisRequest(BaseModel):
    summary: str
    detected_urgency: str = "MEDIUM"
    proposed_actions: List[dict] = []
    raw_llm_response: str = ""


@hermes_router.post("/emails/{thread_id}/analysis")
async def submit_analysis(
    thread_id: str,
    body: HermesAnalysisRequest,
    org_id: str = Query(...),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Hermès soumet son analyse d'un thread.

    Stocke dans email_ai_analysis et passe le thread en PENDING_VALIDATION.
    """
    from app.api.tools_rest import verify_tools_api_key
    verify_tools_api_key(x_api_key)

    sb = get_supabase()

    # Vérifier que le thread existe et est bien READY_FOR_AI
    thread_resp = sb.table("email_threads").select("id, status")\
        .eq("id", thread_id).eq("org_id", org_id).maybe_single().execute()

    if not thread_resp.data:
        raise HTTPException(status_code=404, detail="Thread non trouvé")

    if thread_resp.data.get("status") != "READY_FOR_AI":
        raise HTTPException(status_code=409, detail=f"Statut actuel: {thread_resp.data.get('status')}, attendu: READY_FOR_AI")

    # Valider l'urgence
    urgency = body.detected_urgency.upper()
    if urgency not in ("LOW", "MEDIUM", "HIGH"):
        urgency = "MEDIUM"

    # Insérer l'analyse
    analysis_resp = sb.table("email_ai_analysis").insert({
        "email_thread_id": thread_id,
        "summary": body.summary,
        "detected_urgency": urgency,
        "proposed_actions": [json.loads(a) if isinstance(a, str) else a for a in body.proposed_actions],
        "raw_llm_response": body.raw_llm_response,
    }).execute()

    if not analysis_resp.data:
        raise HTTPException(status_code=500, detail="Échec création analyse")

    analysis_id = analysis_resp.data[0]["id"]

    # Passer le thread en PENDING_VALIDATION
    sb.table("email_threads").update({
        "status": "PENDING_VALIDATION",
        "ai_summary": body.summary,
        "ai_urgency": urgency.lower(),
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", thread_id).execute()

    logger.info(f"[Hermès] Analyse soumise: {analysis_id} pour thread {thread_id}")

    return {
        "success": True,
        "analysis_id": analysis_id,
        "message": "Analyse enregistrée, en attente de validation humaine",
    }


class ExecuteAnalysisRequest(BaseModel):
    action: str = "accept"  # "accept" ou "reject"
    rejection_reason: str = ""


@hermes_router.post("/analysis/{analysis_id}/execute")
async def execute_analysis(
    analysis_id: str,
    body: ExecuteAnalysisRequest,
    org_id: str = Query(...),
    x_api_key: str = Header(None, alias="X-API-Key"),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    """Validation humaine d'une analyse Hermès.

    action=accept : exécute proposed_actions (dépenses, tâches, notifications)
    action=reject : marque le thread comme REJECTED
    """
    from app.api.tools_rest import verify_tools_api_key
    verify_tools_api_key(x_api_key)

    sb = get_supabase()

    # Récupérer l'analyse
    analysis_resp = sb.table("email_ai_analysis").select(
        "id, email_thread_id, proposed_actions, summary"
    ).eq("id", analysis_id).maybe_single().execute()

    if not analysis_resp.data:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")

    analysis = analysis_resp.data
    thread_id = analysis["email_thread_id"]

    # Vérifier que le thread est bien en PENDING_VALIDATION
    thread_resp = sb.table("email_threads").select("id, status, detected_chantier_id, org_id")\
        .eq("id", thread_id).maybe_single().execute()

    if not thread_resp.data:
        raise HTTPException(status_code=404, detail="Thread non trouvé")

    if thread_resp.data.get("status") != "PENDING_VALIDATION":
        raise HTTPException(status_code=409, detail=f"Statut actuel: {thread_resp.data.get('status')}, attendu: PENDING_VALIDATION")

    if body.action == "reject":
        # Rejet
        sb.table("email_ai_analysis").update({
            "validated_at": datetime.utcnow().isoformat(),
            "validated_by": x_user_id,
            "rejected_reason": body.rejection_reason,
        }).eq("id", analysis_id).execute()

        sb.table("email_threads").update({
            "status": "REJECTED",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", thread_id).execute()

        logger.info(f"[Hermès] Analyse {analysis_id} rejetée: {body.rejection_reason}")

        return {"success": True, "message": "Analyse rejetée"}

    # Acceptation : exécuter les actions
    proposed_actions = analysis.get("proposed_actions", [])
    chantier_id = thread_resp.data.get("detected_chantier_id")
    if not chantier_id:
        raise HTTPException(status_code=400, detail="Aucun chantier associé à ce thread")

    if not isinstance(proposed_actions, list):
        proposed_actions = []

    results = {"executed": [], "errors": []}

    for action in proposed_actions:
        try:
            action_type = action.get("type")
            payload = action.get("payload", {})

            if action_type == "CREATE_EXPENSE":
                from app.agents.tools.depense_tools import _create_depense_internal
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: _create_depense_internal(
                        org_id=org_id,
                        chantier_id=chantier_id,
                        description=payload.get("titre") or payload.get("description", ""),
                        montant=payload.get("montant", 0),
                        fournisseur=payload.get("fournisseur", "Email"),
                        categorie=payload.get("categorie", "autre"),
                    )
                )
                results["executed"].append({"type": "expense", "result": result.get("data", {})})

            elif action_type == "CREATE_TASK":
                from app.api.tools_rest import _manage_taches_internal
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: _manage_taches_internal(
                        org_id=org_id,
                        chantier_id=chantier_id,
                        action="create",
                        titre=payload.get("titre", "Action depuis email"),
                        description=payload.get("description", ""),
                        priorite=payload.get("priorite", "moyenne"),
                    )
                )
                results["executed"].append({"type": "task", "result": result.get("data", {})})

            elif action_type == "SEND_NOTIFICATION":
                from app.services.telegram.notification_service import NotificationService
                notif_service = NotificationService(
                    supabase_client=sb,
                    telegram_token=_get_telegram_token(),
                )
                result = await notif_service.notify_admins(
                    org_id=org_id,
                    title=payload.get("titre", "Alerte Hermès"),
                    message=payload.get("message", ""),
                    notification_type=f"hermes_{payload.get('urgence', 'info')}",
                )
                results["executed"].append({"type": "notification", "result": result})

            else:
                logger.warning(f"[Hermès] Type d'action inconnu: {action_type}")

        except Exception as e:
            logger.error(f"[Hermès] Erreur exécution action {action.get('type')}: {e}")
            results["errors"].append({"type": action.get("type"), "error": str(e)})

    # Marquer comme traité
    now = datetime.utcnow().isoformat()
    sb.table("email_ai_analysis").update({
        "validated_at": now,
        "validated_by": x_user_id,
    }).eq("id", analysis_id).execute()

    sb.table("email_threads").update({
        "status": "PROCESSED",
        "updated_at": now,
    }).eq("id", thread_id).execute()

    logger.info(f"[Hermès] Analyse {analysis_id} acceptée et exécutée")

    return {
        "success": True,
        "message": f"{len(results['executed'])} action(s) exécutée(s), {len(results['errors'])} erreur(s)",
        "results": results,
    }
