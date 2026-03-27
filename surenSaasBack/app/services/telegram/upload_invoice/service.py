"""
Service: Upload Invoice (Chargement de factures)

Primitive Telegram: Bouton "Envoyer une facture"
Gère le workflow complet de réception et traitement des factures via Telegram.

Workflow:
1. Réception fichier (photo ou PDF)
2. Validation user autorisé
3. OCR avec Gemini Flash 1.5
4. Présentation données extraites
5. Validation user
6. Création facture en DB
7. Notification gérants
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import uuid
import logging

from app.agents.generic_extractor import create_invoice_extractor

logger = logging.getLogger(__name__)


@dataclass
class ExtractedInvoiceData:
    """Données extraites d'une facture (structure coquille)"""
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    supplier_siret: Optional[str] = None
    amount_ht: Optional[float] = None
    amount_ttc: Optional[float] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    invoice_date: Optional[str] = None  # ISO format
    due_date: Optional[str] = None
    description: Optional[str] = None
    invoice_number: Optional[str] = None
    confidence_score: float = 0.0
    line_items: Optional[list] = None  # Nouveau: lignes de détail
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class InvoiceUploadResult:
    """Résultat du workflow d'upload"""
    success: bool
    invoice_id: Optional[str] = None
    status: Optional[str] = None
    message: str = ""
    extracted_data: Optional[ExtractedInvoiceData] = None
    errors: Optional[list] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class InvoiceUploadService:
    """
    Service de gestion du workflow d'upload de factures via Telegram.
    
    Cette classe est une coquille pour l'instant. Les steps OCR seront
    implémentés plus tard.
    """
    
    def __init__(self, supabase_client, audit_service, notification_service):
        self.supabase = supabase_client
        self.audit = audit_service
        self.notifications = notification_service
    
    async def start_workflow(
        self,
        telegram_user_id: int,
        org_id: str,
        company_id: str,
        file_path: str,  # Chemin local /tmp
        file_type: str,  # 'image' ou 'pdf'
        audit_log_id: str
    ) -> InvoiceUploadResult:
        """
        Démarre le workflow d'upload de facture.
        
        Args:
            telegram_user_id: ID Telegram du conducteur
            org_id: UUID de l'organisation
            company_id: UUID de l'entreprise (construction)
            file_path: Chemin local du fichier (/tmp/...)
            file_type: Type de fichier ('image' ou 'pdf')
            audit_log_id: ID de l'entrée d'audit
            
        Returns:
            InvoiceUploadResult avec le résultat du workflow
        """
        try:
            # Étape 1: Vérifier que l'utilisateur est bien lié à un user de l'app
            user = await self._get_user_from_telegram(telegram_user_id, org_id)
            if not user:
                return InvoiceUploadResult(
                    success=False,
                    message="Utilisateur non autorisé. Veuillez d'abord lier votre compte Telegram dans l'application web."
                )
            
            # Étape 2: Vérifier la capability
            has_capability = await self._check_user_capability(
                user['id'], org_id, 'construction:facturation:write'
            )
            if not has_capability:
                return InvoiceUploadResult(
                    success=False,
                    message="Vous n'avez pas l'autorisation de créer des factures."
                )
            
            # Étape 3: OCR avec Gemini
            extracted_data = await self._perform_ocr(file_path, file_type)
            
            # Log l'étape OCR dans l'audit
            await self.audit.log_workflow_step(
                audit_log_id=audit_log_id,
                workflow_name='invoice_upload',
                step='ocr_completed',
                step_data={
                    'supplier_name': extracted_data.supplier_name,
                    'amount_ttc': extracted_data.amount_ttc,
                    'confidence_score': extracted_data.confidence_score
                }
            )
            
            # Étape 4: Créer la facture en status "brouillon"
            invoice = await self._create_draft_invoice(
                org_id=org_id,
                company_id=company_id,
                user_id=user['id'],
                telegram_user_id=telegram_user_id,
                file_path=file_path,
                extracted_data=extracted_data,
                audit_log_id=audit_log_id
            )
            
            # Note: Les gérants sont notifiés après validation par l'utilisateur
            # (voir _handle_invoice_validation dans telegram_webhooks.py)
            
            return InvoiceUploadResult(
                success=True,
                invoice_id=invoice['id'],
                status='brouillon',
                message="Facture créée avec succès. Elle est en attente de validation par un gérant.",
                extracted_data=extracted_data
            )
            
        except Exception as e:
            # Logger l'erreur dans l'audit
            await self.audit.log_error(
                audit_log_id=audit_log_id,
                error_message=str(e),
                error_type='workflow_failed'
            )
            
            return InvoiceUploadResult(
                success=False,
                message=f"Erreur lors du traitement: {str(e)}"
            )
    
    async def _get_user_from_telegram(self, telegram_user_id: int, org_id: str) -> Optional[Dict]:
        """Récupère l'utilisateur app lié à un ID Telegram.
        
        Utilise deux requêtes séparées pour éviter les problèmes de jointure PostgREST
        avec la table auth.users.
        """
        logger = logging.getLogger(__name__)
        
        # Étape 1: Récupérer le user_id depuis telegram_users
        telegram_result = self.supabase.table('telegram_users') \
            .select('user_id') \
            .eq('telegram_id', telegram_user_id) \
            .eq('org_id', org_id) \
            .eq('is_verified', True) \
            .single() \
            .execute()
        
        if not telegram_result.data:
            logger.warning(f"Aucun utilisateur Telegram trouvé pour ID {telegram_user_id}")
            return None
        
        user_id = telegram_result.data.get('user_id')
        if not user_id:
            logger.error("user_id manquant dans telegram_users")
            return None
        
        logger.debug(f"Utilisateur Telegram {telegram_user_id} lié à user_id {user_id}")
        
        # Étape 2: Récupérer les infos utilisateur depuis users
        user_result = self.supabase.table('users') \
            .select('*') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if not user_result.data:
            logger.error(f"Utilisateur {user_id} non trouvé dans table users")
            return None
        
        return user_result.data
    
    async def _check_user_capability(self, user_id: str, org_id: str, capability: str) -> bool:
        """Vérifie si l'utilisateur a une capability (ou est admin)."""
        # Vérifier si admin (bypass)
        membership = self.supabase.table('users') \
            .select('role') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .single() \
            .execute()
        
        if membership.data and membership.data.get('role') == 'admin':
            return True
        
        # Vérifier capability
        cap = self.supabase.table('user_capabilities') \
            .select('*') \
            .eq('id', user_id) \
            .eq('org_id', org_id) \
            .eq('capability_code', capability) \
            .eq('is_active', True) \
            .execute()
        
        return len(cap.data) > 0
    
    async def _perform_ocr(self, file_path: str, file_type: str) -> ExtractedInvoiceData:
        """
        OCR des factures avec Gemini Flash 1.5.
        
        En cas d'échec (Gemini désactivé, erreur API, etc.), retourne des valeurs
        par défaut pour permettre la création d'une facture à compléter manuellement.
        
        Args:
            file_path: Chemin local du fichier (/tmp/...)
            file_type: Type de fichier ('pdf' ou 'image')
            
        Returns:
            ExtractedInvoiceData avec les données extraites ou valeurs par défaut
        """
        try:
            logger.info(f"🔍 Démarrage OCR pour {file_path} (type: {file_type})")
            
            # Vérifier si Gemini est disponible
            try:
                from app.agents.generic_extractor import create_invoice_extractor
                extractor = create_invoice_extractor()
            except Exception as e:
                logger.warning(f"⚠️ Gemini non disponible: {e}")
                return self._create_fallback_extraction(file_path, file_type, 
                    "Service OCR temporairement indisponible. Veuillez remplir les informations manuellement.")
            
            # Extraire les données
            result = await extractor.extract(file_path, file_type=file_type)
            
            if result.status.value == "error":
                logger.error(f"❌ Erreur extraction: {result.errors}")
                return self._create_fallback_extraction(file_path, file_type,
                    f"Erreur OCR: {result.errors}")
            
            # Parser les données extraites
            raw_data = result.raw_data
            extracted = raw_data.get("extracted_data", {})
            
            # Extraire les informations du fournisseur
            supplier = extracted.get("supplier", {})
            amounts = extracted.get("amounts", {})
            invoice = extracted.get("invoice", {})
            
            # Extraire les lignes de détail (line_items)
            line_items = extracted.get("line_items", [])
            if line_items:
                logger.info(f"📋 {len(line_items)} ligne(s) de détail extraite(s)")
            
            # Construire l'objet ExtractedInvoiceData avec valeurs par défaut si None
            extracted_data = ExtractedInvoiceData(
                supplier_name=supplier.get("name") or "",
                supplier_address=supplier.get("address") or "",
                supplier_siret=supplier.get("siret") or "",
                amount_ht=amounts.get("ht") or 0.0,
                amount_ttc=amounts.get("ttc") or 0.0,
                vat_amount=amounts.get("vat") or 0.0,
                vat_rate=amounts.get("vat_rate") or 0.0,
                invoice_date=invoice.get("date") or "",
                due_date=invoice.get("due_date") or "",
                description=extracted.get("description") or extracted.get("notes") or "",
                invoice_number=invoice.get("number") or "",
                confidence_score=result.get_confidence_score(),
                line_items=line_items,
                raw_data={
                    "full_extraction": raw_data,
                    "model_used": result.model_used,
                    "processing_time_ms": result.processing_time_ms,
                    "file_path": file_path,
                    "file_type": file_type
                }
            )
            
            logger.info(
                f"✅ OCR terminé - Fournisseur: {extracted_data.supplier_name}, "
                f"Montant: {extracted_data.amount_ttc}€, "
                f"Confiance: {extracted_data.confidence_score:.2f}"
            )
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ Exception lors de l'OCR: {e}", exc_info=True)
            return self._create_fallback_extraction(file_path, file_type, str(e))
    
    def _create_fallback_extraction(self, file_path: str, file_type: str, 
                                    error_message: str) -> ExtractedInvoiceData:
        """Crée une extraction par défaut quand l'OCR échoue.
        
        Retourne des valeurs par défaut pour permettre la création d'une facture
        que l'utilisateur pourra compléter manuellement.
        """
        logger.info(f"📝 Création d'une extraction par défaut (fallback)")
        
        return ExtractedInvoiceData(
            supplier_name="",
            supplier_address="",
            supplier_siret="",
            amount_ht=0.0,
            amount_ttc=0.0,
            vat_amount=0.0,
            vat_rate=0.0,
            invoice_date="",
            due_date="",
            description="",
            invoice_number="",
            confidence_score=0.0,
            raw_data={
                "error": error_message,
                "fallback": True,
                "file_path": file_path,
                "file_type": file_type,
                "note": "Cette facture a été créée sans OCR. Veuillez compléter les informations manuellement."
            }
        )
    
    async def _create_draft_invoice(
        self,
        org_id: str,
        company_id: str,
        user_id: str,
        telegram_user_id: int,
        file_path: str,
        extracted_data: ExtractedInvoiceData,
        audit_log_id: str
    ) -> Dict:
        """Crée une facture en status brouillon."""
        # S'assurer que tous les champs ont des valeurs par défaut pour éviter les violations NOT NULL
        invoice_data = {
            'id': str(uuid.uuid4()),
            'org_id': org_id,
            'company_id': company_id,
            'supplier_name': extracted_data.supplier_name or 'À compléter',
            'supplier_address': extracted_data.supplier_address or '',
            'supplier_siret': extracted_data.supplier_siret or '',
            'amount_ht': extracted_data.amount_ht if extracted_data.amount_ht is not None else 0.0,
            'amount_ttc': extracted_data.amount_ttc if extracted_data.amount_ttc is not None else 0.0,
            'vat_amount': extracted_data.vat_amount if extracted_data.vat_amount is not None else 0.0,
            'vat_rate': extracted_data.vat_rate if extracted_data.vat_rate is not None else 0.0,
            'invoice_date': extracted_data.invoice_date or None,
            'due_date': extracted_data.due_date or None,
            'description': extracted_data.description or 'Facture reçue via Telegram',
            'invoice_number': extracted_data.invoice_number or '',
            'original_file_url': file_path,  # TODO: Remplacer par URL S3 quand dispo
            'status': 'brouillon',
            'created_by': user_id,
            'created_by_telegram': True,
            'ocr_data': extracted_data.raw_data or {},
            'metadata': {
                'telegram_user_id': telegram_user_id,
                'audit_log_id': audit_log_id,
                'confidence_score': extracted_data.confidence_score,
                'source': 'telegram_bot',
                'temp_file_path': file_path,
                'needs_manual_review': extracted_data.confidence_score < 0.5 or (extracted_data.amount_ttc or 0) == 0
            }
        }
        
        result = self.supabase.table('invoices').insert(invoice_data).execute()
        invoice = result.data[0] if result.data else invoice_data
        invoice_id = invoice['id']
        
        # Insérer les lignes de détail (items) si présents
        if extracted_data.line_items and len(extracted_data.line_items) > 0:
            try:
                items_data = []
                for idx, item in enumerate(extracted_data.line_items):
                    item_data = {
                        'invoice_id': invoice_id,
                        'org_id': org_id,
                        'description': item.get('description', ''),
                        'quantity': item.get('quantity'),
                        'unit_price': item.get('unit_price'),
                        'total_ht': item.get('total_ht'),
                        'vat_rate': item.get('vat_rate'),
                        'sort_order': idx
                    }
                    items_data.append(item_data)
                
                if items_data:
                    self.supabase.table('invoice_items').insert(items_data).execute()
                    logger.info(f"✅ {len(items_data)} ligne(s) de détail insérée(s) pour la facture {invoice_id}")
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'insertion des items: {e}")
                # Ne pas bloquer la création de la facture si l'insertion des items échoue
        
        return invoice
    
    async def _notify_managers(self, org_id: str, invoice_id: str, extracted_data: ExtractedInvoiceData):
        """Notifie les gérants qu'une nouvelle facture est en attente."""
        # Récupérer les gérants (admins) de l'org
        managers = self.supabase.table('users') \
            .select('user_id') \
            .eq('org_id', org_id) \
            .eq('role', 'admin') \
            .execute()
        
        if not managers.data:
            return
        
        # Envoyer notification à chaque gérant
        for manager in managers.data:
            await self.notifications.send_to_user(
                user_id=manager['user_id'],
                title="Nouvelle facture en attente",
                message=f"Une facture de {extracted_data.supplier_name or 'fournisseur inconnu'} "
                       f"pour {extracted_data.amount_ttc or 'montant inconnu'}€ est en attente de validation.",
                action_url=f"/{org_id}/construction/invoices/{invoice_id}",
                notification_type='invoice_pending_validation'
            )
