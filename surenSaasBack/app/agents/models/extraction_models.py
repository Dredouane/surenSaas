"""
Modèles de données pour l'extraction de documents.

Définit les structures de données utilisées par l'agent d'extraction générique.
"""

from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExtractionStatus(str, Enum):
    """Statut de l'extraction."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Certaines données extraites, d'autres manquantes
    ERROR = "error"
    RETRY = "retry"  # À réessayer


@dataclass
class ExtractionField:
    """Un champ extrait avec métadonnées."""
    value: Any
    confidence: float = 0.0  # Score de confiance 0-1
    raw_text: Optional[str] = None  # Texte brut avant parsing
    location: Optional[Dict[str, Any]] = None  # Position dans le document (page, bbox)


@dataclass
class ExtractionResult:
    """Résultat complet d'une extraction."""
    # Métadonnées
    document_type: str
    extraction_timestamp: datetime
    source_file: str
    model_used: str
    
    # Données brutes extraites (JSON libre)
    raw_data: Dict[str, Any]
    
    # Champs structurés (si schéma défini)
    fields: Dict[str, ExtractionField] = field(default_factory=dict)
    
    # Statut et erreurs
    status: ExtractionStatus = ExtractionStatus.SUCCESS
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Métriques
    processing_time_ms: Optional[float] = None
    pages_processed: Optional[int] = None
    
    def get_confidence_score(self) -> float:
        """Calcule le score de confiance global."""
        if not self.fields:
            return 0.0
        scores = [f.confidence for f in self.fields.values()]
        return sum(scores) / len(scores)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return {
            "document_type": self.document_type,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "source_file": self.source_file,
            "model_used": self.model_used,
            "status": self.status.value,
            "raw_data": self.raw_data,
            "fields": {k: {
                "value": v.value,
                "confidence": v.confidence,
                "raw_text": v.raw_text
            } for k, v in self.fields.items()},
            "errors": self.errors,
            "warnings": self.warnings,
            "confidence_score": self.get_confidence_score(),
            "pages_processed": self.pages_processed,
            "processing_time_ms": self.processing_time_ms
        }


@dataclass
class InvoiceLineItem:
    """Ligne de facture extraite."""
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_ht: Optional[float] = None
    vat_rate: Optional[float] = None


@dataclass
class InvoiceData:
    """Structure spécifique pour les factures."""
    # Fournisseur
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    supplier_siret: Optional[str] = None
    
    # Montants
    amount_ht: Optional[float] = None
    amount_ttc: Optional[float] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    
    # Dates
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    
    # Informations facture
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    
    # Lignes de détail
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    
    @classmethod
    def from_raw_data(cls, raw_data: Dict[str, Any]) -> "InvoiceData":
        """Crée une InvoiceData depuis les données brutes."""
        line_items = []
        for item in raw_data.get("line_items", []):
            line_items.append(InvoiceLineItem(**item))
        
        return cls(
            supplier_name=raw_data.get("supplier_name"),
            supplier_address=raw_data.get("supplier_address"),
            supplier_siret=raw_data.get("supplier_siret"),
            amount_ht=raw_data.get("amount_ht"),
            amount_ttc=raw_data.get("amount_ttc"),
            vat_amount=raw_data.get("vat_amount"),
            vat_rate=raw_data.get("vat_rate"),
            invoice_date=raw_data.get("invoice_date"),
            due_date=raw_data.get("due_date"),
            invoice_number=raw_data.get("invoice_number"),
            description=raw_data.get("description"),
            line_items=line_items
        )
