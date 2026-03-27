"""
Extracteur de documents générique avec Google Gemini.

Point d'entrée principal pour l'extraction de données depuis n'importe quel type de document.
Supporte les factures, reçus, contrats, et documents personnalisés.
"""

import json
from typing import Optional, Dict, Any, Union
from pathlib import Path
from datetime import datetime

from app.agents.base.gemini_client import GeminiClient
from app.agents.processors import FileProcessor
from app.agents.models import ExtractionResult, ExtractionStatus, ExtractionField
from app.agents.prompts import get_prompt, create_custom_prompt
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GenericDocumentExtractor:
    """
    Extracteur générique de documents utilisant Google Gemini.
    
    Permet d'extraire des données structurées depuis n'importe quel document
    (PDF, images) avec un prompt système configurable.
    
    Exemple:
        ```python
        # Extraction standard - facture
        extractor = GenericDocumentExtractor(
            document_type="invoice",
            system_prompt=None  # Utilise le prompt par défaut pour factures
        )
        result = await extractor.extract("facture.pdf")
        
        # Extraction personnalisée
        extractor = GenericDocumentExtractor(
            document_type="custom",
            system_prompt="Prompt spécifique...",
            output_schema={"champ1": "description"}
        )
        ```
    """
    
    def __init__(
        self,
        document_type: str = "generic",
        system_prompt: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        gemini_model: Optional[str] = None,
        temperature: float = 0.1
    ):
        """
        Initialise l'extracteur.
        
        Args:
            document_type: Type de document (invoice, receipt, contract, custom)
            system_prompt: Prompt système personnalisé (optionnel)
            output_schema: Schéma JSON attendu (optionnel)
            gemini_model: Modèle Gemini (défaut: gemini-1.5-flash)
            temperature: Créativité (0.0 = déterministe)
        """
        self.document_type = document_type
        
        # Construire le prompt
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = get_prompt(document_type)
        
        self.output_schema = output_schema
        
        # Initialiser le client Gemini Vertex AI
        model = gemini_model or settings.gemini_model or "gemini-1.5-flash-001"
        self.gemini_client = GeminiClient(
            credentials_b64=settings.gemini_api_key,
            location=settings.gemini_location or "europe-west1",
            model=model,
            temperature=temperature
        )
        
        # Initialiser le processeur de fichiers
        self.file_processor = FileProcessor()
        
        logger.info(f"✅ GenericDocumentExtractor initialisé - Type: {document_type}, Model: {model}")
    
    async def extract(
        self,
        source: str,
        file_type: Optional[str] = None,
        optimize: bool = True
    ) -> ExtractionResult:
        """
        Extrait les données d'un document.
        
        Args:
            source: Chemin fichier, URL, ou données base64
            file_type: Type de fichier (pdf, jpeg, png) - auto-détecté si non fourni
            optimize: Optimiser les images avant envoi
            
        Returns:
            ExtractionResult avec les données extraites
        """
        start_time = datetime.now()
        
        try:
            # Préparer le fichier
            logger.info(f"📄 Préparation du document: {source}")
            
            # Déterminer le type si non fourni
            if not file_type:
                if source.startswith(('http://', 'https://')):
                    file_type = Path(source).suffix.lower().lstrip('.')
                else:
                    file_type = Path(source).suffix.lower().lstrip('.')
            
            # Préparer les données
            file_data, mime_type = await self.file_processor.prepare_for_extraction(
                source, optimize=optimize
            )
            
            logger.info(f"🤖 Envoi à Gemini ({mime_type})...")
            
            # Extraction selon le type
            if mime_type == "application/pdf":
                response_text = self.gemini_client.extract_from_pdf(
                    file_data, self.system_prompt
                )
            else:
                response_text = self.gemini_client.extract_from_image(
                    file_data, self.system_prompt, mime_type
                )
            
            # Parser la réponse JSON
            extracted_data = self._parse_response(response_text)
            
            # Calculer le temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Construire le résultat
            result = ExtractionResult(
                document_type=self.document_type,
                extraction_timestamp=start_time,
                source_file=source,
                model_used=self.gemini_client.model_name,
                raw_data=extracted_data,
                status=ExtractionStatus.SUCCESS,
                processing_time_ms=processing_time,
                pages_processed=extracted_data.get("metadata", {}).get("pages_count", 1)
            )
            
            logger.info(
                f"✅ Extraction réussie en {processing_time:.0f}ms "
                f"- Confiance: {result.get_confidence_score():.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction: {e}")
            
            # Retourner un résultat d'erreur
            return ExtractionResult(
                document_type=self.document_type,
                extraction_timestamp=start_time,
                source_file=source,
                model_used=self.gemini_client.model_name if hasattr(self, 'gemini_client') else "unknown",
                raw_data={},
                status=ExtractionStatus.ERROR,
                errors=[str(e)],
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
        
        finally:
            # Nettoyer
            await self.file_processor.close()
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse la réponse JSON de Gemini.
        
        Args:
            response_text: Texte de réponse
            
        Returns:
            Dictionnaire parsé
        """
        try:
            # Nettoyer la réponse (enlever markdown si présent)
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parser le JSON
            data = json.loads(cleaned)
            
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  Réponse non-JSON, tentative de parsing alternatif: {e}")
            # Si ce n'est pas du JSON, retourner dans un wrapper
            return {
                "raw_text": response_text,
                "parse_error": str(e),
                "document_type": self.document_type
            }
    
    def validate_extraction(self, result: ExtractionResult) -> Dict[str, Any]:
        """
        Valide les données extraites.
        
        Args:
            result: Résultat d'extraction
            
        Returns:
            Rapport de validation
        """
        issues = []
        warnings_list = []
        
        data = result.raw_data
        
        # Vérifier que extracted_data existe
        if "extracted_data" not in data:
            issues.append("Champ 'extracted_data' manquant")
        else:
            extracted = data["extracted_data"]
            
            # Vérifier selon le type de document
            if self.document_type == "invoice":
                # Vérifier montants
                amounts = extracted.get("amounts", {})
                ht = amounts.get("ht")
                ttc = amounts.get("ttc")
                vat = amounts.get("vat")
                
                if ht and ttc and vat:
                    expected_ttc = ht + vat
                    if abs(expected_ttc - ttc) > 0.01:
                        warnings_list.append(
                            f"Incohérence TVA: HT({ht}) + TVA({vat}) ≠ TTC({ttc})"
                        )
                
                # Vérifier présence fournisseur
                supplier = extracted.get("supplier", {})
                if not supplier.get("name"):
                    warnings_list.append("Nom du fournisseur manquant")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings_list,
            "confidence": result.get_confidence_score()
        }


# Fonctions helpers pour créer des extracteurs spécifiques

def create_invoice_extractor(
    gemini_model: Optional[str] = None,
    temperature: float = 0.1
) -> GenericDocumentExtractor:
    """
    Crée un extracteur pré-configuré pour les factures.
    
    Args:
        gemini_model: Modèle Gemini (flash par défaut)
        temperature: Créativité
        
    Returns:
        Extracteur configuré pour factures
    """
    return GenericDocumentExtractor(
        document_type="invoice",
        gemini_model=gemini_model,
        temperature=temperature
    )


def create_receipt_extractor(
    gemini_model: Optional[str] = None,
    temperature: float = 0.1
) -> GenericDocumentExtractor:
    """
    Crée un extracteur pré-configuré pour les tickets de caisse.
    
    Args:
        gemini_model: Modèle Gemini
        temperature: Créativité
        
    Returns:
        Extracteur configuré pour tickets
    """
    return GenericDocumentExtractor(
        document_type="receipt",
        gemini_model=gemini_model,
        temperature=temperature
    )


def create_custom_extractor(
    document_type: str,
    fields: Dict[str, str],
    instructions: str = "",
    gemini_model: Optional[str] = None,
    temperature: float = 0.1
) -> GenericDocumentExtractor:
    """
    Crée un extracteur personnalisé pour un type de document spécifique.
    
    Args:
        document_type: Nom du type de document
        fields: Dictionnaire {nom_champ: description}
        instructions: Instructions supplémentaires
        gemini_model: Modèle Gemini
        temperature: Créativité
        
    Returns:
        Extracteur personnalisé
        
    Exemple:
        ```python
        extractor = create_custom_extractor(
            document_type="delivery_note",
            fields={
                "order_number": "Numéro de commande",
                "delivery_date": "Date de livraison",
                "items": "Liste des articles livrés"
            },
            instructions="Extrais aussi le nom du transporteur si visible"
        )
        ```
    """
    prompt = create_custom_prompt(document_type, fields, instructions)
    
    return GenericDocumentExtractor(
        document_type=document_type,
        system_prompt=prompt,
        output_schema=fields,
        gemini_model=gemini_model,
        temperature=temperature
    )
