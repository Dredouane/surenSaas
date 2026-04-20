"""
Modèles Pydantic pour le service Secrétaire IA.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field


class EmailStatus(str, Enum):
    """Statuts possibles pour un email/thread.
    
    Doivent correspondre à la contrainte CHECK dans la DB:
    ai_status TEXT CHECK (ai_status IN ('new', 'in_progress', 'waiting', 'resolved', 'urgent', 'awaiting_response', 'awaiting_user'))
    """
    NEW = "new"                           # Nouveau, pas encore analysé
    IN_PROGRESS = "in_progress"           # En cours d'analyse par IA
    WAITING = "waiting"                   # Attente réponse/action
    RESOLVED = "resolved"                 # Traité/Résolu
    URGENT = "urgent"                     # Marqué urgent par IA
    AWAITING_RESPONSE = "awaiting_response"  # Attente réponse client
    AWAITING_USER = "awaiting_user"       # Attente action utilisateur


class EmailAnalysisResult(BaseModel):
    """Résultat de l'analyse d'un email par la Secrétaire IA."""
    status: EmailStatus = Field(..., description="Statut déterminé pour le thread")
    summary: str = Field(..., description="Résumé concis de la situation")
    context: Optional[str] = Field(None, description="Contexte important")
    key_points: List[str] = Field(default_factory=list, description="Points clés")
    suggested_actions: List[str] = Field(default_factory=list, description="Actions suggérées")
    urgency_reason: Optional[str] = Field(None, description="Raison de l'urgence si applicable")
    attachments_analysis: Optional[str] = Field(None, description="Analyse des pièces jointes")
    
    class Config:
        use_enum_values = True


class ChatResponse(BaseModel):
    """Réponse de la Secrétaire IA dans le chat."""
    response: str = Field(..., description="Réponse textuelle")
    sources: List[str] = Field(default_factory=list, description="Sources utilisées")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Niveau de confiance")
    suggested_follow_up: Optional[str] = Field(None, description="Question de suivi suggérée")


class ThreadContext(BaseModel):
    """Context complet d'un thread pour la Secrétaire."""
    thread_id: UUID
    subject: str
    email_count: int
    participant_emails: List[str]
    participant_names: List[str]
    previous_summary: Optional[str] = None
    ai_status: Optional[str] = None
    ai_urgency: Optional[str] = None


class EmailContext(BaseModel):
    """Context d'un email spécifique."""
    email_id: UUID
    role: str  # "client" ou "toi"
    sender_email: str
    sender_name: Optional[str]
    subject: str
    content: str
    sent_at: datetime
    has_attachments: bool


class AttachmentContext(BaseModel):
    """Context d'une pièce jointe."""
    attachment_id: UUID
    filename: str
    mime_type: str
    ocr_text: Optional[str]
    ocr_confidence: Optional[float]


class RAGContext(BaseModel):
    """Context RAG (emails similaires)."""
    similar_thread_id: UUID
    similarity_score: float
    summary: str


class ChatMessageContext(BaseModel):
    """Context d'un message de chat."""
    role: str
    content: str
    created_at: datetime


class SecretariatAnalysisContext(BaseModel):
    """Context complet pour l'analyse d'un nouvel email."""
    thread: ThreadContext
    current_email: EmailContext
    previous_emails: List[EmailContext]
    attachments: List[AttachmentContext]
    rag_context: List[RAGContext]


class SecretariatChatContext(BaseModel):
    """Context complet pour une réponse dans le chat."""
    thread: ThreadContext
    chat_history: List[ChatMessageContext]
    relevant_emails: List[EmailContext]
    attachments: List[AttachmentContext]
    rag_context: List[RAGContext]
    user_question: str
