"""
Agent: Invoice OCR Workflow

Structure du workflow agentic pour l'OCR des factures.
Coquille pour l'instant - à implémenter plus tard.

Architecture:
- Workflow orchestre les steps
- Chaque step est indépendant et testable
- Contrats définis entre steps
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowContext:
    """Contexte partagé entre les steps du workflow."""
    workflow_id: str
    file_url: str
    file_type: str  # 'photo' ou 'pdf'
    org_id: str
    user_id: str
    
    # Données accumulées
    raw_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validated_data: Optional[Dict[str, Any]] = None
    
    # Métadonnées
    current_step: str = "init"
    status: WorkflowStatus = WorkflowStatus.PENDING
    errors: Optional[list] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class StepResult:
    """Résultat d'une étape du workflow."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    next_step: Optional[str] = None


class InvoiceOCRWorkflow:
    """
    Workflow agentic pour l'OCR des factures.
    
    Steps:
    1. receive_file: Télécharge et valide le fichier
    2. preprocess: Prétraitement image (rotation, contraste)
    3. ocr_extract: Extraction texte brute (Tesseract/API)
    4. parse_data: Parsing intelligent (NER/LLM)
    5. validate_data: Validation structurelle
    6. format_output: Formatage données finales
    
    Usage:
        workflow = InvoiceOCRWorkflow()
        result = await workflow.execute(context)
    """
    
    def __init__(self):
        self.steps: Dict[str, Callable] = {
            'receive_file': self._step_receive_file,
            'preprocess': self._step_preprocess,
            'ocr_extract': self._step_ocr_extract,
            'parse_data': self._step_parse_data,
            'validate_data': self._step_validate_data,
            'format_output': self._step_format_output,
        }
    
    async def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        Exécute le workflow complet.
        
        Args:
            context: Contexte avec file_url, file_type, etc.
            
        Returns:
            Dict avec les données extraites ou erreur
        """
        context.status = WorkflowStatus.RUNNING
        
        try:
            # Exécuter les steps en séquence
            step_order = ['receive_file', 'preprocess', 'ocr_extract', 
                         'parse_data', 'validate_data', 'format_output']
            
            for step_name in step_order:
                context.current_step = step_name
                step_func = self.steps[step_name]
                
                result = await step_func(context)
                
                if not result.success:
                    context.status = WorkflowStatus.FAILED
                    if context.errors is None:
                        context.errors = []
                    context.errors.append(f"{step_name}: {result.error}")
                    return {
                        'success': False,
                        'error': result.error,
                        'step': step_name,
                        'context': self._context_to_dict(context)
                    }
                
                # Mettre à jour le contexte avec les données du step
                if result.data:
                    self._update_context(context, step_name, result.data)
            
            context.status = WorkflowStatus.COMPLETED
            
            return {
                'success': True,
                'data': context.validated_data or context.extracted_data,
                'confidence_score': self._calculate_confidence(context),
                'context': self._context_to_dict(context)
            }
            
        except Exception as e:
            context.status = WorkflowStatus.FAILED
            if context.errors is None:
                context.errors = []
            context.errors.append(f"workflow_error: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'context': self._context_to_dict(context)
            }
    
    # =========================================================================
    # STEPS (COQUILLES - À IMPLÉMENTER)
    # =========================================================================
    
    async def _step_receive_file(self, context: WorkflowContext) -> StepResult:
        """
        Step 1: Reçoit et valide le fichier.
        
        TODO: Implémenter
        - Télécharger depuis l'URL
        - Vérifier format (PDF, JPG, PNG)
        - Vérifier taille (< 10MB)
        - Stocker temporairement
        """
        # COQUILLE
        return StepResult(
            success=True,
            data={'message': 'Step receive_file - À implémenter'},
            next_step='preprocess'
        )
    
    async def _step_preprocess(self, context: WorkflowContext) -> StepResult:
        """
        Step 2: Prétraite l'image.
        
        TODO: Implémenter
        - Rotation automatique
        - Amélioration contraste
        - Binarisation
        - Débruitage
        """
        # COQUILLE
        return StepResult(
            success=True,
            data={'message': 'Step preprocess - À implémenter'},
            next_step='ocr_extract'
        )
    
    async def _step_ocr_extract(self, context: WorkflowContext) -> StepResult:
        """
        Step 3: Extraction OCR du texte brut.
        
        TODO: Implémenter
        - Tesseract OCR (local)
        - Ou API OCR (Google Vision, Azure, etc.)
        - Retourne texte brut + bounding boxes
        """
        # COQUILLE
        return StepResult(
            success=True,
            data={
                'message': 'Step ocr_extract - À implémenter',
                'raw_text': 'TEXTE_OCR_EXEMPLE_À_REMPLACER'
            },
            next_step='parse_data'
        )
    
    async def _step_parse_data(self, context: WorkflowContext) -> StepResult:
        """
        Step 4: Parsing intelligent des données.
        
        TODO: Implémenter
        - NER (Named Entity Recognition) ou LLM
        - Extraction: supplier, amounts, dates, etc.
        - Structure en JSON
        """
        # COQUILLE
        return StepResult(
            success=True,
            data={
                'message': 'Step parse_data - À implémenter',
                'extracted': {
                    'supplier_name': 'Exemple Fournisseur',
                    'amount_ttc': 1200.00,
                    'invoice_date': '2024-01-15'
                }
            },
            next_step='validate_data'
        )
    
    async def _step_validate_data(self, context: WorkflowContext) -> StepResult:
        """
        Step 5: Validation des données extraites.
        
        TODO: Implémenter
        - Vérifier champs obligatoires
        - Valider formats (SIRET, dates, montants)
        - Score de confiance
        """
        # COQUILLE
        return StepResult(
            success=True,
            data={
                'message': 'Step validate_data - À implémenter',
                'validated': True,
                'confidence': 0.0
            },
            next_step='format_output'
        )
    
    async def _step_format_output(self, context: WorkflowContext) -> StepResult:
        """
        Step 6: Formatage de la sortie finale.
        
        TODO: Implémenter
        - Transformer en format Invoice
        - Ajouter métadonnées OCR
        """
        # COQUILLE - Retourne données d'exemple pour l'instant
        return StepResult(
            success=True,
            data={
                'supplier_name': 'Exemple Fournisseur SARL',
                'supplier_address': '123 Rue Example, 75000 Paris',
                'supplier_siret': '123 456 789 00012',
                'amount_ht': 1000.00,
                'amount_ttc': 1200.00,
                'vat_amount': 200.00,
                'vat_rate': 20.0,
                'invoice_date': '2024-01-15',
                'due_date': '2024-02-15',
                'description': 'Matériaux de construction',
                'invoice_number': 'FAC-2024-001',
                'confidence_score': 0.0,
                'raw_ocr_data': {
                    'note': 'COQUILLE - OCR non implémenté',
                    'workflow_id': context.workflow_id
                }
            }
        )
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _update_context(self, context: WorkflowContext, step: str, data: Dict):
        """Met à jour le contexte avec les données d'un step."""
        if step == 'ocr_extract':
            context.raw_text = data.get('raw_text')
        elif step == 'parse_data':
            context.extracted_data = data.get('extracted')
        elif step == 'validate_data':
            context.validated_data = data.get('validated')
    
    def _context_to_dict(self, context: WorkflowContext) -> Dict[str, Any]:
        """Convertit le contexte en dict pour sérialisation."""
        return {
            'workflow_id': context.workflow_id,
            'file_type': context.file_type,
            'current_step': context.current_step,
            'status': context.status.value,
            'errors': context.errors
        }
    
    def _calculate_confidence(self, context: WorkflowContext) -> float:
        """Calcule le score de confiance global."""
        # TODO: Implémenter logique de scoring
        return 0.0
