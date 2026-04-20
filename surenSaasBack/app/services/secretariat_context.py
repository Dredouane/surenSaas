"""
Context Builder pour le service Secrétaire IA.

Ce module construit les contextes formatés pour les appels à Gemini.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pathlib import Path

from app.core.logging import get_logger
from app.api.auth import get_supabase
from app.services.email_database_service import email_db
from app.models.secretariat import (
    ThreadContext, EmailContext, AttachmentContext,
    RAGContext, ChatMessageContext, SecretariatAnalysisContext,
    SecretariatChatContext
)

logger = get_logger(__name__)


class SecretariatContextBuilder:
    """Builder pour construire les contextes de la Secrétaire IA."""
    
    def __init__(self):
        self.client = get_supabase()
    
    def build_thread_context(self, thread_id: UUID) -> Optional[ThreadContext]:
        """Récupère le context d'un thread."""
        response = self.client.table("email_threads")\
            .select("*")\
            .eq("id", str(thread_id))\
            .single()\
            .execute()
        
        if not response.data:
            return None
        
        thread = response.data
        return ThreadContext(
            thread_id=thread_id,
            subject=thread.get("subject", ""),
            email_count=thread.get("email_count", 0),
            participant_emails=thread.get("participant_emails", []),
            participant_names=thread.get("participant_names", []),
            previous_summary=thread.get("ai_summary"),
            ai_status=thread.get("ai_status"),
            ai_urgency=thread.get("ai_urgency")
        )
    
    def build_email_context(self, email_id: UUID) -> Optional[EmailContext]:
        """Récupère le context d'un email spécifique."""
        response = self.client.table("emails")\
            .select("*")\
            .eq("id", str(email_id))\
            .single()\
            .execute()
        
        if not response.data:
            return None
        
        email = response.data
        return EmailContext(
            email_id=email_id,
            role="client",  # Sera déterminé plus tard
            sender_email=email.get("sender_email", ""),
            sender_name=email.get("sender_name"),
            subject=email.get("subject", ""),
            content=email.get("content_text", ""),
            sent_at=email.get("sent_at"),
            has_attachments=email.get("has_attachments", False)
        )
    
    def build_thread_emails_context(
        self,
        gmail_thread_id: str,
        org_id: UUID,
        exclude_email_id: Optional[UUID] = None
    ) -> List[EmailContext]:
        """Récupère tous les emails d'un thread sauf un (optionnel)."""
        query = self.client.table("emails")\
            .select("*")\
            .eq("gmail_thread_id", gmail_thread_id)\
            .eq("org_id", str(org_id))\
            .order("sent_at", desc=False)
        
        response = query.execute()
        
        if not response.data:
            return []
        
        emails = []
        for email in response.data:
            if exclude_email_id and email["id"] == str(exclude_email_id):
                continue
            
            emails.append(EmailContext(
                email_id=email["id"],
                role="client",  # Déterminé par comparaison
                sender_email=email.get("sender_email", ""),
                sender_name=email.get("sender_name"),
                subject=email.get("subject", ""),
                content=email.get("content_text", "")[:2000],  # Limité pour le prompt
                sent_at=email.get("sent_at"),
                has_attachments=email.get("has_attachments", False)
            ))
        
        return emails
    
    def build_attachments_context(self, email_id: UUID) -> List[AttachmentContext]:
        """Récupère les pièces jointes d'un email avec leur OCR."""
        response = self.client.table("email_attachments")\
            .select("*")\
            .eq("email_id", str(email_id))\
            .execute()
        
        if not response.data:
            return []
        
        attachments = []
        for att in response.data:
            attachments.append(AttachmentContext(
                attachment_id=att["id"],
                filename=att.get("filename", ""),
                mime_type=att.get("mime_type", ""),
                ocr_text=att.get("ocr_text", "")[:1500] if att.get("ocr_text") else None,  # Limité
                ocr_confidence=att.get("ocr_confidence")
            ))
        
        return attachments
    
    async def build_rag_context(
        self,
        email_id: UUID,
        org_id: UUID,
        limit: int = 3
    ) -> List[RAGContext]:
        """Recherche des threads similaires via embeddings."""
        # Récupérer les embeddings de l'email
        embeddings_response = self.client.table("email_embeddings")\
            .select("embedding")\
            .eq("email_id", str(email_id))\
            .eq("source_type", "email_body")\
            .limit(1)\
            .execute()
        
        if not embeddings_response.data:
            return []
        
        query_embedding = embeddings_response.data[0]["embedding"]
        
        # Recherche vectorielle
        similar = await email_db.search_similar_emails(
            query_embedding=query_embedding,
            org_id=str(org_id),
            match_threshold=0.7,
            match_count=limit
        )
        
        rag_context = []
        for item in similar:
            # Éviter le thread courant
            if item.get("email_id") == str(email_id):
                continue
            
            rag_context.append(RAGContext(
                similar_thread_id=item.get("email_id"),
                similarity_score=item.get("similarity", 0),
                summary=item.get("content_chunk", "")[:500]
            ))
        
        return rag_context
    
    def build_chat_history(
        self,
        session_id: UUID,
        limit: int = 10
    ) -> List[ChatMessageContext]:
        """Récupère l'historique des messages de chat."""
        response = self.client.table("thread_chat_messages")\
            .select("*")\
            .eq("session_id", str(session_id))\
            .order("created_at", desc=False)\
            .limit(limit)\
            .execute()
        
        if not response.data:
            return []
        
        messages = []
        for msg in response.data:
            messages.append(ChatMessageContext(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                created_at=msg.get("created_at")
            ))
        
        return messages
    
    def format_thread_context(self, thread: ThreadContext) -> str:
        """Formate le context du thread en texte."""
        lines = [
            f"Sujet: {thread.subject}",
            f"Nombre d'emails: {thread.email_count}",
            f"Participants: {', '.join(thread.participant_names) if thread.participant_names else ', '.join(thread.participant_emails)}",
        ]
        
        if thread.previous_summary:
            lines.append(f"Résumé précédent: {thread.previous_summary}")
        
        if thread.ai_status:
            lines.append(f"Statut actuel: {thread.ai_status}")
        
        if thread.ai_urgency:
            lines.append(f"Urgence: {thread.ai_urgency}")
        
        return "\n".join(lines)
    
    def format_email_context(self, email: EmailContext) -> str:
        """Formate le context d'un email en texte."""
        lines = [
            f"De: {email.sender_name or email.sender_email} <{email.sender_email}>",
            f"Date: {email.sent_at}",
            f"Sujet: {email.subject}",
            f"Contenu:\n{email.content[:1500]}",  # Limité pour le prompt
        ]
        
        if email.has_attachments:
            lines.append("(Contient des pièces jointes)")
        
        return "\n".join(lines)
    
    def format_emails_context(self, emails: List[EmailContext]) -> str:
        """Formate plusieurs emails en texte."""
        if not emails:
            return "Aucun email précédent"
        
        parts = []
        for i, email in enumerate(emails, 1):
            parts.append(f"--- Email {i} ---")
            parts.append(self.format_email_context(email))
            parts.append("")
        
        return "\n".join(parts)
    
    def format_attachments_context(self, attachments: List[AttachmentContext]) -> str:
        """Formate les pièces jointes en texte."""
        if not attachments:
            return "Aucune pièce jointe"
        
        parts = []
        for att in attachments:
            lines = [
                f"Fichier: {att.filename} ({att.mime_type})",
            ]
            if att.ocr_text:
                lines.append(f"Contenu OCR:\n{att.ocr_text[:1000]}")  # Limité
            if att.ocr_confidence:
                lines.append(f"Confiance OCR: {att.ocr_confidence:.2f}")
            parts.append("\n".join(lines))
        
        return "\n\n".join(parts)
    
    def format_rag_context(self, rag_items: List[RAGContext]) -> str:
        """Formate le context RAG en texte."""
        if not rag_items:
            return "Aucun échange similaire trouvé"
        
        parts = []
        for item in rag_items:
            parts.append(f"- Similarité {item.similarity_score:.2f}: {item.summary}")
        
        return "\n".join(parts)
    
    def format_chat_history(self, messages: List[ChatMessageContext]) -> str:
        """Formate l'historique de chat en texte."""
        if not messages:
            return "Nouvelle conversation"
        
        parts = []
        for msg in messages:
            role_label = "🤖" if msg.role == "assistant" else "👤" if msg.role == "user" else "📝"
            parts.append(f"{role_label} {msg.role.upper()}: {msg.content}")
        
        return "\n".join(parts)
    
    def load_prompt_template(self, filename: str) -> str:
        """Charge un template de prompt depuis un fichier."""
        prompt_path = Path(__file__).parent.parent / "agents" / "prompts" / "secretariat" / filename
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Erreur chargement prompt {filename}: {e}")
            # Templates par défaut en cas d'erreur
            if "system_preanalysis" in filename:
                return "Tu es une Secrétaire IA professionnelle. Analyse l'email et fournis un résumé."
            elif "user_preanalysis" in filename:
                return "{{THREAD_CONTEXT}}\n\n{{CURRENT_EMAIL}}"
            elif "system_chat" in filename:
                return "Tu es une Secrétaire IA. Réponds aux questions sur les emails."
            elif "user_chat" in filename:
                return "Question: {{USER_QUESTION}}"
            return ""
    
    async def build_preanalysis_prompt(
        self,
        thread_id: UUID,
        email_id: UUID
    ) -> tuple[str, str]:
        """Construit les prompts pour la pré-analyse."""
        # Récupérer les données
        thread = self.build_thread_context(thread_id)
        current_email = self.build_email_context(email_id)
        
        if not thread or not current_email:
            raise ValueError("Thread ou email non trouvé")
        
        # Récupérer les emails précédents du thread
        response = self.client.table("emails")\
            .select("gmail_thread_id, org_id")\
            .eq("id", str(email_id))\
            .single()\
            .execute()
        
        if not response.data:
            raise ValueError("Email non trouvé")
        
        email_data = response.data
        previous_emails = self.build_thread_emails_context(
            email_data["gmail_thread_id"],
            UUID(email_data["org_id"]),
            exclude_email_id=email_id
        )
        
        # Récupérer les pièces jointes
        attachments = self.build_attachments_context(email_id)
        
        # Récupérer le context RAG
        rag_context = await self.build_rag_context(
            email_id,
            UUID(email_data["org_id"])
        )
        
        # Formater les contextes
        thread_text = self.format_thread_context(thread)
        current_email_text = self.format_email_context(current_email)
        previous_emails_text = self.format_emails_context(previous_emails)
        attachments_text = self.format_attachments_context(attachments)
        rag_text = self.format_rag_context(rag_context)
        
        # Assembler le context complet du thread
        full_thread_context = f"""{thread_text}

EMAILS PRÉCÉDENTS:
{previous_emails_text}"""
        
        # Charger les templates
        system_prompt = self.load_prompt_template("system_preanalysis.txt")
        user_template = self.load_prompt_template("user_preanalysis.txt")
        
        # Remplacer les placeholders
        user_prompt = user_template\
            .replace("{{THREAD_CONTEXT}}", full_thread_context)\
            .replace("{{CURRENT_EMAIL}}", current_email_text)\
            .replace("{{ATTACHMENTS_CONTEXT}}", attachments_text)\
            .replace("{{RAG_CONTEXT}}", rag_text)
        
        return system_prompt, user_prompt
    
    async def build_chat_prompt(
        self,
        thread_id: UUID,
        session_id: UUID,
        user_question: str
    ) -> tuple[str, str]:
        """Construit les prompts pour le chat."""
        # Récupérer les données
        thread = self.build_thread_context(thread_id)
        
        if not thread:
            raise ValueError("Thread non trouvé")
        
        # Récupérer le thread complet
        thread_data = self.client.table("email_threads")\
            .select("gmail_thread_id, org_id")\
            .eq("id", str(thread_id))\
            .single()\
            .execute()
        
        if not thread_data.data:
            raise ValueError("Thread non trouvé")
        
        # Récupérer tous les emails du thread
        emails = self.build_thread_emails_context(
            thread_data.data["gmail_thread_id"],
            UUID(thread_data.data["org_id"])
        )
        
        # Récupérer l'historique de chat
        chat_history = self.build_chat_history(session_id)
        
        # Récupérer les pièces jointes de tous les emails
        all_attachments = []
        for email in emails[-3:]:  # Seulement les 3 derniers emails
            attachments = self.build_attachments_context(email.email_id)
            all_attachments.extend(attachments)
        
        # Récupérer le context RAG (depuis le dernier email)
        rag_context = []
        if emails:
            rag_context = await self.build_rag_context(
                emails[-1].email_id,
                UUID(thread_data.data["org_id"]),
                limit=2
            )
        
        # Formater les contextes
        thread_text = self.format_thread_context(thread)
        emails_text = self.format_emails_context(emails[-5:])  # 5 derniers emails
        attachments_text = self.format_attachments_context(all_attachments)
        chat_history_text = self.format_chat_history(chat_history)
        rag_text = self.format_rag_context(rag_context)
        
        # Charger les templates
        system_prompt = self.load_prompt_template("system_chat.txt")
        user_template = self.load_prompt_template("user_chat.txt")
        
        # Remplacer les placeholders
        user_prompt = user_template\
            .replace("{{THREAD_SUMMARY}}", thread_text)\
            .replace("{{CHAT_HISTORY}}", chat_history_text)\
            .replace("{{EMAILS_CONTEXT}}", emails_text)\
            .replace("{{ATTACHMENTS_CONTEXT}}", attachments_text)\
            .replace("{{RAG_CONTEXT}}", rag_text)\
            .replace("{{USER_QUESTION}}", user_question)
        
        return system_prompt, user_prompt


# Instance singleton
context_builder = SecretariatContextBuilder()
