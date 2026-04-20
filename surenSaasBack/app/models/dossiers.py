"""
Modèles Pydantic pour les Dossiers et le Drafting Sandbox.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================

class DossierStatus(str, Enum):
    """Statut possible d'un dossier."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


# ============================================================================
# DOSSIERS - Modèles Base
# ============================================================================

class DossierBase(BaseModel):
    """Champs de base pour un dossier."""
    name: str = Field(..., description="Nom du dossier/chantier")
    client_name: Optional[str] = Field(None, description="Nom du client")
    client_email: Optional[str] = Field(None, description="Email du client")
    address: Optional[str] = Field(None, description="Adresse du chantier")
    project_type: Optional[str] = Field(None, description="Type: renovation, construction, maintenance")
    budget_estimate: Optional[Decimal] = Field(None, description="Budget estimé en euros")
    deadline: Optional[date] = Field(None, description="Date butoir")


class DossierCreate(DossierBase):
    """Modèle pour créer un dossier."""
    pass


class DossierUpdate(BaseModel):
    """Modèle pour modifier un dossier (tous les champs optionnels)."""
    name: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    address: Optional[str] = None
    project_type: Optional[str] = None
    budget_estimate: Optional[Decimal] = None
    deadline: Optional[date] = None
    status: Optional[DossierStatus] = None


# ============================================================================
# DOSSIERS - Modèles Response
# ============================================================================

class DossierListItem(BaseModel):
    """Item de la liste des dossiers (vue réduite)."""
    id: UUID
    name: str
    client_name: Optional[str]
    address: Optional[str]
    status: DossierStatus
    thread_count: int
    document_count: int
    ai_summary: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class DossierDetail(DossierBase):
    """Détail complet d'un dossier."""
    id: UUID
    org_id: UUID
    company_id: Optional[UUID]
    status: DossierStatus
    ai_summary: Optional[str]
    ai_summary_updated_at: Optional[datetime]
    thread_count: int
    document_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DossierWithStats(DossierDetail):
    """Dossier avec statistiques additionnelles."""
    recent_threads: List[Dict[str, Any]] = []  # 5 derniers threads
    document_types: Dict[str, int] = {}  # { "devis": 3, "facture": 2 }


# ============================================================================
# DOSSIERS - Liaison Thread
# ============================================================================

class LinkThreadToDossierRequest(BaseModel):
    """Requête pour lier un thread à un dossier."""
    dossier_id: Optional[UUID] = Field(None, description="ID du dossier existant")
    create_new: bool = Field(False, description="Créer un nouveau dossier ?")
    new_dossier_name: Optional[str] = Field(None, description="Nom si création")


class SuggestedDossier(BaseModel):
    """Suggestion de dossier pour un thread (par IA)."""
    dossier_id: UUID
    name: str
    client_name: Optional[str]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score 0-1")
    reason: str = Field(..., description="Explication de la suggestion")


# ============================================================================
# DOSSIERS - Dashboard
# ============================================================================

class DossierDashboardSummary(BaseModel):
    """Résumé cross-threads pour le dashboard dossier."""
    dossier_id: UUID
    generated_at: datetime
    summary_text: str
    key_points: List[str]  # Points clés extraits
    pending_actions: List[str]  # Actions en attente détectées
    total_value: Optional[Decimal]  # Valeur totale des devis/factures


class DossierDocumentsView(BaseModel):
    """Vue agrégée des documents d'un dossier."""
    dossier_id: UUID
    total_documents: int
    by_type: Dict[str, List[Dict[str, Any]]]  # { "devis": [...], "facture": [...] }


class DossierTasksView(BaseModel):
    """Tâches/actions détectées par IA dans les échanges."""
    dossier_id: UUID
    tasks: List[Dict[str, Any]]  # { "description": "...", "source_thread_id": "...", "detected_at": "..." }


# ============================================================================
# DRAFTING SANDBOX - Modèles
# ============================================================================

class DraftGenerationRequest(BaseModel):
    """Requête pour générer un draft initial."""
    context_level: str = Field("full", description="full | summary | minimal")
    tone: str = Field("professional", description="professional | formal | friendly | technical")


class DraftIterationRequest(BaseModel):
    """Requête pour itérer sur un draft (Petit Prompt)."""
    current_content: str = Field(..., description="Contenu HTML actuel")
    instruction: str = Field(..., description="Instruction utilisateur")
    action: str = Field("iterate", description="iterate | apply_chip")


class DraftSmartChipAction(BaseModel):
    """Action Smart Chip prédéfinie."""
    chip_id: str = Field(..., description="shorten | formal | add_signature | technical")
    current_content: str


class DraftResponse(BaseModel):
    """Réponse contenant le draft généré."""
    draft_id: str = Field(..., description="ID temporaire du draft")
    content: str = Field(..., description="Contenu HTML généré")
    plain_text: str = Field(..., description="Version texte brut")
    suggestions: List[str] = Field(default=[], description="Suggestions de smart chips")
    generated_at: datetime
    model_used: str = Field("gemini-2.5-flash-lite", description="Modèle IA utilisé")


class DraftIterationResponse(DraftResponse):
    """Réponse après itération sur un draft."""
    changes_summary: Optional[str] = Field(None, description="Résumé des modifications")


class DraftFinalizeRequest(BaseModel):
    """Requête pour finaliser un draft."""
    draft_id: str
    action: str = Field("copy", description="copy | prepare_for_gmail")
    final_content: str


class DraftFinalizeResponse(BaseModel):
    """Réponse après finalisation."""
    success: bool
    message: str
    clipboard_content: Optional[str] = None  # Si action=copy
    gmail_draft_url: Optional[str] = None  # Si action=prepare_for_gmail


# ============================================================================
# LISTES ET PAGINATION
# ============================================================================

class DossierListResponse(BaseModel):
    """Réponse liste des dossiers avec pagination."""
    data: List[DossierListItem]
    total: int
    page: int
    limit: int


class SuggestedDossiersResponse(BaseModel):
    """Réponse suggestions de dossiers pour un thread."""
    thread_id: UUID
    suggestions: List[SuggestedDossier]
    has_match: bool  # True si au moins une suggestion > 0.7
