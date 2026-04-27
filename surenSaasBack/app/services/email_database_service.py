"""
Service database pour le module Emails.

Gère les interactions avec Supabase pour les tables emails, email_accounts, 
email_attachments et email_embeddings.

Note: Ce service est dédié au module Emails. Les autres modules utilisent
app.api.auth.get_supabase() directement.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

# Import du client Supabase existant
from app.api.auth import get_supabase


class EmailDatabaseService:
    """Service de base de données pour les opérations liées aux emails."""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        """Lazy loading du client Supabase."""
        if self._client is None:
            self._client = get_supabase()
        return self._client
    
    # ============================================
    # Email Accounts
    # ============================================
    
    async def create_email_account(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un compte email."""
        response = self.client.table("email_accounts").insert(data).execute()
        return response.data[0] if response.data else None
    
    async def get_email_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un compte email par ID."""
        response = self.client.table("email_accounts")\
            .select("*")\
            .eq("id", account_id)\
            .single()\
            .execute()
        return response.data if response.data else None
    
    async def get_email_accounts_by_org(self, org_id: str) -> List[Dict[str, Any]]:
        """Liste les comptes email d'une organisation."""
        response = self.client.table("email_accounts")\
            .select("*")\
            .eq("org_id", org_id)\
            .execute()
        return response.data if response.data else []
    
    async def update_email_account(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour un compte email."""
        response = self.client.table("email_accounts")\
            .update(data)\
            .eq("id", account_id)\
            .execute()
        return response.data[0] if response.data else None
    
    # ============================================
    # Emails
    # ============================================
    
    async def create_email(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un email."""
        try:
            response = self.client.table("emails").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            err_str = str(e)
            # Si colonne dedup_hash manquante, retry sans
            if "dedup_hash" in err_str and "PGRST204" in err_str:
                data_no_hash = {k: v for k, v in data.items() if k != "dedup_hash"}
                response = self.client.table("emails").insert(data_no_hash).execute()
                return response.data[0] if response.data else None
            raise
    
    async def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un email par son ID."""
        response = self.client.table("emails")\
            .select("*")\
            .eq("id", email_id)\
            .single()\
            .execute()
        return response.data if response.data else None
    
    async def get_email_by_message_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un email par son Gmail message ID."""
        try:
            response = self.client.table("emails")\
                .select("*")\
                .eq("gmail_message_id", message_id)\
                .single()\
                .execute()
            return response.data if response.data else None
        except Exception:
            return None

    async def get_email_by_dedup_hash(self, dedup_hash: str, org_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un email par son hash de déduplication."""
        try:
            response = self.client.table("emails")\
                .select("*")\
                .eq("dedup_hash", dedup_hash)\
                .eq("org_id", str(org_id))\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        except Exception:
            return None
    
    async def get_emails_by_thread(self, thread_id: str, org_id: str) -> List[Dict[str, Any]]:
        """Récupère les emails d'un thread."""
        response = self.client.table("emails")\
            .select("*")\
            .eq("gmail_thread_id", thread_id)\
            .eq("org_id", org_id)\
            .order("sent_at")\
            .execute()
        return response.data if response.data else []
    
    async def update_email(self, email_id: str, data: Dict[str, Any]):
        """Met à jour un email."""
        response = self.client.table("emails")\
            .update(data)\
            .eq("id", email_id)\
            .execute()
        return response.data[0] if response.data else None
    
    async def delete_email(self, email_id: str) -> bool:
        """Supprime un email et ses pièces jointes."""
        try:
            # Supprimer d'abord les pièces jointes
            self.client.table("email_attachments")\
                .delete()\
                .eq("email_id", email_id)\
                .execute()
            
            # Supprimer les embeddings
            self.client.table("email_embeddings")\
                .delete()\
                .eq("email_id", email_id)\
                .execute()
            
            # Supprimer l'email
            response = self.client.table("emails")\
                .delete()\
                .eq("id", email_id)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting email {email_id}: {e}")
            return False
    
    async def update_email_status(self, email_id: str, status: str, error: str = None):
        """Met à jour le statut de traitement d'un email."""
        data = {"processing_status": status}
        if error:
            data["processing_error"] = error
        self.client.table("emails").update(data).eq("id", email_id).execute()
    
    async def list_emails(self, filters: Dict[str, Any], limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Liste les emails avec filtres."""
        query = self.client.table("emails").select("*")
        
        if "org_id" in filters:
            query = query.eq("org_id", filters["org_id"])
        if "company_id" in filters:
            query = query.eq("company_id", filters["company_id"])
        if "account_id" in filters:
            query = query.eq("email_account_id", filters["account_id"])
        if "status" in filters:
            query = query.eq("processing_status", filters["status"])
        if "thread_id" in filters:
            query = query.eq("gmail_thread_id", filters["thread_id"])
        
        query = query.order("sent_at", desc=True).limit(limit).offset(offset)
        response = query.execute()
        return response.data if response.data else []
    
    # ============================================
    # Email Attachments
    # ============================================
    
    async def create_attachment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée une pièce jointe."""
        response = self.client.table("email_attachments").insert(data).execute()
        return response.data[0] if response.data else None
    
    async def get_attachments_by_email(self, email_id: str) -> List[Dict[str, Any]]:
        """Récupère les pièces jointes d'un email."""
        response = self.client.table("email_attachments")\
            .select("*")\
            .eq("email_id", email_id)\
            .execute()
        return response.data if response.data else []
    
    async def update_attachment_ocr(self, attachment_id: str, ocr_text: str, confidence: float):
        """Met à jour les résultats OCR d'une pièce jointe."""
        self.client.table("email_attachments").update({
            "ocr_text": ocr_text,
            "ocr_confidence": confidence,
            "is_processed": True,
            "ocr_processed_at": datetime.utcnow().isoformat()
        }).eq("id", attachment_id).execute()
    
    # ============================================
    # Email Embeddings
    # ============================================
    
    async def create_embedding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un embedding."""
        response = self.client.table("email_embeddings").insert(data).execute()
        return response.data[0] if response.data else None
    
    async def search_similar_emails(
        self,
        query_embedding: List[float],
        org_id: str,
        company_id: Optional[str] = None,
        match_threshold: float = 0.7,
        match_count: int = 10
    ) -> List[Dict[str, Any]]:
        """Recherche par similarité vectorielle."""
        params = {
            "query_embedding": query_embedding,
            "target_org_id": org_id,
            "match_threshold": match_threshold,
            "match_count": match_count
        }
        if company_id:
            params["target_company_id"] = company_id
            
        response = self.client.rpc("search_similar_emails", params).execute()
        return response.data if response.data else []
    
    async def get_embeddings_by_email(self, email_id: str) -> List[Dict[str, Any]]:
        """Récupère les embeddings d'un email."""
        response = self.client.table("email_embeddings")\
            .select("*")\
            .eq("email_id", email_id)\
            .execute()
        return response.data if response.data else []
    
    # ============================================
    # Cleanup (pour les tests)
    # ============================================
    
    async def cleanup_test_data(self):
        """Supprime les données de test (pour les tests uniquement)."""
        self.client.table("email_embeddings").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        self.client.table("email_attachments").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        self.client.table("emails").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        self.client.table("email_accounts").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()


# Instance singleton
email_db = EmailDatabaseService()
