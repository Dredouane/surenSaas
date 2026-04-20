"""
Service Secrétaire IA.

Ce service gère:
1. La pré-analyse des emails (trigger: après vectorisation)
2. Les réponses dans le chat (trigger: message utilisateur)
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.config import settings
from app.api.auth import get_supabase
from app.agents.base.gemini_client import GeminiClient
from app.services.secretariat_context import context_builder
from app.models.secretariat import (
    EmailAnalysisResult, ChatResponse, EmailStatus
)

logger = get_logger(__name__)


class SecretariatService:
    """Service principal de la Secrétaire IA."""
    
    def __init__(self):
        self.client = get_supabase()
        self._gemini_client: Optional[GeminiClient] = None
    
    def _get_gemini_client(self) -> GeminiClient:
        """Initialise et retourne le client Gemini (lazy loading)."""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model=settings.secretariat_model,
                temperature=0.3,  # Légèrement créatif mais cohérent
                max_output_tokens=4096
            )
        return self._gemini_client
    
    async def analyze_new_email(self, email_id: str) -> Optional[EmailAnalysisResult]:
        """
        Analyse un nouvel email et met à jour le thread.
        
        Cette méthode est appelée de manière asynchrone après la vectorisation.
        
        Args:
            email_id: ID de l'email à analyser
            
        Returns:
            Résultat de l'analyse ou None en cas d'erreur
        """
        try:
            logger.info(f"🤖 Secrétaire: Début analyse email {email_id}")
            
            # Récupérer l'email
            email_response = self.client.table("emails")\
                .select("*")\
                .eq("id", email_id)\
                .single()\
                .execute()
            
            if not email_response.data:
                logger.error(f"Email {email_id} non trouvé")
                return None
            
            email_data = email_response.data
            
            # Récupérer le thread via gmail_thread_id
            gmail_thread_id = email_data.get("gmail_thread_id")
            org_id = email_data.get("org_id")
            company_id = email_data.get("company_id")
            
            if not gmail_thread_id:
                logger.error(f"gmail_thread_id non trouvé pour l'email {email_id}")
                return None
            
            # Chercher le thread
            thread_response = self.client.table("email_threads")\
                .select("id")\
                .eq("gmail_thread_id", gmail_thread_id)\
                .eq("org_id", org_id)\
                .maybe_single()\
                .execute()
            
            if not thread_response.data:
                # Créer le thread s'il n'existe pas
                logger.info(f"Création du thread pour gmail_thread_id {gmail_thread_id}")
                from app.services.email_thread_service import thread_service
                thread_data = thread_service.get_or_create_thread(
                    org_id=UUID(org_id),
                    company_id=UUID(company_id) if company_id else None,
                    gmail_thread_id=gmail_thread_id,
                    subject=email_data.get("subject")
                )
                thread_id = thread_data["id"]
            else:
                thread_id = thread_response.data["id"]
            
            if not thread_id:
                logger.error(f"Thread non trouvé pour l'email {email_id}")
                return None
            
            # Marquer le thread comme "en cours d'analyse"
            self.client.table("email_threads")\
                .update({
                    "ai_status": EmailStatus.IN_PROGRESS,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", thread_id)\
                .execute()
            
            # Construire les prompts
            system_prompt, user_prompt = await context_builder.build_preanalysis_prompt(
                UUID(thread_id),
                UUID(email_id)
            )
            
            # Appeler Gemini
            gemini = self._get_gemini_client()
            
            # Créer le contenu avec system + user
            from google.genai import types
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")
                    ]
                )
            ]
            
            config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
            
            response = gemini._client.models.generate_content(
                model=gemini.model_name,
                contents=contents,
                config=config
            )
            
            # Parser la réponse JSON
            try:
                result_data = json.loads(response.text)
                result = EmailAnalysisResult(**result_data)
            except Exception as e:
                logger.error(f"Erreur parsing réponse Gemini: {e}")
                logger.error(f"Réponse reçue: {response.text[:500]}")
                # Fallback
                result = EmailAnalysisResult(
                    status=EmailStatus.NEW,
                    summary="Analyse en cours...",
                    context="L'analyse automatique est en cours.",
                    key_points=["Email reçu", "À analyser"],
                    suggested_actions=["Consulter le dossier"]
                )
            
            # Mettre à jour le thread avec les résultats
            self._update_thread_after_analysis(thread_id, result)
            
            # Créer ou mettre à jour le message dans le chat
            await self._update_chat_summary(thread_id, result)
            
            logger.info(f"✅ Secrétaire: Analyse terminée pour email {email_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur analyse email {email_id}: {e}")
            # Marquer comme erreur mais ne pas bloquer
            try:
                self.client.table("emails")\
                    .update({
                        "processing_status": "error",
                        "processing_error": str(e)[:500]
                    })\
                    .eq("id", email_id)\
                    .execute()
            except:
                pass
            return None
    
    def _update_thread_after_analysis(
        self,
        thread_id: str,
        result: EmailAnalysisResult
    ):
        """Met à jour le thread avec les résultats de l'analyse."""
        # result.status est déjà une chaîne (use_enum_values = True)
        # Mapper les statuts pour être compatible avec la contrainte DB
        # La DB accepte: 'new', 'in_progress', 'waiting', 'resolved'
        original_status = result.status
        status_mapping = {
            "awaiting_response": "waiting",
            "awaiting_user": "waiting",
            "in_analysis": "in_progress",
            "urgent": "waiting",  # L'urgence est gérée via ai_urgency = 'high'
            "escalated": "waiting"
        }
        status_value = status_mapping.get(original_status, original_status)
        
        # Déterminer l'urgence en fonction du statut original
        is_urgent = original_status == "urgent" or result.urgency_reason is not None
        
        update_data = {
            "ai_summary": result.summary,
            "ai_context": result.context,
            "ai_status": status_value,
            "ai_urgency": "high" if is_urgent else "medium",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.client.table("email_threads")\
            .update(update_data)\
            .eq("id", thread_id)\
            .execute()
    
    async def _update_chat_summary(self, thread_id: str, result: EmailAnalysisResult):
        """Crée ou met à jour le résumé dans le chat du thread."""
        try:
            # Chercher la session de chat par défaut
            try:
                session_response = self.client.table("thread_chat_sessions")\
                    .select("id, message_count")\
                    .eq("thread_id", thread_id)\
                    .eq("is_default", True)\
                    .eq("is_active", True)\
                    .maybe_single()\
                    .execute()
            except Exception as e:
                logger.warning(f"Erreur recherche session: {e}")
                session_response = None
            
            if not session_response or not session_response.data:
                # Créer une session par défaut
                thread_data = self.client.table("email_threads")\
                    .select("org_id, company_id")\
                    .eq("id", thread_id)\
                    .single()\
                    .execute()
                
                if not thread_data.data:
                    return
                
                session_insert = self.client.table("thread_chat_sessions")\
                    .insert({
                        "org_id": thread_data.data["org_id"],
                        "company_id": thread_data.data.get("company_id"),
                        "thread_id": thread_id,
                        "name": "Chat principal",
                        "is_default": True,
                        "is_active": True,
                        "rag_context": {}
                    })\
                    .execute()
                
                if not session_insert or not session_insert.data:
                    logger.warning(f"Impossible de créer la session de chat pour thread {thread_id}")
                    return
                
                session_id = session_insert.data[0]["id"]
                is_first_message = True
            else:
                session_id = session_response.data["id"]
                is_first_message = session_response.data.get("message_count", 0) == 0
            
            # Construire le message de résumé
            urgency_emoji = "🔴" if result.status == "urgent" else "🟢"
            
            content_lines = [
                f"{urgency_emoji} **Résumé du dossier**",
                "",
                f"**Statut:** {result.status}",
                "",
                f"**De quoi s'agit-il ?**",
                result.summary,
            ]
            
            if result.context:
                content_lines.extend([
                    "",
                    f"**Contexte:**",
                    result.context
                ])
            
            if result.key_points:
                content_lines.extend([
                    "",
                    f"**Points clés:**",
                    *[f"• {point}" for point in result.key_points]
                ])
            
            if result.suggested_actions:
                content_lines.extend([
                    "",
                    f"**Actions suggérées:**",
                    *[f"→ {action}" for action in result.suggested_actions]
                ])
            
            if result.urgency_reason:
                content_lines.extend([
                    "",
                    f"⚠️ **Urgence:** {result.urgency_reason}"
                ])
            
            content = "\n".join(content_lines)
            
            # Si c'est le premier message, créer un message system
            if is_first_message:
                message_data = {
                    "session_id": session_id,
                    "role": "system",
                    "content": content,
                    "metadata": {
                        "type": "summary",
                        "status": result.status,
                        "auto_generated": True
                    }
                }
                
                self.client.table("thread_chat_messages")\
                    .insert(message_data)\
                    .execute()
                
                # Mettre à jour le compteur
                self.client.table("thread_chat_sessions")\
                    .update({
                        "message_count": 1,
                        "last_message_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", session_id)\
                    .execute()
            else:
                # Mettre à jour le message system existant
                existing_msg = self.client.table("thread_chat_messages")\
                    .select("id")\
                    .eq("session_id", session_id)\
                    .eq("role", "system")\
                    .order("created_at", desc=False)\
                    .limit(1)\
                    .execute()
                
                if existing_msg.data:
                    self.client.table("thread_chat_messages")\
                        .update({
                            "content": content,
                            "metadata": {
                                "type": "summary",
                                "status": result.status,
                                "auto_generated": True,
                                "updated_at": datetime.utcnow().isoformat()
                            }
                        })\
                        .eq("id", existing_msg.data[0]["id"])\
                        .execute()
                else:
                    # Créer un nouveau message system si inexistant
                    message_data = {
                        "session_id": session_id,
                        "role": "system",
                        "content": content,
                        "metadata": {
                            "type": "summary",
                            "status": result.status,
                            "auto_generated": True
                        }
                    }
                    
                    self.client.table("thread_chat_messages")\
                        .insert(message_data)\
                        .execute()
        
        except Exception as e:
            import traceback
            logger.error(f"Erreur mise à jour chat summary: {e}")
            logger.error(traceback.format_exc())
    
    async def respond_to_chat(
        self,
        thread_id: UUID,
        session_id: UUID,
        user_message: str
    ) -> Optional[ChatResponse]:
        """
        Génère une réponse à une question dans le chat.
        
        Args:
            thread_id: ID du thread
            session_id: ID de la session de chat
            user_message: Message de l'utilisateur
            
        Returns:
            Réponse de la Secrétaire ou None
        """
        try:
            logger.info(f"🤖 Secrétaire: Réponse à question dans thread {thread_id}")
            
            # Construire les prompts
            system_prompt, user_prompt = await context_builder.build_chat_prompt(
                thread_id,
                session_id,
                user_message
            )
            
            # Appeler Gemini
            gemini = self._get_gemini_client()
            
            from google.genai import types
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")
                    ]
                )
            ]
            
            config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
            
            response = gemini._client.models.generate_content(
                model=gemini.model_name,
                contents=contents,
                config=config
            )
            
            # Parser la réponse
            try:
                result_data = json.loads(response.text)
                return ChatResponse(**result_data)
            except Exception as e:
                logger.error(f"Erreur parsing réponse chat: {e}")
                # Fallback
                return ChatResponse(
                    response="Je n'ai pas pu analyser votre question. Pourriez-vous la reformuler ?",
                    sources=[],
                    confidence=0.0,
                    suggested_follow_up=None
                )
        
        except Exception as e:
            logger.error(f"❌ Erreur réponse chat: {e}")
            return ChatResponse(
                response="Une erreur s'est produite. Veuillez réessayer.",
                sources=[],
                confidence=0.0,
                suggested_follow_up=None
            )


# Instance singleton
secretariat_service = SecretariatService()
