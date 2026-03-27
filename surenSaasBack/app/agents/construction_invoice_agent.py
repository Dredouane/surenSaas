"""
Agent: Construction Invoice Extraction

Agent OCR pour extraire les données des factures de construction.
Utilise l'extracteur générique avec Gemini Flash.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from app.agents.generic_extractor import create_invoice_extractor
from app.agents.models import ExtractionResult, InvoiceData
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class InvoiceLineItem:
    """Ligne de facture extraite."""
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_ht: Optional[float] = None
    vat_rate: Optional[float] = None


@dataclass
class ExtractedInvoiceData:
    """Données extraites d'une facture."""
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
    invoice_date: Optional[str] = None  # ISO format
    due_date: Optional[str] = None
    delivery_date: Optional[str] = None
    
    # Informations facture
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    purchase_order: Optional[str] = None
    
    # Lignes de détail
    line_items: Optional[List[InvoiceLineItem]] = None
    
    # Métadonnées
    confidence_score: float = 0.0
    raw_ocr_data: Optional[Dict[str, Any]] = None
    extraction_method: str = "gemini_flash"
    
    def __post_init__(self):
        if self.line_items is None:
            self.line_items = []


class ConstructionInvoiceAgent:
    """
    Agent d'extraction de factures de construction.
    
    Utilise l'extracteur générique avec Gemini Flash pour OCR.
    """
    
    def __init__(self):
        self.extraction_method = "gemini_flash"
        self.extractor = create_invoice_extractor()
        logger.info("✅ ConstructionInvoiceAgent initialisé (Gemini Flash)")
    
    async def extract_from_document(
        self, 
        file_url: str, 
        file_type: str
    ) -> ExtractedInvoiceData:
        """
        Extrait les données d'une facture depuis un document.
        
        Args:
            file_url: URL du fichier (photo ou PDF)
            file_type: Type de fichier ('photo', 'pdf', 'document')
            
        Returns:
            ExtractedInvoiceData avec les données extraites
        """
        logger.info(f"📄 Extraction facture: {file_type} - {file_url}")
        
        try:
            # Utiliser l'extracteur générique
            result = await self.extractor.extract(
                source=file_url,
                file_type=file_type,
                optimize=True
            )
            
            if result.status.value == "error":
                logger.error(f"❌ Erreur extraction: {result.errors}")
                raise Exception(f"Extraction échouée: {result.errors}")
            
            # Convertir le résultat générique vers le format spécifique
            return self._convert_to_invoice_data(result)
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction facture: {e}")
            raise
    
    def _convert_to_invoice_data(self, result: ExtractionResult) -> ExtractedInvoiceData:
        """
        Convertit le résultat générique vers ExtractedInvoiceData.
        
        Args:
            result: Résultat de l'extraction générique
            
        Returns:
            Données au format Invoice
        """
        raw = result.raw_data
        extracted = raw.get("extracted_data", {})
        
        # Extraire les lignes
        line_items = []
        for item in extracted.get("line_items", []):
            line_items.append(InvoiceLineItem(
                description=item.get("description", ""),
                quantity=item.get("quantity"),
                unit_price=item.get("unit_price"),
                total_ht=item.get("total_ht"),
                vat_rate=item.get("vat_rate")
            ))
        
        # Construire l'objet
        invoice_data = ExtractedInvoiceData(
            supplier_name=extracted.get("supplier", {}).get("name"),
            supplier_address=extracted.get("supplier", {}).get("address"),
            supplier_siret=extracted.get("supplier", {}).get("siret"),
            amount_ht=extracted.get("amounts", {}).get("ht"),
            amount_ttc=extracted.get("amounts", {}).get("ttc"),
            vat_amount=extracted.get("amounts", {}).get("vat"),
            vat_rate=extracted.get("amounts", {}).get("vat_rate"),
            invoice_date=extracted.get("invoice", {}).get("date"),
            due_date=extracted.get("invoice", {}).get("due_date"),
            invoice_number=extracted.get("invoice", {}).get("number"),
            description=extracted.get("invoice", {}).get("description"),
            purchase_order=extracted.get("invoice", {}).get("purchase_order"),
            line_items=line_items,
            confidence_score=result.get_confidence_score(),
            raw_ocr_data=raw,
            extraction_method=self.extraction_method
        )
        
        logger.info(
            f"✅ Facture extraite: {invoice_data.supplier_name} "
            f"- {invoice_data.amount_ttc}€ "
            f"(confiance: {invoice_data.confidence_score:.2f})"
        )
        
        return invoice_data
    
    async def validate_extraction(self, data: ExtractedInvoiceData) -> Dict[str, Any]:
        """
        Valide les données extraites.
        
        Returns:
            Dict avec 'valid' (bool) et 'errors' (list)
        """
        errors = []
        
        # Validation minimale
        if not data.supplier_name:
            errors.append("Nom du fournisseur manquant")
        
        if not data.amount_ttc or data.amount_ttc <= 0:
            errors.append("Montant TTC invalide")
        
        if not data.invoice_date:
            errors.append("Date de facture manquante")
        
        # Validation TVA
        if data.amount_ht and data.vat_amount and data.amount_ttc:
            expected_ttc = data.amount_ht + data.vat_amount
            if abs(expected_ttc - data.amount_ttc) > 0.01:
                errors.append(
                    f"Incohérence TVA: HT({data.amount_ht}) + TVA({data.vat_amount}) "
                    f"≠ TTC({data.amount_ttc})"
                )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "confidence": data.confidence_score
        }
