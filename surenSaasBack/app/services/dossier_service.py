"""
Service de gestion des Dossiers (Le Classeur).

Responsabilités:
- CRUD des dossiers
- Liaison/déliaison des threads
- Génération de résumés cross-threads
- Suggestions IA de liaison
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.core.logging import get_logger
from app.api.auth import get_supabase
from app.models.dossiers import (
    DossierCreate, DossierUpdate, DossierDetail, DossierListItem,
    SuggestedDossier, LinkThreadToDossierRequest
)

logger = get_logger(__name__)


class DossierService:
    """Service de gestion des dossiers."""
    
    def __init__(self):
        self.client = get_supabase()
    
    def create_dossier(
        self,
        org_id: UUID,
        company_id: Optional[UUID],
        data: DossierCreate
    ) -> DossierDetail:
        """
        Crée un nouveau dossier.
        
        Args:
            org_id: ID de l'organisation
            company_id: ID de l'entreprise (optionnel)
            data: Données du dossier
            
        Returns:
            Le dossier créé
        """
        logger.info(f"📁 Création dossier '{data.name}' pour org {org_id}")
        
        dossier_data = {
            "org_id": str(org_id),
            "company_id": str(company_id) if company_id else None,
            "name": data.name,
            "client_name": data.client_name,
            "client_email": data.client_email,
            "address": data.address,
            "project_type": data.project_type,
            "budget_estimate": float(data.budget_estimate) if data.budget_estimate else None,
            "deadline": data.deadline.isoformat() if data.deadline else None,
            "status": "active",
            "thread_count": 0,
            "document_count": 0
        }
        
        response = self.client.table("dossiers").insert(dossier_data).execute()
        
        if not response.data:
            raise Exception("Échec création dossier")
        
        dossier = response.data[0]
        logger.info(f"✅ Dossier créé: {dossier['id']}")
        
        return DossierDetail(**dossier)
    
    def get_dossier(
        self,
        dossier_id: UUID,
        org_id: UUID
    ) -> Optional[DossierDetail]:
        """
        Récupère un dossier par son ID.
        
        Args:
            dossier_id: ID du dossier
            org_id: ID de l'organisation (pour sécurité)
            
        Returns:
            Le dossier ou None si non trouvé
        """
        response = self.client.table("dossiers")\
            .select("*")\
            .eq("id", str(dossier_id))\
            .eq("org_id", str(org_id))\
            .maybe_single()\
            .execute()
        
        if response.data:
            return DossierDetail(**response.data)
        return None
    
    def list_dossiers(
        self,
        org_id: UUID,
        company_id: Optional[UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Liste les dossiers avec filtres et pagination.
        
        Args:
            org_id: ID de l'organisation
            company_id: Filtre par entreprise
            status: Filtre par statut
            search: Recherche textuelle (nom, client, adresse)
            page: Numéro de page
            limit: Nombre par page
            
        Returns:
            { data: [...], total: int, page: int, limit: int }
        """
        query = self.client.table("dossiers")\
            .select("*", count="exact")\
            .eq("org_id", str(org_id))
        
        if company_id:
            query = query.eq("company_id", str(company_id))
        
        if status:
            query = query.eq("status", status)
        
        if search:
            # Recherche sur nom, client_name ou address
            query = query.or_(f"name.ilike.%{search}%,client_name.ilike.%{search}%,address.ilike.%{search}%")
        
        # Tri par date de mise à jour
        query = query.order("updated_at", desc=True)
        
        # Pagination
        start = (page - 1) * limit
        query = query.range(start, start + limit - 1)
        
        response = query.execute()
        
        return {
            "data": [DossierListItem(**item) for item in response.data],
            "total": response.count if hasattr(response, 'count') else len(response.data),
            "page": page,
            "limit": limit
        }
    
    def update_dossier(
        self,
        dossier_id: UUID,
        org_id: UUID,
        data: DossierUpdate
    ) -> DossierDetail:
        """
        Met à jour un dossier.
        
        Args:
            dossier_id: ID du dossier
            org_id: ID de l'organisation
            data: Données à mettre à jour
            
        Returns:
            Le dossier mis à jour
        """
        update_data = {k: v for k, v in data.dict(exclude_unset=True).items() if v is not None}
        
        if not update_data:
            raise ValueError("Aucune donnée à mettre à jour")
        
        # Conversion des types
        if "budget_estimate" in update_data and update_data["budget_estimate"]:
            update_data["budget_estimate"] = float(update_data["budget_estimate"])
        if "deadline" in update_data and update_data["deadline"]:
            update_data["deadline"] = update_data["deadline"].isoformat()
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = self.client.table("dossiers")\
            .update(update_data)\
            .eq("id", str(dossier_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if not response.data:
            raise Exception("Dossier non trouvé ou pas de modification")
        
        return DossierDetail(**response.data[0])
    
    def delete_dossier(
        self,
        dossier_id: UUID,
        org_id: UUID
    ) -> bool:
        """
        Supprime un dossier (soft delete en passant status à 'cancelled').
        
        Args:
            dossier_id: ID du dossier
            org_id: ID de l'organisation
            
        Returns:
            True si supprimé
        """
        logger.info(f"🗑️ Suppression dossier {dossier_id}")
        
        # Soft delete: on met le status à cancelled
        # Les threads liés restent mais avec dossier_id = NULL
        response = self.client.table("dossiers")\
            .update({"status": "cancelled", "updated_at": datetime.utcnow().isoformat()})\
            .eq("id", str(dossier_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if response.data:
            logger.info(f"✅ Dossier {dossier_id} marqué comme cancelled")
            return True
        return False
    
    def link_thread_to_dossier(
        self,
        thread_id: UUID,
        org_id: UUID,
        request: LinkThreadToDossierRequest
    ) -> DossierDetail:
        """
        Lie un thread à un dossier (existant ou nouveau).
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            request: Dossier existant ou création
            
        Returns:
            Le dossier (existant ou créé)
        """
        if request.create_new:
            if not request.new_dossier_name:
                raise ValueError("Nom requis pour créer un nouveau dossier")
            
            # Créer le dossier
            dossier = self.create_dossier(
                org_id=org_id,
                company_id=None,  # Sera déduit du thread
                data=DossierCreate(name=request.new_dossier_name)
            )
            dossier_id = dossier.id
        else:
            if not request.dossier_id:
                raise ValueError("dossier_id requis si pas de création")
            dossier_id = request.dossier_id
        
        # Lier le thread
        response = self.client.table("email_threads")\
            .update({"dossier_id": str(dossier_id)})\
            .eq("id", str(thread_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if not response.data:
            raise Exception("Thread non trouvé")
        
        logger.info(f"✅ Thread {thread_id} lié au dossier {dossier_id}")
        
        # Retourner le dossier mis à jour
        return self.get_dossier(dossier_id, org_id)
    
    def unlink_thread_from_dossier(
        self,
        thread_id: UUID,
        org_id: UUID
    ) -> bool:
        """
        Délie un thread de son dossier.
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            
        Returns:
            True si délié
        """
        response = self.client.table("email_threads")\
            .update({"dossier_id": None})\
            .eq("id", str(thread_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if response.data:
            logger.info(f"✅ Thread {thread_id} délié de son dossier")
            return True
        return False
    
    def get_threads_in_dossier(
        self,
        dossier_id: UUID,
        org_id: UUID,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Récupère les threads liés à un dossier.
        
        Args:
            dossier_id: ID du dossier
            org_id: ID de l'organisation
            page: Page
            limit: Limite
            
        Returns:
            Liste des threads
        """
        start = (page - 1) * limit
        
        response = self.client.table("email_threads")\
            .select("*")\
            .eq("dossier_id", str(dossier_id))\
            .eq("org_id", str(org_id))\
            .order("last_email_at", desc=True)\
            .range(start, start + limit - 1)\
            .execute()
        
        return response.data
    
    def get_documents_in_dossier(
        self,
        dossier_id: UUID,
        org_id: UUID
    ) -> Dict[str, Any]:
        """
        Récupère les documents (PJ) de tous les threads d'un dossier.
        
        Args:
            dossier_id: ID du dossier
            org_id: ID de l'organisation
            
        Returns:
            { total: int, by_type: { "devis": [...], ... } }
        """
        # Récupérer tous les threads du dossier
        threads_response = self.client.table("email_threads")\
            .select("gmail_thread_id")\
            .eq("dossier_id", str(dossier_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if not threads_response.data:
            return {"total": 0, "by_type": {}}
        
        thread_ids = [t["gmail_thread_id"] for t in threads_response.data]
        
        # Récupérer les emails de ces threads
        emails_response = self.client.table("emails")\
            .select("id")\
            .in_("gmail_thread_id", thread_ids)\
            .execute()
        
        if not emails_response.data:
            return {"total": 0, "by_type": {}}
        
        email_ids = [e["id"] for e in emails_response.data]
        
        # Récupérer les pièces jointes
        attachments_response = self.client.table("email_attachments")\
            .select("*")\
            .in_("email_id", email_ids)\
            .execute()
        
        # Grouper par type (basé sur filename patterns)
        by_type = {"devis": [], "facture": [], "plan": [], "photo": [], "autre": []}
        
        for att in attachments_response.data:
            filename = att.get("filename", "").lower()
            
            if any(kw in filename for kw in ["devis", "quote", "estimation"]):
                by_type["devis"].append(att)
            elif any(kw in filename for kw in ["facture", "invoice", "billing"]):
                by_type["facture"].append(att)
            elif any(kw in filename for kw in ["plan", "drawing", "schema", "dxf", "dwg"]):
                by_type["plan"].append(att)
            elif any(kw in filename for kw in [".jpg", ".jpeg", ".png", ".gif", "photo", "img"]):
                by_type["photo"].append(att)
            else:
                by_type["autre"].append(att)
        
        total = len(attachments_response.data)
        
        return {
            "total": total,
            "by_type": by_type
        }
    
    async def suggest_dossiers_for_thread(
        self,
        thread_id: UUID,
        org_id: UUID
    ) -> List[SuggestedDossier]:
        """
        Suggère des dossiers existants pour un thread donné (IA).
        
        Stratégie:
        1. Extraire entités du thread (client, adresse)
        2. Comparer avec dossiers existants
        3. Scoring basé sur similarité textuelle
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            
        Returns:
            Liste des suggestions classées par confiance
        """
        # Récupérer le thread (sans jointure - les emails sont liés via gmail_thread_id)
        thread_response = self.client.table("email_threads")\
            .select("id, subject, participant_names, participant_emails, ai_context, gmail_thread_id")\
            .eq("id", str(thread_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not thread_response.data:
            return []
        
        thread = thread_response.data
        
        # Extraire entités (client_name, address du thread)
        client_name = None
        if thread.get("participant_names") and len(thread["participant_names"]) > 0:
            client_name = thread["participant_names"][0]
        elif thread.get("participant_emails") and len(thread["participant_emails"]) > 0:
            # Extraire le nom de l'email (partie avant @)
            email = thread["participant_emails"][0]
            client_name = email.split("@")[0] if "@" in email else email
        
        # Récupérer les dossiers actifs de l'org
        dossiers_response = self.client.table("dossiers")\
            .select("*")\
            .eq("org_id", str(org_id))\
            .eq("status", "active")\
            .execute()
        
        if not dossiers_response.data:
            return []
        
        suggestions = []
        
        for dossier in dossiers_response.data:
            score = 0.0
            reasons = []
            
            # Matching client_name
            if client_name and dossier.get("client_name"):
                if client_name.lower() in dossier["client_name"].lower() or \
                   dossier["client_name"].lower() in client_name.lower():
                    score += 0.5
                    reasons.append(f"Même client: {dossier['client_name']}")
            
            # Matching adresse (si disponible)
            if thread.get("ai_context") and dossier.get("address"):
                # Simple matching - pourrait être amélioré avec NLP
                thread_context = thread["ai_context"].lower()
                dossier_address = dossier["address"].lower()
                
                # Extraire code postal ou rue
                if any(word in thread_context for word in dossier_address.split()[:3]):
                    score += 0.4
                    reasons.append(f"Adresse similaire: {dossier['address'][:30]}...")
            
            # Bonus si plusieurs threads déjà liés (chantier actif)
            if dossier.get("thread_count", 0) > 0:
                score += 0.1
            
            if score >= 0.5:  # Threshold
                suggestions.append(SuggestedDossier(
                    dossier_id=dossier["id"],
                    name=dossier["name"],
                    client_name=dossier.get("client_name"),
                    confidence=min(score, 1.0),
                    reason="; ".join(reasons) if reasons else "Correspondance détectée"
                ))
        
        # Trier par confiance décroissante
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        return suggestions[:5]  # Max 5 suggestions
    
    async def generate_cross_thread_summary(
        self,
        dossier_id: UUID,
        org_id: UUID
    ) -> str:
        """
        Génère un résumé cross-threads pour un dossier (IA Gemini).
        
        Args:
            dossier_id: ID du dossier
            org_id: ID de l'organisation
            
        Returns:
            Résumé texte généré
        """
        # Récupérer les threads avec leurs analyses IA
        threads = self.get_threads_in_dossier(dossier_id, org_id, limit=50)
        
        if not threads:
            return "Aucun email dans ce dossier."
        
        # Construire le contexte pour Gemini
        context = {
            "dossier": self.get_dossier(dossier_id, org_id).dict(),
            "threads": [
                {
                    "subject": t["subject"],
                    "ai_summary": t.get("ai_summary", ""),
                    "email_count": t["email_count"],
                    "ai_status": t["ai_status"],
                    "ai_urgency": t["ai_urgency"]
                }
                for t in threads
            ]
        }
        
        # TODO: Appel Gemini pour générer le résumé
        # Pour l'instant, résumé basique
        summary = f"Dossier '{context['dossier']['name']}' avec {len(threads)} conversation(s). "
        
        if context["dossier"]["client_name"]:
            summary += f"Client: {context['dossier']['client_name']}. "
        
        urgent_threads = [t for t in threads if t["ai_urgency"] == "high"]
        if urgent_threads:
            summary += f"{len(urgent_threads)} sujet(s) marqué(s) comme urgent(s). "
        
        # Mettre à jour le résumé en DB
        self.client.table("dossiers")\
            .update({
                "ai_summary": summary,
                "ai_summary_updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", str(dossier_id))\
            .execute()
        
        return summary


# Instance singleton
dossier_service = DossierService()
