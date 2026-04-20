"""
Modèles Pydantic pour le Module AO (Appels d'Offres).

Ce module gère les candidatures aux appels d'offres BTP, avec support pour :
- La gestion des documents (RC, BPU, CCTP, Mémoire...)
- L'extraction automatique de données par IA
- L'analyse comparative de pricing
- La rédaction assistée du mémoire technique
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

class AOStatut(str, Enum):
    """Statut d'une candidature."""
    EN_COURS = "en_cours"
    GAGNE = "gagne"
    PERDU = "perdu"
    ABANDONNE = "abandonne"


class AODocumentType(str, Enum):
    """Types de documents dans le module AO."""
    RC = "RC"                           # Règlement de Consultation
    CCTP = "CCTP"                       # Cahier des Clauses Techniques Particulières
    BPU = "BPU"                         # Bordereau des Prix Unitaires
    DAO = "DAO"                         # Dossier d'Appel d'Offres
    MEMOIRE = "MEMOIRE"                 # Mémoire Technique
    DQE = "DQE"                         # Devis Quantitatif Estimatif
    GARANTIE = "GARANTIE"               # Caution, garanties
    REJET = "REJET"                     # Rapport de rejet
    ATTRIBUE = "ATTRIBUE"               # Décision d'attribution
    NEGOCIATION = "NEGociation"         # CR de négociation
    AUTRE = "AUTRE"                     # Autre document


class AOTraitementStatus(str, Enum):
    """Statut de traitement d'un document."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class AOLensType(str, Enum):
    """Types de Lentilles d'analyse IA."""
    PRICING = "pricing"
    REDACTION = "redaction"
    RISQUE = "risque"
    COMPARAISON = "comparaison"
    OPPORTUNITE = "opportunite"


class AOValidationStatus(str, Enum):
    """Statut de validation humaine."""
    PENDING = "pending"
    VALIDE = "valide"
    REJETE = "rejete"
    PARTIEL = "partiel"


# ============================================================================
# BASE MODELS
# ============================================================================

class AOCandidatureBase(BaseModel):
    """Champs de base pour une candidature."""
    nom_projet: str = Field(..., description="Nom du projet")
    client_nom: Optional[str] = Field(None, description="Nom du maître d'ouvrage")
    reference_ao: Optional[str] = Field(None, description="Référence de l'appel d'offres")
    description: Optional[str] = Field(None, description="Description du projet")
    
    # Dates
    date_depot: Optional[date] = Field(None, description="Date de dépôt des plis")
    date_ouverture: Optional[date] = Field(None, description="Date d'ouverture des plis")
    date_notification: Optional[date] = Field(None, description="Date de notification")
    date_limite_remise: Optional[date] = Field(None, description="Date limite de remise")
    
    # Données financières
    montant_total: Optional[Decimal] = Field(None, description="Montant total candidature")
    montant_maximum: Optional[Decimal] = Field(None, description="Montant maximum accepté")
    monnaie: str = Field("EUR", description="Code devise")
    
    # Planning
    duree_travaux_jours: Optional[int] = Field(None, description="Durée travaux en jours")
    date_debut_previsionnelle: Optional[date] = None
    date_fin_previsionnelle: Optional[date] = None


class AODocumentBase(BaseModel):
    """Champs de base pour un document."""
    type_doc: AODocumentType
    sous_type: Optional[str] = Field(None, description="Précision du type")
    nom_fichier: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AOPostePricingBase(BaseModel):
    """Champs de base pour un poste de pricing."""
    numero: str = Field(..., description="Numéro de poste (ex: 01.01.001)")
    description: str
    unite: Optional[str] = None
    quantite: Optional[Decimal] = None
    prix_unitaire_ht: Optional[Decimal] = None
    prix_total_ht: Optional[Decimal] = None
    categorie: Optional[str] = Field(None, description="GROS_OEUVRE, SECOND_OEUVRE...")
    sous_categorie: Optional[str] = None


# ============================================================================
# CREATE MODELS
# ============================================================================

class AOCandidatureCreate(AOCandidatureBase):
    """Modèle pour créer une candidature."""
    dossier_id: Optional[UUID] = Field(None, description="ID du dossier lié")
    company_id: Optional[UUID] = None


class AODocumentCreate(AODocumentBase):
    """Modèle pour créer un document."""
    candidature_id: UUID
    url_stockage: Optional[str] = None
    mime_type: Optional[str] = None
    taille_bytes: Optional[int] = None


class AOPostePricingCreate(AOPostePricingBase):
    """Modèle pour créer un poste de pricing."""
    candidature_id: UUID
    document_id: UUID
    ligne_bpu: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# UPDATE MODELS
# ============================================================================

