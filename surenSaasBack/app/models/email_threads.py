"""
Modèles Pydantic pour le module Email Threads Management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# Modèles de base
# ============================================================================

class ParticipantInfo(BaseModel):
    """Informations sur les participants d'un thread."""
    emails: List[str] = []
    names: List[str] = []


class ThreadMetrics(BaseModel):
    """Métriques d'un thread."""
    email_count: int = 0
    attachment_count: int = 0
    first_email_at: Optional[datetime] = None
    last_email_at: Optional[datetime] = None


class ThreadFlags(BaseModel):
    """Flags d'un thread."""
    is_archived: bool = False
    is_starred: bool = False


class AIAnalysis(BaseModel):
    """Analyse IA d'un thread."""
    summary: Optional[str] = None
    context: Optional[str] = None
    urgency: str = "medium"  # low, medium, high
    status: str = "new"  # new, in_progress, waiting, resolved


# ============================================================================
# Modèles Email (dans un thread)
# ============================================================================

class AttachmentInfo(BaseModel):
    """Informations sur une pièce jointe."""
    id: UUID
    filename: str
    mime_type: str
    size: int
    preview_url: Optional[str] = None


class EmailInThread(BaseModel):
    """Email formaté pour affichage dans un thread."""
    id: UUID
    role: str  # "client" ou "toi"
    sender: Dict[str, Optional[str]]  # {email, name}
    subject: str
    content: Dict[str, Optional[str]]  # {text, html}
    sent_at: datetime
    has_attachments: bool = False
    attachments: List[AttachmentInfo] = []


# ============================================================================
# Modèles Chat
# ============================================================================

class ChatMessage(BaseModel):
    """Message dans un chat."""
    id: UUID
    role: str  # "system", "assistant", "user"
    content: str
    metadata: Dict[str, Any] = {}
    created_at: datetime


class ChatSession(BaseModel):
    """Session de chat."""
    id: UUID
    name: str
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    is_default: bool = False


class ChatSessionDetail(ChatSession):
    """Session de chat avec détails."""
    rag_context: Dict[str, Any] = {}
    created_at: datetime


# ============================================================================
# Modèles Thread (API Responses)
# ============================================================================

class ThreadListItem(BaseModel):
    """Item de la liste des threads (page liste)."""
    id: UUID
    gmail_thread_id: str
    subject: str
    subject_cleaned: Optional[str] = None
    participants: ParticipantInfo
    ai_summary: Optional[str] = None
    ai_urgency: str = "medium"
    ai_status: str = "new"
    metrics: ThreadMetrics
    flags: ThreadFlags
    is_historical_partial: bool = False  # True si historique incomplet (forward externe)
    created_at: datetime
    updated_at: datetime


class ThreadDetail(BaseModel):
    """Détail d'un thread (page détail)."""
    id: UUID
    gmail_thread_id: str
    subject: str
    subject_cleaned: Optional[str] = None
    participants: ParticipantInfo
    ai_summary: Optional[str] = None
    ai_context: Optional[str] = None
    ai_urgency: str = "medium"
    ai_status: str = "new"
    flags: ThreadFlags
    emails: List[EmailInThread] = []
    metrics: ThreadMetrics
    chat_session: Optional[ChatSession] = None
    is_historical_partial: bool = False  # True si historique incomplet
    historical_notes: Optional[str] = None  # Notes sur la reconstruction
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Modèles Request/Response
# ============================================================================

class ThreadListResponse(BaseModel):
    """Réponse de la liste des threads."""
    data: List[ThreadListItem]
    pagination: Dict[str, Any]


class ThreadChatResponse(BaseModel):
    """Réponse du chat d'un thread."""
    session: ChatSessionDetail
    messages: List[ChatMessage]


class SendChatMessageRequest(BaseModel):
    """Requête pour envoyer un message au chat."""
    message: str
    session_id: Optional[UUID] = None


class SendChatMessageResponse(BaseModel):
    """Réponse après envoi d'un message."""
    user_message: ChatMessage
    assistant_message: ChatMessage


class UpdateThreadRequest(BaseModel):
    """Requête de mise à jour d'un thread."""
    ai_status: Optional[str] = None  # new, in_progress, waiting, resolved
    is_starred: Optional[bool] = None
    is_archived: Optional[bool] = None


class UpdateThreadResponse(BaseModel):
    """Réponse de mise à jour d'un thread."""
    id: UUID
    ai_status: Optional[str] = None
    is_starred: Optional[bool] = None
    is_archived: Optional[bool] = None
    updated_at: datetime


# ============================================================================
# Modèles Internes (DB)
# ============================================================================

class ThreadCreateInternal(BaseModel):
    """Création interne d'un thread (depuis un email)."""
    org_id: UUID
    company_id: Optional[UUID]
    gmail_thread_id: str
    subject: Optional[str]
    subject_cleaned: Optional[str] = None


class ChatSessionCreateInternal(BaseModel):
    """Création interne d'une session de chat."""
    org_id: UUID
    company_id: Optional[UUID]
    thread_id: UUID
    name: str = "Chat principal"
    is_default: bool = True
