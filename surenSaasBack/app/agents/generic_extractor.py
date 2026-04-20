"""
Extracteur de documents générique avec Google Gemini.

Point d'entrée principal pour l'extraction de données depuis n'importe quel type de document.
Supporte les factures, reçus, contrats, et documents personnalisés.
"""

import json
from typing import Optional, Dict, Any, Union, Tuple, List
from pathlib import Path
from datetime import datetime

from app.agents.base.gemini_client import GeminiClient
from app.agents.processors import FileProcessor
from app.agents.models import ExtractionResult, ExtractionStatus, ExtractionField, PageExtractionResult, PageExtractionStatus
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
        temperature: float = 0.1,
        # Nouveaux paramètres pour PDF multi-pages
        page_range: Optional[Tuple[int, int]] = None,
        extract_by_pages: bool = False,
        max_pages: Optional[int] = None,
        fallback_on_page_error: bool = True
    ):
        """
        Initialise l'extracteur.
        
        Args:
            document_type: Type de document (invoice, receipt, contract, custom)
            system_prompt: Prompt système personnalisé (optionnel)
            output_schema: Schéma JSON attendu (optionnel)
            gemini_model: Modèle Gemini (défaut: gemini-1.5-flash)
            temperature: Créativité (0.0 = déterministe)
            page_range: Plage de pages à extraire (start, end) inclusif
            extract_by_pages: Traiter chaque page séparément (pour documents complexes)
            max_pages: Nombre maximum de pages à traiter
            fallback_on_page_error: Continuer l'extraction si une page échoue
        """
        self.document_type = document_type
        
        # Construire le prompt
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            # Inclure les instructions multi-pages si on extrait par pages
            self.system_prompt = get_prompt(document_type, multi_page=extract_by_pages)
        
        self.output_schema = output_schema
        
        # Paramètres PDF multi-pages
        self.page_range = page_range
        self.extract_by_pages = extract_by_pages
        self.max_pages = max_pages
        self.fallback_on_page_error = fallback_on_page_error
        
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
        if page_range:
            logger.info(f"   Page range: {page_range[0]}-{page_range[1]}")
        if extract_by_pages:
            logger.info(f"   Mode: extraction par pages")
    
    async def extract(
        self,
        source: str,
        file_type: Optional[str] = None,
        optimize: bool = True,
        # Paramètres optionnels pour override
        page_range: Optional[Tuple[int, int]] = None,
        extract_by_pages: Optional[bool] = None
    ) -> ExtractionResult:
        """
        Extrait les données d'un document.
        
        Args:
            source: Chemin fichier, URL, ou données base64
            file_type: Type de fichier (pdf, jpeg, png) - auto-détecté si non fourni
            optimize: Optimiser les images avant envoi
            page_range: Override de la plage de pages (optionnel)
            extract_by_pages: Override du mode extraction par pages (optionnel)
            
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
            
            # Ignorer les fichiers ZIP
            if file_type == 'zip':
                logger.warning(f"⚠️  Fichier ZIP ignoré: {source}")
                return ExtractionResult(
                    document_type=self.document_type,
                    extraction_timestamp=start_time,
                    source_file=source,
                    model_used="none",
                    raw_data={"raw_text": "", "document_type": self.document_type, "zip_ignored": True},
                    status=ExtractionStatus.SUCCESS,
                    processing_time_ms=0
                )
            
            # Préparer les données
            file_data, mime_type = await self.file_processor.prepare_for_extraction(
                source, optimize=optimize
            )
            
            logger.info(f"🤖 Envoi à Gemini ({mime_type})...")
            
            # Extraction selon le type et les paramètres
            use_page_range = page_range if page_range is not None else self.page_range
            use_extract_by_pages = extract_by_pages if extract_by_pages is not None else self.extract_by_pages
            
            if mime_type == "application/pdf" and use_extract_by_pages:
                # Mode extraction par pages
                page_results = await self._extract_pdf_by_pages(
                    file_data, mime_type, use_page_range
                )
                
                # Fusionner les résultats des pages
                extracted_data, page_extraction_results = self._merge_page_results(page_results)
                
                # Calculer les métriques
                pages_extracted = len([p for p in page_extraction_results if p.status == PageExtractionStatus.SUCCESS])
                pages_failed = len([p for p in page_extraction_results if p.status == PageExtractionStatus.ERROR])
                
            else:
                # Mode extraction standard
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
                page_extraction_results = []
                pages_extracted = extracted_data.get("metadata", {}).get("pages_count", 1)
                pages_failed = 0
            
            # Calculer le temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Construire le résultat
            result = ExtractionResult(
                document_type=self.document_type,
                extraction_timestamp=start_time,
                source_file=source,
                model_used=self.gemini_client.model_name,
                raw_data=extracted_data,
                page_results=page_extraction_results,
                status=ExtractionStatus.SUCCESS,
                processing_time_ms=processing_time,
                pages_processed=extracted_data.get("metadata", {}).get("pages_count", 1),
                pages_extracted=pages_extracted,
                pages_failed=pages_failed,
                page_range_extracted=f"{use_page_range[0]}-{use_page_range[1]}" if use_page_range else None
            )
            
            logger.info(
                f"✅ Extraction réussie en {processing_time:.0f}ms "
                f"- Pages: {pages_extracted} extraites, {pages_failed} échouées"
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
    
    async def _extract_pdf_by_pages(
        self,
        pdf_data: bytes,
        mime_type: str,
        page_range: Optional[Tuple[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrait un PDF page par page.
        
        Args:
            pdf_data: Données binaires du PDF
            mime_type: Type MIME
            page_range: Plage de pages à extraire
            
        Returns:
            Liste de résultats par page
        """
        try:
            logger.info(f"📑 Extraction PDF par pages (range: {page_range})")
            
            # Utiliser la nouvelle méthode du client Gemini
            page_results = self.gemini_client.extract_from_pdf_pages(
                pdf_data=pdf_data,
                prompt=self.system_prompt,
                page_range=page_range,
                max_pages=self.max_pages,
                fallback_on_error=self.fallback_on_page_error
            )
            
            return page_results
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction par pages: {e}")
            
            if self.fallback_on_page_error:
                logger.warning("⚠️  Fallback vers extraction standard")
                # Retourne un résultat vide pour permettre le fallback
                return []
            else:
                raise
    
    def _merge_page_results(self, page_results: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[PageExtractionResult]]:
        """
        Fusionne les résultats d'extraction par page.
        
        Args:
            page_results: Résultats bruts par page
            
        Returns:
            Tuple (données fusionnées, résultats par page)
        """
        if not page_results:
            return {"document_type": self.document_type, "extracted_data": {}}, []
        
        page_extraction_results = []
        all_extracted_data = {}
        
        for page_result in page_results:
            page_number = page_result.get("page_number", 1)
            response_text = page_result.get("response_text", "")
            status = page_result.get("status", "success")
            
            try:
                if response_text:
                    parsed_data = self._parse_response(response_text)
                    
                    # Créer le résultat de page
                    page_extraction_result = PageExtractionResult(
                        page_number=page_number,
                        extracted_data=parsed_data,
                        status=PageExtractionStatus.SUCCESS if status == "success" else PageExtractionStatus.ERROR,
                        confidence=0.8,  # Valeur par défaut
                        errors=page_result.get("errors", []),
                        warnings=page_result.get("warnings", [])
                    )
                    
                    # Fusionner les données extraites
                    extracted_data = parsed_data.get("extracted_data", {})
                    if extracted_data:
                        # Stratégie de fusion simple: priorité aux dernières pages
                        for key, value in extracted_data.items():
                            if key not in all_extracted_data or isinstance(value, (list, dict)):
                                # Pour les listes et dicts, on les fusionne
                                if isinstance(value, list) and key in all_extracted_data:
                                    all_extracted_data[key].extend(value)
                                elif isinstance(value, dict) and key in all_extracted_data:
                                    all_extracted_data[key].update(value)
                                else:
                                    all_extracted_data[key] = value
                            elif isinstance(value, (str, int, float)) and not all_extracted_data[key]:
                                # Pour les valeurs simples, on remplace si vide
                                all_extracted_data[key] = value
                    
                else:
                    page_extraction_result = PageExtractionResult(
                        page_number=page_number,
                        extracted_data={},
                        status=PageExtractionStatus.ERROR,
                        errors=["Pas de réponse de l'API"],
                        confidence=0.0
                    )
                
                page_extraction_results.append(page_extraction_result)
                
            except Exception as e:
                logger.error(f"❌ Erreur traitement page {page_number}: {e}")
                
                page_extraction_result = PageExtractionResult(
                    page_number=page_number,
                    extracted_data={},
                    status=PageExtractionStatus.ERROR,
                    errors=[str(e)],
                    confidence=0.0
                )
                page_extraction_results.append(page_extraction_result)
        
        # Créer la structure finale
        merged_data = {
            "document_type": self.document_type,
            "extracted_data": all_extracted_data,
            "metadata": {
                "confidence": "high" if len(page_extraction_results) > 0 else "low",
                "pages_count": len(page_results),
                "extraction_method": "page_by_page"
            }
        }
        
        return merged_data, page_extraction_results
    
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
    temperature: float = 0.1,
    page_range: Optional[Tuple[int, int]] = None,
    extract_by_pages: bool = False,
    max_pages: Optional[int] = None,
    fallback_on_page_error: bool = True
) -> GenericDocumentExtractor:
    """
    Crée un extracteur pré-configuré pour les factures.
    
    Args:
        gemini_model: Modèle Gemini (flash par défaut)
        temperature: Créativité
        page_range: Plage de pages à extraire
        extract_by_pages: Traiter chaque page séparément
        max_pages: Nombre maximum de pages
        fallback_on_page_error: Continuer si une page échoue
        
    Returns:
        Extracteur configuré pour factures
    """
    return GenericDocumentExtractor(
        document_type="invoice",
        gemini_model=gemini_model,
        temperature=temperature,
        page_range=page_range,
        extract_by_pages=extract_by_pages,
        max_pages=max_pages,
        fallback_on_page_error=fallback_on_page_error
    )