class AOCandidatureUpdate(BaseModel):
    """Modèle pour modifier une candidature."""
    nom_projet: Optional[str] = None
    client_nom: Optional[str] = None
    reference_ao: Optional[str] = None
    description: Optional[str] = None
    statut: Optional[AOStatut] = None
    
    date_depot: Optional[date] = None
    date_ouverture: Optional[date] = None
    date_notification: Optional[date] = None
    date_limite_remise: Optional[date] = None
    
    montant_total: Optional[Decimal] = None
    montant_maximum: Optional[Decimal] = None
    
    duree_travaux_jours: Optional[int] = None
    date_debut_previsionnelle: Optional[date] = None
    date_fin_previsionnelle: Optional[date] = None
    
    ai_summary: Optional[str] = None
    ai_score_gagner: Optional[float] = None


class AODocumentUpdate(BaseModel):
    """Modèle pour modifier un document."""
    type_doc: Optional[AODocumentType] = None
    sous_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    statut_traitement: Optional[AOTraitementStatus] = None
    message_erreur: Optional[str] = None


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class AOCandidatureListItem(BaseModel):
    """Item de liste des candidatures (vue réduite)."""
    id: UUID
    nom_projet: str
    client_nom: Optional[str]
    reference_ao: Optional[str]
    statut: AOStatut
    montant_total: Optional[Decimal]
    date_depot: Optional[date]
    date_limite_remise: Optional[date]
    ai_score_gagner: Optional[float]
    document_count: int
    poste_count: int
    dossier_id: Optional[UUID]
    dossier_name: Optional[str]
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AOCandidatureDetail(AOCandidatureBase):
    """Détail complet d'une candidature."""
    id: UUID
    org_id: UUID
    dossier_id: Optional[UUID]
    dossier_name: Optional[str]
    company_id: Optional[UUID]
    statut: AOStatut
    
    # IA
    ai_summary: Optional[str]
    ai_keywords: Optional[List[str]]
    ai_score_gagner: Optional[float]
    
    # Compteurs
    document_count: int
    poste_count: int
    
    # Métadonnées
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AOCandidatureWithStats(AOCandidatureDetail):
    """Candidature avec statistiques détaillées."""
    documents: List[Dict[str, Any]] = []
    stats_pricing: Dict[str, Any] = {}


class AODocumentListItem(BaseModel):
    """Item de liste des documents."""
    id: UUID
    type_doc: AODocumentType
    sous_type: Optional[str]
    nom_fichier: str
    statut_traitement: AOTraitementStatus
    taille_bytes: Optional[int]
    metadata: Dict[str, Any]
    date_extraction: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AODocumentDetail(AODocumentBase):
    """Détail complet d'un document."""
    id: UUID
    candidature_id: UUID
    org_id: UUID
    url_stockage: Optional[str]
    mime_type: Optional[str]
    taille_bytes: Optional[int]
    checksum: Optional[str]
    contenu_texte: Optional[str]
    nombre_pages: Optional[int]
    statut_traitement: AOTraitementStatus
    message_erreur: Optional[str]
    date_extraction: Optional[datetime]
    model_extraction: Optional[str]
    uploaded_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AOPostePricingListItem(BaseModel):
    """Item de liste des postes pricing."""
    id: UUID
    numero: str
    description: str
    unite: Optional[str]
    quantite: Optional[Decimal]
    prix_unitaire_ht: Optional[Decimal]
    prix_total_ht: Optional[Decimal]
    categorie: Optional[str]
    
    class Config:
        from_attributes = True


class AOPostePricingDetail(AOPostePricingBase):
    """Détail complet d'un poste pricing."""
    id: UUID
    candidature_id: UUID
    document_id: UUID
    description_normalisee: Optional[str]
    prix_unitaire_reference: Optional[Decimal]
    ecart_reference_pct: Optional[Decimal]
    ligne_bpu: Optional[int]
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AOEmbeddingItem(BaseModel):
    """Item d'embedding vectoriel."""
    id: UUID
    doc_id: UUID
    content: str
    tags: List[str]
    chunk_index: int
    chunk_total: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AOAnalyseListItem(BaseModel):
    """Item de liste des analyses."""
    id: UUID
    lens_type: AOLensType
    score_confiance: Optional[float]
    validation_humain: AOValidationStatus
    valide_par: Optional[UUID]
    date_validation: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AOAnalyseDetail(BaseModel):
    """Détail complet d'une analyse."""
    id: UUID
    candidature_id: UUID
    lens_type: AOLensType
    prompt_version: Optional[str]
    contexte: Dict[str, Any]
    documents_analyses: List[UUID]
    resultat: Dict[str, Any]
    score_confiance: Optional[float]
    validation_humain: AOValidationStatus
    valide_par: Optional[UUID]
    date_validation: Optional[datetime]
    commentaire_validation: Optional[str]
    tokens_input: Optional[int]
    tokens_output: Optional[int]
    duree_ms: Optional[int]
    model_utilise: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# REQUEST MODELS (API)
# ============================================================================

class AOIngestFolderRequest(BaseModel):
    """Requête pour ingérer un dossier de fichiers."""
    candidature_id: UUID
    folder_path: str = Field(..., description="Chemin du dossier à ingérer")
    auto_classify: bool = Field(True, description="Classer automatiquement les documents")


