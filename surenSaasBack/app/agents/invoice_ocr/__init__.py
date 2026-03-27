"""
Invoice OCR Agent

Module agentic pour l'extraction automatique des données de factures.
Actuellement en coquille - le workflow est structuré mais l'OCR n'est pas implémenté.

Usage:
    from app.agents.invoice_ocr import InvoiceOCRWorkflow, ExtractedInvoiceData
    
    workflow = InvoiceOCRWorkflow()
    result = await workflow.execute(context)
"""

from .workflow import InvoiceOCRWorkflow, WorkflowContext, WorkflowStatus, StepResult
from .contracts import (
    ExtractedInvoiceData,
    InvoiceLineItem,
    OCRInput,
    OCROutput,
    ValidationResult,
)

__version__ = "1.0.0"

__all__ = [
    'InvoiceOCRWorkflow',
    'WorkflowContext',
    'WorkflowStatus',
    'StepResult',
    'ExtractedInvoiceData',
    'InvoiceLineItem',
    'OCRInput',
    'OCROutput',
    'ValidationResult',
]
