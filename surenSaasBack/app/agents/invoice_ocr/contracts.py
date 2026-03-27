"""
Contracts: Invoice OCR

Définition des types et contrats entre les steps du workflow OCR.
Ces contrats assurent la compatibilité entre les différentes étapes.
"""

from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass


# =============================================================================
# INPUT/OUTPUT CONTRACTS
# =============================================================================

class OCRInput(TypedDict):
    """Données d'entrée du workflow OCR."""
    file_url: str
    file_type: str  # 'photo' | 'pdf'
    org_id: str
    user_id: str
    invoice_id: Optional[str]  # Si modification


class OCROutput(TypedDict):
    """Données de sortie du workflow OCR."""
    success: bool
    data: Optional['ExtractedInvoiceData']
    error: Optional[str]
    confidence_score: float
    processing_time_ms: int
    raw_ocr_text: Optional[str]


# =============================================================================
# EXTRACTED DATA CONTRACT
# =============================================================================

@dataclass
class ExtractedInvoiceData:
    """
    Structure des données extraites d'une facture.
    
    Cette classe définit le contrat entre l'agent OCR et le service
    de facturation. Tous les champs sont optionnels car l'OCR
    peut ne pas tout détecter.
    """
    # Fournisseur
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    supplier_siret: Optional[str] = None
    supplier_email: Optional[str] = None
    supplier_phone: Optional[str] = None
    
    # Montants
    amount_ht: Optional[float] = None
    amount_ttc: Optional[float] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    currency: str = "EUR"
    
    # Dates
    invoice_date: Optional[str] = None  # ISO 8601: YYYY-MM-DD
    due_date: Optional[str] = None
    delivery_date: Optional[str] = None
    
    # Détails
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    purchase_order: Optional[str] = None  # Numéro bon de commande
    
    # Lignes de facture (détail)
    line_items: Optional[List['InvoiceLineItem']] = None
    
    # Métadonnées OCR
    confidence_score: float = 0.0
    raw_ocr_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation JSON."""
        return {
            'supplier_name': self.supplier_name,
            'supplier_address': self.supplier_address,
            'supplier_siret': self.supplier_siret,
            'supplier_email': self.supplier_email,
            'supplier_phone': self.supplier_phone,
            'amount_ht': self.amount_ht,
            'amount_ttc': self.amount_ttc,
            'vat_amount': self.vat_amount,
            'vat_rate': self.vat_rate,
            'currency': self.currency,
            'invoice_date': self.invoice_date,
            'due_date': self.due_date,
            'delivery_date': self.delivery_date,
            'invoice_number': self.invoice_number,
            'description': self.description,
            'purchase_order': self.purchase_order,
            'line_items': [item.to_dict() for item in self.line_items] if self.line_items else None,
            'confidence_score': self.confidence_score,
            'raw_ocr_data': self.raw_ocr_data
        }


@dataclass
class InvoiceLineItem:
    """Ligne de facture détaillée."""
    label: str
    quantity: float
    unit: str = "unité"  # m², kg, heure, etc.
    unit_price_ht: Optional[float] = None
    total_price_ht: Optional[float] = None
    vat_rate: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'label': self.label,
            'quantity': self.quantity,
            'unit': self.unit,
            'unit_price_ht': self.unit_price_ht,
            'total_price_ht': self.total_price_ht,
            'vat_rate': self.vat_rate
        }


# =============================================================================
# STEP CONTRACTS
# =============================================================================

class StepInput(TypedDict):
    """Input standard pour un step."""
    context: Dict[str, Any]
    previous_step_data: Optional[Dict[str, Any]]


class StepOutput(TypedDict):
    """Output standard pour un step."""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    next_step: Optional[str]


# =============================================================================
# OCR PROVIDER CONTRACTS
# =============================================================================

class OCRProviderResult(TypedDict):
    """Résultat d'un provider OCR (Tesseract, Google Vision, etc.)."""
    text: str
    confidence: float
    bounding_boxes: Optional[List[Dict[str, Any]]]
    raw_response: Optional[Dict[str, Any]]


class OCRProvider(Protocol):
    """Interface pour les providers OCR."""
    
    async def extract_text(self, image_path: str) -> OCRProviderResult:
        """Extrait le texte d'une image."""
        ...
    
    async def extract_from_pdf(self, pdf_path: str) -> List[OCRProviderResult]:
        """Extrait le texte d'un PDF (une page = un résultat)."""
        ...


# =============================================================================
# VALIDATION CONTRACTS
# =============================================================================

class ValidationResult(TypedDict):
    """Résultat de la validation des données."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    confidence: float
    validated_fields: Dict[str, bool]  # Champ -> valide ou non


class ValidationRule(TypedDict):
    """Règle de validation pour un champ."""
    field: str
    required: bool
    type: str  # 'string', 'number', 'date', 'email', etc.
    pattern: Optional[str]  # Regex pattern
    min_value: Optional[float]
    max_value: Optional[float]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'OCRInput',
    'OCROutput',
    'ExtractedInvoiceData',
    'InvoiceLineItem',
    'StepInput',
    'StepOutput',
    'OCRProviderResult',
    'OCRProvider',
    'ValidationResult',
    'ValidationRule',
]


# Import Protocol depuis typing pour Python < 3.8
try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol
    __all__.append('Protocol')