class AOClassifyDocumentRequest(BaseModel):
    """Requête pour classifier un document."""
    document_id: UUID


class AOExtractPricingRequest(BaseModel):
    """Requête pour extraire les données pricing d'un BPU."""
    document_id: UUID


class AOLensAnalysisRequest(BaseModel):
    """Requête pour lancer une analyse par Lentille."""
    lens_type: AOLensType
    candidature_id: UUID
    document_ids: Optional[List[UUID]] = Field(None, description="Documents spécifiques à analyser")
    contexte: Dict[str, Any] = Field(default_factory=dict)


class AODraftingRequest(BaseModel):
    """Requête pour générer du contenu via Lentille Rédaction."""
    candidature_id: UUID
    chapitre: str = Field(..., description="Chapitre du mémoire à rédiger")
    contexte_additionnel: Optional[str] = None
    references_memoires_gagnants: Optional[List[UUID]] = None


class AODraftingIterateRequest(BaseModel):
    """Requête pour itérer sur un draft (Petit Prompt)."""
    current_content: str
    instruction: str = Field(..., description="Instruction de modification")


class AOValidationRequest(BaseModel):
    """Requête pour valider/rejeter une suggestion IA."""
    analyse_id: UUID
    validation: AOValidationStatus
    commentaire: Optional[str] = None


# ============================================================================
# RESPONSE MODELS (API)
# ============================================================================

class AOIngestFolderResponse(BaseModel):
    """Réponse après ingestion d'un dossier."""
    candidature_id: UUID
    fichiers_trouves: int
    documents_crees: int
    erreurs: List[str]
    documents: List[AODocumentListItem]


class AOClassifyDocumentResponse(BaseModel):
    """Réponse après classification."""
    document_id: UUID
    type_doc_detecte: AODocumentType
    confidence: float
    metadata_extrait: Dict[str, Any]


class AOExtractPricingResponse(BaseModel):
    """Réponse après extraction pricing."""
    document_id: UUID
    postes_extraits: int
    montant_total_ht: Optional[Decimal]
    postes: List[AOPostePricingListItem]


class AOLensAnalysisResponse(BaseModel):
    """Réponse après analyse par Lentille."""
    analyse_id: UUID
    lens_type: AOLensType
    resultat: Dict[str, Any]
    score_confiance: float
    tokens_utilises: int
    duree_ms: int


class AODraftingResponse(BaseModel):
    """Réponse après génération de draft."""
    content: str
    suggestions: List[str] = []
    sources_utilisees: List[UUID] = []
    generated_at: datetime
    model_used: str


class AOPricingContextResponse(BaseModel):
    """Réponse avec contexte pricing historique."""
    poste_recherche: str
    resultats: List[Dict[str, Any]]
    prix_moyen_historique: Optional[Decimal]
    prix_min_historique: Optional[Decimal]
    prix_max_historique: Optional[Decimal]
    nombre_occurrences: int


class AOSimilarAOResponse(BaseModel):
    """Réponse avec AO similaires historiques."""
    candidature_id: UUID
    similar_ao: List[Dict[str, Any]]


# ============================================================================
# LIST AND PAGINATION
# ============================================================================

class AOCandidatureListResponse(BaseModel):
    """Réponse liste des candidatures avec pagination."""
    data: List[AOCandidatureListItem]
    total: int
    page: int
    limit: int


class AODocumentListResponse(BaseModel):
    """Réponse liste des documents."""
    data: List[AODocumentListItem]
    total: int


class AOPostePricingListResponse(BaseModel):
    """Réponse liste des postes pricing."""
    data: List[AOPostePricingListItem]
    total: int
    montant_total_ht: Optional[Decimal]


class AOAnalyseListResponse(BaseModel):
    """Réponse liste des analyses."""
    data: List[AOAnalyseListItem]
    total: int


# ============================================================================
# DASHBOARD / STATS
# ============================================================================

class AODashboardStats(BaseModel):
    """Statistiques pour le dashboard AO."""
    org_id: UUID
    total_candidatures: int
    par_statut: Dict[str, int]
    taux_reussite: float
    montant_total_gagne: Decimal
    montant_total_perdu: Decimal
    moyenne_postes_par_ao: float
    top_categories: List[Dict[str, Any]]
    
    
class AOPricingGapAnalysis(BaseModel):
    """Analyse du gap de pricing entre gagnés et perdus."""
    categorie: str
    prix_moyen_gagne: Optional[Decimal]
    prix_moyen_perdu: Optional[Decimal]
    gap_pct: Optional[float]
    nb_postes_gagne: int
    nb_postes_perdu: int


class AOComparativeAnalysisResponse(BaseModel):
    """Réponse analyse comparative complète."""
    candidature_id: UUID
    gaps_pricing: List[AOPricingGapAnalysis]
    recommandations: List[str]
    score_competitivite: float  # 0-100