def create_receipt_extractor(
    gemini_model: Optional[str] = None,
    temperature: float = 0.1,
    page_range: Optional[Tuple[int, int]] = None,
    extract_by_pages: bool = False,
    max_pages: Optional[int] = None,
    fallback_on_page_error: bool = True
) -> GenericDocumentExtractor:
    """
    Crée un extracteur pré-configuré pour les tickets de caisse.
    
    Args:
        gemini_model: Modèle Gemini
        temperature: Créativité
        page_range: Plage de pages à extraire
        extract_by_pages: Traiter chaque page séparément
        max_pages: Nombre maximum de pages
        fallback_on_page_error: Continuer si une page échoue
        
    Returns:
        Extracteur configuré pour tickets
    """
    return GenericDocumentExtractor(
        document_type="receipt",
        gemini_model=gemini_model,
        temperature=temperature,
        page_range=page_range,
        extract_by_pages=extract_by_pages,
        max_pages=max_pages,
        fallback_on_page_error=fallback_on_page_error
    )


def create_custom_extractor(
    document_type: str,
    fields: Dict[str, str],
    instructions: str = "",
    gemini_model: Optional[str] = None,
    temperature: float = 0.1,
    page_range: Optional[Tuple[int, int]] = None,
    extract_by_pages: bool = False,
    max_pages: Optional[int] = None,
    fallback_on_page_error: bool = True
) -> GenericDocumentExtractor:
    """
    Crée un extracteur personnalisé pour un type de document spécifique.
    
    Args:
        document_type: Nom du type de document
        fields: Dictionnaire {nom_champ: description}
        instructions: Instructions supplémentaires
        gemini_model: Modèle Gemini
        temperature: Créativité
        page_range: Plage de pages à extraire
        extract_by_pages: Traiter chaque page séparément
        max_pages: Nombre maximum de pages
        fallback_on_page_error: Continuer si une page échoue
        
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
    # Inclure les instructions multi-pages si on extrait par pages
    prompt = create_custom_prompt(document_type, fields, instructions, multi_page=extract_by_pages)
    
    return GenericDocumentExtractor(
        document_type=document_type,
        system_prompt=prompt,
        output_schema=fields,
        gemini_model=gemini_model,
        temperature=temperature,
        page_range=page_range,
        extract_by_pages=extract_by_pages,
        max_pages=max_pages,
        fallback_on_page_error=fallback_on_page_error
    )
