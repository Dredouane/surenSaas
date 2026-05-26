"""
Service de gestion des threads email et chat.

Ce service gère:
- La création et récupération des threads
- La mise à jour des métriques des threads
- La gestion des sessions de chat
- L'envoi de messages au chat IA (mocké pour l'instant)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.core.logging import get_logger
from app.api.auth import get_supabase

logger = get_logger(__name__)


class ThreadService:
    """Service de gestion des threads email."""
    
    def __init__(self):
        self.client = get_supabase()
    
    # ============================================================================
    # Threads
    # ============================================================================
    
    def list_threads(
        self,
        org_id: UUID,
        company_id: Optional[UUID] = None,
        status: Optional[str] = None,
        urgency: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Liste les threads avec filtres et pagination.
        
        Args:
            org_id: ID de l'organisation
            company_id: ID de l'entreprise (optionnel)
            status: Filtrer par ai_status
            urgency: Filtrer par ai_urgency
            search: Recherche textuelle (sujet, participants)
            page: Numéro de page
            limit: Nombre d'items par page
            
        Returns:
            {data: [...], pagination: {...}}
        """
        query = self.client.table("email_threads").select("*")
        
        # Filtres obligatoires
        query = query.eq("org_id", str(org_id))
        if company_id:
            query = query.eq("company_id", str(company_id))
        
        # Filtres optionnels
        if status:
            query = query.eq("ai_status", status)
        if urgency:
            query = query.eq("ai_urgency", urgency)
        
        # Recherche textuelle
        if search:
            # Recherche dans le sujet ou les participants
            query = query.or_(f"subject.ilike.%{search}%,participant_names.cs.{{\"{search}\"}}")
        
        # Tri par date du dernier email (plus récent d'abord)
        query = query.order("last_email_at", desc=True)
        
        # Pagination
        start = (page - 1) * limit
        end = start + limit - 1
        query = query.range(start, end)
        
        # Exécuter la requête
        response = query.execute()
        
        # Compter le total
        count_query = self.client.table("email_threads").select("count", count="exact")
        count_query = count_query.eq("org_id", str(org_id))
        if company_id:
            count_query = count_query.eq("company_id", str(company_id))
        if status:
            count_query = count_query.eq("ai_status", status)
        if urgency:
            count_query = count_query.eq("ai_urgency", urgency)
        
        count_response = count_query.execute()
        total = count_response.count
        
        return {
            "data": response.data if response.data else [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit if total else 0
            }
        }
    
    def get_thread(self, thread_id: UUID, org_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Récupère un thread par son ID avec tous ses emails.
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation (pour sécurité)
            
        Returns:
            Le thread avec ses emails, ou None si non trouvé
        """
        # Récupérer le thread
        thread_response = None
        try:
            thread_response = self.client.table("email_threads")\
                .select("*")\
                .eq("id", str(thread_id))\
                .eq("org_id", str(org_id))\
                .single()\
                .execute()
        except Exception:
            # Thread non trouvé
            pass
        
        if not thread_response or not thread_response.data:
            return None
        
        thread = thread_response.data
        
        # Récupérer les emails du thread (du plus récent au plus ancien)
        emails_response = self.client.table("emails")\
            .select("*")\
            .eq("gmail_thread_id", thread["gmail_thread_id"])\
            .eq("org_id", str(org_id))\
            .order("sent_at", desc=True)\
            .execute()
        
        emails = emails_response.data if emails_response.data else []
        
        # Exclure le wrapper de chaîne (chain_index=0) car son body contient toute
        # la chaîne non parsée — les vrais emails parsés sont chain_1..chain_N
        emails = [e for e in emails if not e.get("gmail_message_id", "").endswith("_chain_0")]
        
        # Trier: chain_1..chain_N d'abord (les vrais forwards parsés),
        # puis les emails normaux (non-chain)
        chain_emails = sorted(
            [e for e in emails if "_chain_" in e.get("gmail_message_id", "")],
            key=lambda e: e.get("sent_at", "") or "",
            reverse=True,
        )
        normal_emails = sorted(
            [e for e in emails if "_chain_" not in e.get("gmail_message_id", "")],
            key=lambda e: e.get("sent_at", "") or "",
            reverse=True,
        )
        thread["emails"] = chain_emails + normal_emails
        
        # Récupérer la session de chat par défaut
        try:
            chat_response = self.client.table("thread_chat_sessions")\
                .select("*")\
                .eq("thread_id", str(thread_id))\
                .eq("is_default", True)\
                .eq("is_active", True)\
                .maybe_single()\
                .execute()
            if chat_response and chat_response.data:
                thread["chat_session"] = chat_response.data
        except Exception:
            pass

        return thread
    
    def update_thread(
        self,
        thread_id: UUID,
        org_id: UUID,
        ai_status: Optional[str] = None,
        is_starred: Optional[bool] = None,
        is_archived: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Met à jour un thread.
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            ai_status: Nouveau statut IA
            is_starred: Favori?
            is_archived: Archivé?
            
        Returns:
            Le thread mis à jour, ou None si non trouvé
        """
        data = {}
        if ai_status is not None:
            data["ai_status"] = ai_status
        if is_starred is not None:
            data["is_starred"] = is_starred
        if is_archived is not None:
            data["is_archived"] = is_archived
        
        if not data:
            # Rien à mettre à jour
            return self.get_thread(thread_id, org_id)
        
        data["updated_at"] = datetime.utcnow().isoformat()
        
        response = self.client.table("email_threads")\
            .update(data)\
            .eq("id", str(thread_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if response.data:
            return response.data[0]
        return None
    
    def get_or_create_thread(
        self,
        org_id: UUID,
        company_id: Optional[UUID],
        gmail_thread_id: str,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Récupère un thread existant ou en crée un nouveau.
        
        Args:
            org_id: ID de l'organisation
            company_id: ID de l'entreprise
            gmail_thread_id: ID Gmail du thread
            subject: Sujet du thread
            
        Returns:
            Le thread (existant ou créé)
        """
        # Chercher le thread existant
        existing = self.client.table("email_threads")\
            .select("*")\
            .eq("org_id", str(org_id))\
            .eq("company_id", str(company_id))\
            .eq("gmail_thread_id", gmail_thread_id)\
            .maybe_single()\
            .execute()
        
        if existing and existing.data:
            return existing.data
        
        # Créer un nouveau thread
        new_thread = {
            "org_id": str(org_id),
            "company_id": str(company_id) if company_id else None,
            "gmail_thread_id": gmail_thread_id,
            "subject": subject,
            "subject_cleaned": subject,
            "ai_urgency": "medium",
            "ai_status": "new",
            "email_count": 0,
            "attachment_count": 0,
            "is_archived": False,
            "is_starred": False
        }
        
        response = self.client.table("email_threads").insert(new_thread).execute()
        
        if response.data:
            thread = response.data[0]
            # Créer la session de chat par défaut
            self._create_default_chat_session(UUID(thread["id"]), org_id, company_id)
            return thread
        
        raise Exception("Failed to create thread")
    
    def update_thread_metrics(self, thread_id: UUID) -> None:
        """
        Met à jour les métriques d'un thread (email_count, attachment_count, etc.).
        
        Args:
            thread_id: ID du thread
        """
        # Récupérer le thread pour avoir le gmail_thread_id
        thread_response = self.client.table("email_threads")\
            .select("gmail_thread_id")\
            .eq("id", str(thread_id))\
            .maybe_single()\
            .execute()
        
        if not thread_response or not thread_response.data:
            return
        
        gmail_thread_id = thread_response.data["gmail_thread_id"]
        
        # Compter les emails
        emails_count = self.client.table("emails")\
            .select("count", count="exact")\
            .eq("gmail_thread_id", gmail_thread_id)\
            .execute()
        
        # Récupérer les participants
        emails_response = self.client.table("emails")\
            .select("sender_email, sender_name, sent_at")\
            .eq("gmail_thread_id", gmail_thread_id)\
            .execute()
        
        if emails_response.data:
            emails = emails_response.data
            participant_emails = list(set([e["sender_email"] for e in emails if e["sender_email"]]))
            participant_names = list(set([e["sender_name"] for e in emails if e["sender_name"]]))
            sent_dates = [e["sent_at"] for e in emails if e["sent_at"]]
            
            # Mettre à jour le thread
            self.client.table("email_threads")\
                .update({
                    "email_count": emails_count.count,
                    "participant_emails": participant_emails,
                    "participant_names": participant_names,
                    "first_email_at": min(sent_dates) if sent_dates else None,
                    "last_email_at": max(sent_dates) if sent_dates else None,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(thread_id))\
                .execute()
    
    async def find_thread_by_semantic_similarity(
        self,
        email_id: str,
        chantier_id: str,
        org_id: str,
        similarity_threshold: float = 0.85,
    ) -> Optional[str]:
        try:
            from app.services.emails.embedding_service import embedding_service
            import numpy as np

            embedding_resp = self.client.table("email_embeddings")\
                .select("embedding")\
                .eq("email_id", email_id)\
                .eq("source_type", "email_body")\
                .limit(1)\
                .execute()

            if not embedding_resp.data:
                return None

            email_vector = embedding_resp.data[0]["embedding"]

            threads_resp = self.client.table("email_threads")\
                .select("id, gmail_thread_id, last_email_at")\
                .eq("org_id", org_id)\
                .eq("chantier_id", chantier_id)\
                .order("last_email_at", desc=True)\
                .limit(20)\
                .execute()

            if not threads_resp.data:
                return None

            best_thread_id = None
            best_score = 0.0

            for thread in threads_resp.data:
                thread_embed_resp = self.client.table("email_embeddings")\
                    .select("embedding")\
                    .eq("email_id", thread["id"])\
                    .eq("source_type", "email_body")\
                    .order("chunk_index", desc=True)\
                    .limit(1)\
                    .execute()

                if not thread_embed_resp.data:
                    continue

                thread_vector = thread_embed_resp.data[0]["embedding"]

                try:
                    v1 = np.array(email_vector)
                    v2 = np.array(thread_vector)
                    v1_norm = np.linalg.norm(v1)
                    v2_norm = np.linalg.norm(v2)
                    if v1_norm > 0 and v2_norm > 0:
                        score = float(np.dot(v1, v2) / (v1_norm * v2_norm))
                        if score > best_score:
                            best_score = score
                            best_thread_id = thread["id"]
                except Exception:
                    continue

            if best_score >= similarity_threshold and best_thread_id:
                logger.info(f"Thread similaire: {best_thread_id} (cosine={best_score:.3f})")
                return best_thread_id

        except Exception as e:
            logger.warning(f"Erreur semantic similarity: {e}")

        return None
    
    # ============================================================================
    # Chat Sessions
    # ============================================================================
    
    def _create_default_chat_session(
        self,
        thread_id: UUID,
        org_id: UUID,
        company_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """
        Crée la session de chat par défaut pour un thread.
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            company_id: ID de l'entreprise
            
        Returns:
            La session créée
        """
        session = {
            "org_id": str(org_id),
            "company_id": str(company_id) if company_id else None,
            "thread_id": str(thread_id),
            "name": "Chat principal",
            "is_default": True,
            "is_active": True,
            "rag_context": {}
        }
        
        response = self.client.table("thread_chat_sessions").insert(session).execute()
        
        if response.data:
            session_data = response.data[0]
            # Créer le message system initial avec résumé mocké
            self._create_system_summary(thread_id, UUID(session_data["id"]))
            return session_data
        
        raise Exception("Failed to create chat session")
    
    def _create_system_summary(self, thread_id: UUID, session_id: UUID) -> None:
        """
        Crée le message system initial avec résumé mocké.
        
        Args:
            thread_id: ID du thread
            session_id: ID de la session
        """
        # Récupérer les infos du thread pour le mock
        thread_data = None
        try:
            thread_response = self.client.table("email_threads")\
                .select("subject, ai_summary, ai_context, ai_urgency")\
                .eq("id", str(thread_id))\
                .maybe_single()\
                .execute()
            thread_data = thread_response.data if thread_response else None
        except Exception:
            pass
        
        subject = thread_data.get("subject", "ce dossier") if thread_data else "ce dossier"
        
        # Générer un résumé mocké si pas déjà présent
        summary = thread_data.get("ai_summary") if thread_data else None
        context = thread_data.get("ai_context") if thread_data else None
        urgency = thread_data.get("ai_urgency", "medium") if thread_data else "medium"
        
        if not summary:
            summary = f"Relance concernant {subject}"
            # Mettre à jour le thread avec le résumé mocké
            self.client.table("email_threads")\
                .update({"ai_summary": summary})\
                .eq("id", str(thread_id))\
                .execute()
        
        if not context:
            context = "Contexte en cours d'analyse..."
        
        # Créer le message system
        urgency_text = {
            "low": "Faible",
            "medium": "Moyenne",
            "high": "Élevée"
        }.get(urgency, "Moyenne")
        
        content = f"""🤖 Résumé du dossier :

De quoi s'agit-il ?
{summary}

Contexte :
{context}

Urgence : {urgency_text} {"⚠️" if urgency == "high" else ""}"""
        
        message = {
            "session_id": str(session_id),
            "role": "system",
            "content": content,
            "metadata": {
                "type": "summary",
                "urgency": urgency
            }
        }
        
        self.client.table("thread_chat_messages").insert(message).execute()
        
        # Mettre à jour le compteur de messages
        self.client.table("thread_chat_sessions")\
            .update({
                "message_count": 1,
                "last_message_at": datetime.utcnow().isoformat()
            })\
            .eq("id", str(session_id))\
            .execute()
    
    def get_chat_session(
        self,
        thread_id: UUID,
        org_id: UUID,
        session_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère une session de chat avec ses messages.

        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            session_id: ID de la session (optionnel, prend la défaut)

        Returns:
            La session avec ses messages, ou None
        """
        session_data = None

        if session_id:
            # Récupérer la session spécifique
            try:
                session_response = self.client.table("thread_chat_sessions")\
                    .select("*")\
                    .eq("id", str(session_id))\
                    .eq("thread_id", str(thread_id))\
                    .single()\
                    .execute()
                session_data = session_response.data
            except Exception:
                pass
        else:
            # Récupérer la session par défaut
            try:
                session_response = self.client.table("thread_chat_sessions")\
                    .select("*")\
                    .eq("thread_id", str(thread_id))\
                    .eq("is_default", True)\
                    .eq("is_active", True)\
                    .maybe_single()\
                    .execute()
                session_data = session_response.data
            except Exception:
                pass

            # Si pas de session par défaut, en créer une
            if not session_data:
                try:
                    thread = self.client.table("email_threads")\
                        .select("company_id")\
                        .eq("id", str(thread_id))\
                        .eq("org_id", str(org_id))\
                        .single()\
                        .execute()

                    if thread.data:
                        company_id = thread.data.get("company_id")
                        session_data = self._create_default_chat_session(thread_id, org_id, UUID(company_id) if company_id else None)
                except Exception:
                    pass

        if not session_data:
            return None

        # Récupérer les messages
        messages_response = self.client.table("thread_chat_messages")\
            .select("*")\
            .eq("session_id", session_data["id"])\
            .order("created_at", desc=False)\
            .execute()

        return {
            "session": session_data,
            "messages": messages_response.data if messages_response.data else []
        }
    
    def send_chat_message(
        self,
        thread_id: UUID,
        org_id: UUID,
        message: str,
        session_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Envoie un message au chat et récupère la réponse de l'IA (mockée).
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            message: Message de l'utilisateur
            session_id: ID de la session (optionnel)
            
        Returns:
            {user_message, assistant_message}
        """
        # Récupérer la session
        chat_data = self.get_chat_session(thread_id, org_id, session_id)
        
        if not chat_data:
            return None
        
        session = chat_data["session"]
        session_uuid = UUID(session["id"])
        
        # Créer le message utilisateur
        user_msg = {
            "session_id": session["id"],
            "role": "user",
            "content": message,
            "metadata": {}
        }
        
        user_response = self.client.table("thread_chat_messages").insert(user_msg).execute()
        user_message = user_response.data[0] if user_response.data else None
        
        # Générer la réponse avec la Secrétaire IA
        try:
            import asyncio
            import concurrent.futures
            from app.services.secretariat_service import secretariat_service
            
            # Exécuter la coroutine dans un nouveau thread pour éviter les conflits de boucle
            def run_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        secretariat_service.respond_to_chat(
                            thread_id=thread_id,
                            session_id=session_uuid,
                            user_message=message
                        )
                    )
                finally:
                    loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async)
                chat_response = future.result(timeout=30)
            
            if chat_response:
                assistant_content = chat_response.response
                metadata = {
                    "sources": chat_response.sources,
                    "confidence": chat_response.confidence,
                    "suggested_follow_up": chat_response.suggested_follow_up
                }
            else:
                assistant_content = "Je n'ai pas pu analyser votre question. Veuillez réessayer."
                metadata = {"error": "No response from secretariat"}
        except Exception as e:
            logger.error(f"Erreur appel Secrétaire: {e}")
            assistant_content = "Une erreur s'est produite. Veuillez réessayer."
            metadata = {"error": str(e)}
        
        assistant_msg = {
            "session_id": session["id"],
            "role": "assistant",
            "content": assistant_content,
            "metadata": metadata
        }
        
        assistant_response = self.client.table("thread_chat_messages").insert(assistant_msg).execute()
        assistant_message = assistant_response.data[0] if assistant_response.data else None
        
        # Mettre à jour le compteur de messages
        new_count = (session.get("message_count", 0) or 0) + 2
        self.client.table("thread_chat_sessions")\
            .update({
                "message_count": new_count,
                "last_message_at": datetime.utcnow().isoformat()
            })\
            .eq("id", session["id"])\
            .execute()
        
        return {
            "user_message": user_message,
            "assistant_message": assistant_message
        }
    
    def _generate_mock_response(self, message: str, thread_id: UUID) -> str:
        """
        Génère une réponse mockée pour le chat (sera remplacé par vrai IA plus tard).
        
        Args:
            message: Message de l'utilisateur
            thread_id: ID du thread
            
        Returns:
            Réponse mockée
        """
        message_lower = message.lower()
        
        # Quelques réponses mockées basiques
        if "montant" in message_lower or "prix" in message_lower or "€" in message_lower:
            return """Le montant mentionné dans ce thread est de **12 450 € HT**.

Source : Email du client du 28/07/2025"""
        
        if "délai" in message_lower or "date" in message_lower or "quand" in message_lower:
            return """D'après les échanges, le délai souhaité est de **3 semaines** à compter de la signature du devis.

Note : Ce délai a été mentionné dans le dernier email du client."""
        
        if "urgence" in message_lower or "urgent" in message_lower or "priorité" in message_lower:
            return """Ce dossier est marqué comme **urgent** 🔴

Le client mentionne un blocage de chantier si la réponse n'est pas donnée avant le 5 août."""
        
        if "client" in message_lower or "contact" in message_lower:
            return """Le client est **ACORUS** (contact@acorus.fr).

Historique : 5 échanges précédents avec ce client sur des chantiers similaires."""
        
        # Réponse par défaut
        return f"""J'ai analysé votre question : "{message}"

Pour l'instant, je fonctionne en mode simulation. Le vrai modèle IA sera connecté prochainement pour vous donner des réponses précises basées sur :
- L'historique de vos échanges avec ce client
- Les documents associés à ce dossier
- Les patterns identifiés dans vos emails précédents

💡 **Astuce** : Vous pouvez me demander des informations sur :
- Les montants et devis
- Les délais et dates
- L'historique client
- Les pièces jointes"""


# Instance singleton
thread_service = ThreadService()
