"""
Service AO (Appels d'Offres) - Gestion des candidatures et documents.

Responsabilités:
- Ingestion de dossiers de fichiers AO
- Classification automatique des documents (Gemini Flash)
- Extraction des données pricing des BPU
- Gestion du cycle de vie des candidatures
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.core.config import settings
from app.api.auth import get_supabase
from app.models.ao import (
    AOCandidatureCreate, AOCandidatureUpdate, AODocumentCreate,
    AODocumentUpdate, AOPostePricingCreate, AODocumentType,
    AOTraitementStatus, AOStatut
)
from app.agents.base.gemini_client import GeminiClient
from app.agents.generic_extractor import create_custom_extractor
from app.services.emails.embedding_service import embedding_service
from app.services.file_storage_service import file_storage_service

logger = get_logger(__name__)


class AOService:
    """Service principal pour la gestion des Appels d'Offres."""
    
    def __init__(self):
        self.client = get_supabase()
        self._gemini_flash: Optional[GeminiClient] = None
        self._gemini_pro: Optional[GeminiClient] = None
    
    def _get_gemini_flash(self) -> GeminiClient:
        """Client Gemini Flash pour tâches rapides."""
        if self._gemini_flash is None:
            self._gemini_flash = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model="gemini-2.5-flash-lite",
                temperature=0.1,
                max_output_tokens=2048
            )
        return self._gemini_flash
    
    def _get_gemini_pro(self) -> GeminiClient:
        """Client Gemini Pro pour analyses complexes."""
        if self._gemini_pro is None:
            self._gemini_pro = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model="gemini-2.5-pro",
                temperature=0.2,
                max_output_tokens=8192
            )
        return self._gemini_pro
    
    # =========================================================================
    # CANDIDATURES
    # =========================================================================
    
    async def create_candidature(
        self,
        org_id: UUID,
        data: AOCandidatureCreate,
        created_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Crée une nouvelle candidature."""
        logger.info(f"📝 Création candidature: {data.nom_projet}")
        
        insert_data = {
            "org_id": str(org_id),
            "nom_projet": data.nom_projet,
            "client_nom": data.client_nom,
            "reference_ao": data.reference_ao,
            "description": data.description,
            "dossier_id": str(data.dossier_id) if data.dossier_id else None,
            "company_id": str(data.company_id) if data.company_id else None,
            "statut": AOStatut.EN_COURS.value,
            "date_depot": data.date_depot.isoformat() if data.date_depot else None,
            "date_ouverture": data.date_ouverture.isoformat() if data.date_ouverture else None,
            "date_notification": data.date_notification.isoformat() if data.date_notification else None,
            "date_limite_remise": data.date_limite_remise.isoformat() if data.date_limite_remise else None,
            "montant_total": float(data.montant_total) if data.montant_total else None,
            "montant_maximum": float(data.montant_maximum) if data.montant_maximum else None,
            "monnaie": data.monnaie,
            "duree_travaux_jours": data.duree_travaux_jours,
            "date_debut_previsionnelle": data.date_debut_previsionnelle.isoformat() if data.date_debut_previsionnelle else None,
            "date_fin_previsionnelle": data.date_fin_previsionnelle.isoformat() if data.date_fin_previsionnelle else None,
            "created_by": str(created_by) if created_by else None
        }
        
        response = self.client.table("ao_candidatures").insert(insert_data).execute()
        
        if not response.data:
            raise Exception("Échec création candidature")
        
        logger.info(f"✅ Candidature créée: {response.data[0]['id']}")
        return response.data[0]
    
    async def get_candidature(
        self,
        candidature_id: UUID,
        org_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Récupère une candidature par ID."""
        response = self.client.table("ao_candidatures")\
            .select("*, dossiers(name, client_name)")\
            .eq("id", str(candidature_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        return response.data if response.data else None
    
    async def list_candidatures(
        self,
        org_id: UUID,
        statut: Optional[AOStatut] = None,
        dossier_id: Optional[UUID] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Liste les candidatures avec pagination."""
        query = self.client.table("ao_candidatures")\
            .select("*, dossiers(name, client_name)", count="exact")\
            .eq("org_id", str(org_id))\
            .order("created_at", desc=True)
        
        if statut:
            query = query.eq("statut", statut.value)
        if dossier_id:
            query = query.eq("dossier_id", str(dossier_id))
        
        start = (page - 1) * limit
        end = start + limit - 1
        
        response = query.range(start, end).execute()
        
        # Enrichir les données
        data = []
        for item in response.data:
            enriched = {
                **item,
                "dossier_name": item.get("dossiers", {}).get("name") if item.get("dossiers") else None,
                "dossier_client": item.get("dossiers", {}).get("client_name") if item.get("dossiers") else None
            }
            data.append(enriched)
        
        total = response.count if hasattr(response, 'count') else len(data)
        return data, total
    
    async def update_candidature(
        self,
        candidature_id: UUID,
        org_id: UUID,
        data: AOCandidatureUpdate
    ) -> Dict[str, Any]:
        """Met à jour une candidature."""
        update_data = {}
        
        if data.nom_projet is not None:
            update_data["nom_projet"] = data.nom_projet
        if data.client_nom is not None:
            update_data["client_nom"] = data.client_nom
        if data.reference_ao is not None:
            update_data["reference_ao"] = data.reference_ao
        if data.description is not None:
            update_data["description"] = data.description
        if data.statut is not None:
            update_data["statut"] = data.statut.value
        if data.date_depot is not None:
            update_data["date_depot"] = data.date_depot.isoformat()
        if data.date_ouverture is not None:
            update_data["date_ouverture"] = data.date_ouverture.isoformat()
        if data.date_notification is not None:
            update_data["date_notification"] = data.date_notification.isoformat()
        if data.date_limite_remise is not None:
            update_data["date_limite_remise"] = data.date_limite_remise.isoformat()
        if data.montant_total is not None:
            update_data["montant_total"] = float(data.montant_total)
        if data.montant_maximum is not None:
            update_data["montant_maximum"] = float(data.montant_maximum)
        if data.duree_travaux_jours is not None:
            update_data["duree_travaux_jours"] = data.duree_travaux_jours
        if data.date_debut_previsionnelle is not None:
            update_data["date_debut_previsionnelle"] = data.date_debut_previsionnelle.isoformat()
        if data.date_fin_previsionnelle is not None:
            update_data["date_fin_previsionnelle"] = data.date_fin_previsionnelle.isoformat()
        if data.ai_summary is not None:
            update_data["ai_summary"] = data.ai_summary
        if data.ai_score_gagner is not None:
            update_data["ai_score_gagner"] = data.ai_score_gagner
        
        if not update_data:
            raise ValueError("Aucune donnée à mettre à jour")
        
        response = self.client.table("ao_candidatures")\
            .update(update_data)\
            .eq("id", str(candidature_id))\
            .eq("org_id", str(org_id))\
            .execute()
        
        if not response.data:
            raise Exception("Candidature non trouvée ou non autorisée")
        
        return response.data[0]
    
    # =========================================================================
    # DOCUMENTS - INGESTION ET GESTION
    # =========================================================================
    
    async def ingest_ao_folder(
        self,
        candidature_id: UUID,
        org_id: UUID,
        folder_path: str,
        auto_classify: bool = True,
        uploaded_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Ingestion d'un dossier de fichiers AO.
        
        Args:
            candidature_id: ID de la candidature
            org_id: ID de l'organisation
            folder_path: Chemin du dossier à ingérer
            auto_classify: Classifier automatiquement les documents
            uploaded_by: ID de l'utilisateur
            
        Returns:
            Résultat de l'ingestion avec liste des documents créés
        """
        logger.info(f"📁 Ingestion dossier: {folder_path}")
        
        # Vérifier que la candidature existe
        candidature = await self.get_candidature(candidature_id, org_id)
        if not candidature:
            raise ValueError(f"Candidature {candidature_id} non trouvée")
        
        # Lister les fichiers
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Dossier non trouvé: {folder_path}")
        
        fichiers = [
            f for f in folder.iterdir()
            if f.is_file() and not f.name.startswith('.')
        ]
        
        logger.info(f"📄 {len(fichiers)} fichiers trouvés")
        
        documents_crees = []
        erreurs = []
        
        for fichier in fichiers:
            try:
                doc = await self._process_single_file(
                    candidature_id=candidature_id,
                    org_id=org_id,
                    file_path=fichier,
                    auto_classify=auto_classify,
                    uploaded_by=uploaded_by
                )
                documents_crees.append(doc)
            except Exception as e:
                logger.error(f"❌ Erreur traitement {fichier.name}: {e}")
                erreurs.append(f"{fichier.name}: {str(e)}")
        
        logger.info(f"✅ {len(documents_crees)} documents créés, {len(erreurs)} erreurs")
        
        return {
            "candidature_id": str(candidature_id),
            "fichiers_trouves": len(fichiers),
            "documents_crees": len(documents_crees),
            "erreurs": erreurs,
            "documents": documents_crees
        }
    
    async def _process_single_file(
        self,
        candidature_id: UUID,
        org_id: UUID,
        file_path: Path,
        auto_classify: bool,
        uploaded_by: Optional[UUID]
    ) -> Dict[str, Any]:
        """Traite un fichier unique."""
        logger.info(f"📄 Traitement: {file_path.name}")
        
        # Lire le fichier
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Calculer le checksum
        checksum = hashlib.sha256(file_data).hexdigest()
        
        # Stocker le fichier - essayer S3/R2 d'abord, fallback local si échec
        storage_key = None
        
        try:
            # Essayer S3/R2
            storage_key = await file_storage_service.store_file(
                file_data=file_data,
                filename=file_path.name,
                org_id=str(org_id),
                folder="ao"
            )
            logger.info(f"✅ Fichier stocké sur S3/R2: {storage_key}")
        except Exception as s3_error:
            # Fallback: stockage local temporaire (pour développement/test)
            logger.warning(f"⚠️ S3/R2 échoué, fallback local: {s3_error}")
            
            # Créer le chemin local
            local_path = f"/tmp/ao/{org_id}/{candidature_id}/{file_path.name}"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Sauvegarder localement
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            storage_key = local_path
            logger.info(f"📁 Fichier stocké localement: {local_path}")
        
        # Créer le document en DB
        doc_data = {
            "candidature_id": str(candidature_id),
            "org_id": str(org_id),
            "nom_fichier": file_path.name,
            "type_doc": AODocumentType.AUTRE.value,  # Par défaut, sera mis à jour si auto_classify
            "url_stockage": storage_key,
            "mime_type": self._detect_mime_type(file_path.suffix),
            "taille_bytes": len(file_data),
            "checksum": checksum,
            "statut_traitement": AOTraitementStatus.PENDING.value,
            "uploaded_by": str(uploaded_by) if uploaded_by else None
        }
        
        response = self.client.table("ao_documents").insert(doc_data).execute()
        document = response.data[0]
        
        # Classification automatique si demandée
        if auto_classify:
            try:
                classification = await self.classify_document(
                    document_id=UUID(document["id"]),
                    file_data=file_data,
                    filename=file_path.name
                )
                document["type_doc"] = classification["type_doc_detecte"]
                document["metadata"] = classification["metadata_extrait"]
            except Exception as e:
                logger.warning(f"⚠️ Classification échouée pour {file_path.name}: {e}")
        
        return document
    
    def _detect_mime_type(self, extension: str) -> str:
        """Détecte le MIME type depuis l'extension."""
        mapping = {
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }
        return mapping.get(extension.lower(), 'application/octet-stream')
    
    async def classify_document(
        self,
        document_id: UUID,
        file_data: Optional[bytes] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classifie un document et extrait les métadonnées via Gemini Flash.
        
        Args:
            document_id: ID du document
            file_data: Données binaires (optionnel, sinon lu depuis DB)
            filename: Nom du fichier (optionnel)
            
        Returns:
            Résultat de la classification avec type_doc et metadata
        """
        logger.info(f"🔍 Classification document: {document_id}")
        
        # Récupérer le document
        doc_response = self.client.table("ao_documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise ValueError(f"Document {document_id} non trouvé")
        
        document = doc_response.data
        org_id = UUID(document["org_id"])
        
        # Mettre à jour le statut
        self.client.table("ao_documents")\
            .update({"statut_traitement": AOTraitementStatus.PROCESSING.value})\
            .eq("id", str(document_id))\
            .execute()
        
        try:
            # Lire le fichier si non fourni
            if file_data is None:
                with open(document["url_stockage"], 'rb') as f:
                    file_data = f.read()
            
            filename = filename or document["nom_fichier"]
            
            # Construire le prompt de classification
            system_prompt = """Tu es un expert en analyse de documents d'appels d'offres BTP.
Analyse ce document et identifie:
1. Son type (RC, CCTP, BPU, DAO, MEMOIRE, DQE, GARANTIE, REJET, ATTRIBUE, NEGociation ou AUTRE)
2. Les métadonnées clés (client, projet, dates, etc.)

Réponds UNIQUEMENT en JSON avec ce format:
{
  "type_doc": "RC",
  "confidence": 0.95,
  "metadata": {
    "client_nom": "Nom du client",
    "projet_nom": "Nom du projet",
    "date_document": "2024-01-15",
    "reference": "Référence AO",
    "pages": 12
  }
}"""
            
            # Appel Gemini Flash
            gemini = self._get_gemini_flash()
            
            # Détecter le type de fichier et extraire
            extension = Path(filename).suffix.lower()
            
            from google.genai import types
            
            if extension == '.pdf':
                user_content = types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=system_prompt),
                        types.Part.from_bytes(data=file_data, mime_type="application/pdf")
                    ]
                )
            elif extension in ['.jpg', '.jpeg', '.png']:
                mime_type = 'image/jpeg' if extension in ['.jpg', '.jpeg'] else 'image/png'
                user_content = types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=system_prompt),
                        types.Part.from_bytes(data=file_data, mime_type=mime_type)
                    ]
                )
            else:
                # Pour les autres formats, extraire le texte si possible
                try:
                    text_content = file_data.decode('utf-8')
                    user_content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=f"{system_prompt}\n\nContenu du fichier:\n{text_content[:5000]}")]
                    )
                except:
                    # Fallback: analyser juste le nom
                    user_content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=f"{system_prompt}\n\nNom du fichier: {filename}")]
                    )
            
            config = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )
            
            response = gemini._client.models.generate_content(
                model=gemini.model_name,
                contents=[user_content],
                config=config
            )
            
            # Parser le résultat
            result = json.loads(response.text)
            
            type_doc = result.get("type_doc", "AUTRE")
            confidence = result.get("confidence", 0.5)
            metadata = result.get("metadata", {})
            
            # Mettre à jour le document en DB
            update_data = {
                "type_doc": type_doc,
                "metadata": metadata,
                "statut_traitement": AOTraitementStatus.PROCESSED.value,
                "date_extraction": datetime.utcnow().isoformat(),
                "model_extraction": "gemini-2.5-flash-lite"
            }
            
            self.client.table("ao_documents")\
                .update(update_data)\
                .eq("id", str(document_id))\
                .execute()
            
            logger.info(f"✅ Document classifié: {type_doc} (confiance: {confidence})")
            
            return {
                "document_id": str(document_id),
                "type_doc_detecte": type_doc,
                "confidence": confidence,
                "metadata_extrait": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur classification: {e}")
            
            # Mettre à jour avec erreur
            self.client.table("ao_documents")\
                .update({
                    "statut_traitement": AOTraitementStatus.ERROR.value,
                    "message_erreur": str(e)[:500]
                })\
                .eq("id", str(document_id))\
                .execute()
            
            raise
    
    async def list_documents(
        self,
        candidature_id: UUID,
        org_id: UUID,
        type_doc: Optional[AODocumentType] = None
    ) -> List[Dict[str, Any]]:
        """Liste les documents d'une candidature."""
        query = self.client.table("ao_documents")\
            .select("*")\
            .eq("candidature_id", str(candidature_id))\
            .eq("org_id", str(org_id))\
            .order("created_at", desc=True)
        
        if type_doc:
            query = query.eq("type_doc", type_doc.value)
        
        response = query.execute()
        return response.data or []
    
    # =========================================================================
    # EXTRACTION PRICING (BPU)
    # =========================================================================
    
    async def extract_pricing_data(
        self,
        document_id: UUID,
        org_id: UUID
    ) -> Dict[str, Any]:
        """
        Extrait les postes pricing d'un document BPU via Gemini Pro.
        
        Args:
            document_id: ID du document BPU
            org_id: ID de l'organisation
            
        Returns:
            Postes extraits avec leurs prix et quantités
        """
        logger.info(f"💰 Extraction pricing document: {document_id}")
        
        # Récupérer le document
        doc_response = self.client.table("ao_documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise ValueError(f"Document {document_id} non trouvé")
        
        document = doc_response.data
        candidature_id = UUID(document["candidature_id"])
        
        # Lire le fichier
        with open(document["url_stockage"], 'rb') as f:
            file_data = f.read()
        
        # Construire le prompt d'extraction
        system_prompt = """Tu es un expert en chiffrage BTP. Extrais tous les postes du BPU.

Pour chaque poste, identifie:
- numero: numéro de poste (ex: "01.01.001")
- description: libellé complet
- unite: unité (m2, m3, ml, forfait, u, kg, etc.)
- quantite: quantité (nombre décimal)
- prix_unitaire_ht: prix unitaire hors taxe
- prix_total_ht: total HT (quantite × prix_unitaire_ht)
- categorie: catégorie (GROS_OEUVRE, SECOND_OEUVRE, EQUIPEMENT, ETANCHEITE, MENUISERIE, etc.)

Réponds en JSON:
{
  "postes": [
    {
      "numero": "01.01.001",
      "description": "Béton armé - Fondations",
      "unite": "m3",
      "quantite": 150.5,
      "prix_unitaire_ht": 850.00,
      "prix_total_ht": 127925.00,
      "categorie": "GROS_OEUVRE"
    }
  ],
  "montant_total_ht": 1250000.00,
  "nombre_postes": 45
}"""
        
        try:
            gemini = self._get_gemini_pro()
            
            from google.genai import types
            
            extension = Path(document["nom_fichier"]).suffix.lower()
            
            if extension == '.pdf':
                user_content = types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=system_prompt),
                        types.Part.from_bytes(data=file_data, mime_type="application/pdf")
                    ]
                )
            elif extension == '.csv':
                # Pour CSV, lire directement
                text_content = file_data.decode('utf-8')
                user_content = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"{system_prompt}\n\nContenu CSV:\n{text_content[:10000]}")]
                )
            else:
                # Essayer de décoder comme texte
                try:
                    text_content = file_data.decode('utf-8')
                    user_content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=f"{system_prompt}\n\nContenu:\n{text_content[:10000]}")]
                    )
                except:
                    raise ValueError(f"Format non supporté: {extension}")
            
            config = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )
            
            response = gemini._client.models.generate_content(
                model=gemini.model_name,
                contents=[user_content],
                config=config
            )
            
            # Parser le résultat
            result = json.loads(response.text)
            postes = result.get("postes", [])
            
            # Créer les postes en DB
            postes_crees = []
            for idx, poste_data in enumerate(postes):
                try:
                    poste_create = AOPostePricingCreate(
                        candidature_id=candidature_id,
                        document_id=document_id,
                        numero=poste_data.get("numero", f"LIGNE_{idx+1}"),
                        description=poste_data.get("description", ""),
                        unite=poste_data.get("unite"),
                        quantite=Decimal(str(poste_data["quantite"])) if poste_data.get("quantite") else None,
                        prix_unitaire_ht=Decimal(str(poste_data["prix_unitaire_ht"])) if poste_data.get("prix_unitaire_ht") else None,
                        prix_total_ht=Decimal(str(poste_data["prix_total_ht"])) if poste_data.get("prix_total_ht") else None,
                        categorie=poste_data.get("categorie"),
                        ligne_bpu=idx + 1
                    )
                    
                    insert_data = {
                        "candidature_id": str(poste_create.candidature_id),
                        "document_id": str(poste_create.document_id),
                        "org_id": str(org_id),
                        "numero": poste_create.numero,
                        "description": poste_create.description,
                        "description_normalisee": poste_create.description.lower().strip() if poste_create.description else None,
                        "unite": poste_create.unite,
                        "quantite": float(poste_create.quantite) if poste_create.quantite else None,
                        "prix_unitaire_ht": float(poste_create.prix_unitaire_ht) if poste_create.prix_unitaire_ht else None,
                        "prix_total_ht": float(poste_create.prix_total_ht) if poste_create.prix_total_ht else None,
                        "categorie": poste_create.categorie,
                        "ligne_bpu": poste_create.ligne_bpu
                    }
                    
                    resp = self.client.table("ao_postes_pricing").insert(insert_data).execute()
                    if resp.data:
                        postes_crees.append(resp.data[0])
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erreur création poste {idx}: {e}")
            
            # Mettre à jour le document
            montant_total = sum(
                float(p["prix_total_ht"]) for p in postes 
                if p.get("prix_total_ht")
            )
            
            self.client.table("ao_documents")\
                .update({
                    "metadata": {
                        **document.get("metadata", {}),
                        "extraction_pricing": {
                            "nombre_postes": len(postes_crees),
                            "montant_total_ht": montant_total,
                            "date_extraction": datetime.utcnow().isoformat()
                        }
                    }
                })\
                .eq("id", str(document_id))\
                .execute()
            
            logger.info(f"✅ {len(postes_crees)} postes extraits")
            
            return {
                "document_id": str(document_id),
                "postes_extraits": len(postes_crees),
                "montant_total_ht": Decimal(str(montant_total)) if montant_total else None,
                "postes": postes_crees[:50]  # Limiter la réponse
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction pricing: {e}")
            raise
    
    async def get_postes_pricing(
        self,
        candidature_id: UUID,
        org_id: UUID,
        categorie: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Récupère les postes pricing d'une candidature."""
        query = self.client.table("ao_postes_pricing")\
            .select("*")\
            .eq("candidature_id", str(candidature_id))\
            .eq("org_id", str(org_id))\
            .order("ligne_bpu")
        
        if categorie:
            query = query.eq("categorie", categorie)
        
        response = query.execute()
        return response.data or []

    # =========================================================================
    # OCR ET EXTRACTION DE TEXTE
    # =========================================================================
    
    async def extract_document_text(
        self,
        document_id: UUID,
        org_id: UUID
    ) -> Dict[str, Any]:
        """
        Extrait le texte d'un document via OCR (Gemini) et met à jour le document.
        
        Args:
            document_id: ID du document
            org_id: ID de l'organisation
            
        Returns:
            Résultat de l'extraction avec texte et métadonnées
        """
        logger.info(f"🔍 Extraction OCR document: {document_id}")
        
        # Récupérer le document
        doc_response = self.client.table("ao_documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise ValueError(f"Document {document_id} non trouvé")
        
        document = doc_response.data
        file_path = document["url_stockage"]
        
        # Vérifier si c'est une clé R2 (commence par test/ ou prod/) ou un chemin local
        cleanup_temp = False
        
        if file_path.startswith(('test/', 'prod/')):
            # C'est une clé R2, vérifier si on a une copie locale
            # Format R2: test/org/{org_id}/ao/{timestamp}_{filename}
            # Format local: /tmp/ao/{org_id}/{candidature_id}/{filename}
            
            # Extraire le nom de fichier original (après le timestamp_)
            import glob
            import re
            full_filename = Path(file_path).name
            
            # Le format est {timestamp}_{filename} où timestamp peut être:
            # - YYYYMMDD_HHMMSS_ffffff (date_heure_microsecondes)
            # - YYYYMMDD_HHMMSS (date_heure)
            # On essaie de détecter et extraire le nom de fichier original
            
            # Pattern pour timestamp: YYYYMMDD_HHMMSS_ffffff ou YYYYMMDD_HHMMSS
            timestamp_pattern = r'^\d{8}_\d{6}(?:_\d{6})?_'
            
            if re.match(timestamp_pattern, full_filename):
                # Supprimer le timestamp (tout jusqu'au dernier '_' du timestamp)
                match = re.match(r'^(\d{8}_\d{6}(?:_\d{6})?)_(.*)$', full_filename)
                if match:
                    original_filename = match.group(2)
                else:
                    original_filename = full_filename
            else:
                # Pas de timestamp détecté, utiliser le nom complet
                original_filename = full_filename
            
            # Essayer de trouver le fichier local
            # Chercher dans /tmp/ao/{org_id}/*/{original_filename} ET avec le nom complet
            local_patterns = [
                f"/tmp/ao/{org_id}/*/{original_filename}",  # Nom original
                f"/tmp/ao/{org_id}/*/{full_filename}",      # Nom complet avec timestamp
                f"/tmp/ao/{org_id}/*/*{Path(original_filename).suffix}"  # Tous les fichiers avec la même extension
            ]
            
            local_files = []
            for pattern in local_patterns:
                found = glob.glob(pattern)
                if found:
                    local_files.extend(found)
                    break  # Prendre le premier pattern qui trouve
            
            if local_files:
                file_path = local_files[0]
                logger.debug(f"📁 Fichier local trouvé: {file_path}")
            else:
                # Télécharger depuis R2
                logger.info(f"📥 Téléchargement depuis R2: {file_path}")
                from app.services.file_storage_service import file_storage_service
                file_data = await file_storage_service.get_file(file_path)
                
                if not file_data:
                    raise FileNotFoundError(f"Fichier non trouvé sur R2: {file_path}")
                
                # Sauvegarder temporairement
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix)
                temp_file.write(file_data)
                temp_file.close()
                file_path = temp_file.name
                cleanup_temp = True
                logger.debug(f"📁 Fichier téléchargé temporairement: {file_path}")
        
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
        
        try:
            # Créer un extracteur personnalisé pour les documents AO
            extractor = create_custom_extractor(
                document_type="ao_document",
                fields={
                    "content": "Contenu textuel complet du document",
                    "title": "Titre ou sujet du document",
                    "metadata": "Métadonnées extraites (dates, références, etc.)"
                },
                instructions="""
                Extrais le contenu textuel complet de ce document d'appel d'offres.
                Pour un tableau (BPU), extrais les données en format structuré.
                Pour un document texte, extrais tout le contenu lisible.
                """
            )
            
            # Extraire le contenu
            result = await extractor.extract(file_path)
            
            # Récupérer le texte extrait
            extracted_text = result.get_extracted_text()
            
            # Compter les pages (approximation pour les fichiers texte)
            nombre_pages = extracted_text.count("\n\n") // 40 + 1 if extracted_text else 0
            
            # Mettre à jour le document dans la base
            update_data = {
                "contenu_texte": extracted_text[:50000],  # Limiter à 50k caractères
                "nombre_pages": nombre_pages,
                "statut_traitement": AOTraitementStatus.PROCESSED.value,
                "date_extraction": datetime.utcnow().isoformat(),
                "model_extraction": "gemini-ocr"
            }
            
            self.client.table("ao_documents")\
                .update(update_data)\
                .eq("id", str(document_id))\
                .execute()
            
            logger.info(f"✅ OCR terminé: {len(extracted_text)} caractères extraits")
            
            # Nettoyer le fichier temporaire si créé
            if cleanup_temp and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.debug(f"🧹 Fichier temporaire nettoyé: {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Erreur nettoyage fichier temporaire: {e}")
            
            return {
                "document_id": str(document_id),
                "text_length": len(extracted_text),
                "pages": nombre_pages,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur OCR: {e}")
            
            # Nettoyer le fichier temporaire si créé (même en cas d'erreur)
            if cleanup_temp and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.debug(f"🧹 Fichier temporaire nettoyé (erreur): {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Erreur nettoyage fichier temporaire: {e}")
            
            # Mettre à jour avec statut erreur
            self.client.table("ao_documents")\
                .update({
                    "statut_traitement": AOTraitementStatus.ERROR.value,
                    "message_erreur": f"OCR failed: {str(e)[:500]}"
                })\
                .eq("id", str(document_id))\
                .execute()
            raise
    
    # =========================================================================
    # VECTORISATION
    # =========================================================================
    
    async def vectorize_document(
        self,
        document_id: UUID,
        org_id: UUID,
        candidature_id: UUID
    ) -> Dict[str, Any]:
        """
        Vectorise un document en chunks et stocke dans ao_embeddings.
        Réutilise le EmbeddingService existant pour les emails.
        
        Args:
            document_id: ID du document
            org_id: ID de l'organisation
            candidature_id: ID de la candidature
            
        Returns:
            Résultat de la vectorisation
        """
        logger.info(f"📊 Vectorisation document: {document_id}")
        
        # Récupérer le document avec son contenu
        doc_response = self.client.table("ao_documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise ValueError(f"Document {document_id} non trouvé")
        
        document = doc_response.data
        content = document.get("contenu_texte", "")
        
        if not content:
            logger.warning(f"⚠️ Pas de contenu à vectoriser pour {document_id}")
            return {"document_id": str(document_id), "chunks_created": 0}
        
        try:
            # Chunker le texte avec le service existant
            chunks = embedding_service.chunk_text(content)
            
            chunks_crees = 0
            for idx, chunk in enumerate(chunks):
                try:
                    # Générer l'embedding via le service existant
                    embedding = await embedding_service.generate_embedding(chunk)
                    
                    # Insérer dans ao_embeddings
                    insert_data = {
                        "doc_id": str(document_id),
                        "candidature_id": str(candidature_id),
                        "org_id": str(org_id),
                        "content": chunk,
                        "embedding": embedding,
                        "tags": [document.get("type_doc", "document"), "ao"],
                        "chunk_index": idx,
                        "chunk_total": len(chunks)
                    }
                    
                    self.client.table("ao_embeddings").insert(insert_data).execute()
                    chunks_crees += 1
                    
                except Exception as chunk_error:
                    logger.warning(f"⚠️ Erreur chunk {idx}: {chunk_error}")
            
            logger.info(f"✅ {chunks_crees}/{len(chunks)} chunks vectorisés")
            
            return {
                "document_id": str(document_id),
                "chunks_created": chunks_crees,
                "total_chunks": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur vectorisation: {e}")
            raise
    
    # =========================================================================
    # UPLOAD INDIVIDUEL DE FICHIERS
    # =========================================================================
    
    async def upload_document(
        self,
        candidature_id: UUID,
        org_id: UUID,
        file_data: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        uploaded_by: Optional[UUID] = None,
        process_ocr: bool = True,
        vectorize: bool = True
    ) -> Dict[str, Any]:
        """
        Upload un fichier individuel et l'associe à une candidature AO.
        Exécute OCR et vectorisation si demandé.
        
        Args:
            candidature_id: ID de la candidature
            org_id: ID de l'organisation
            file_data: Données binaires du fichier
            filename: Nom du fichier
            mime_type: Type MIME (optionnel, auto-détecté si non fourni)
            uploaded_by: ID de l'utilisateur
            process_ocr: Si True, lance l'OCR après upload
            vectorize: Si True, vectorise le document après OCR
            
        Returns:
            Document créé avec métadonnées
        """
        logger.info(f"📤 Upload fichier: {filename} pour candidature {candidature_id}")
        
        # Vérifier que la candidature existe
        candidature = await self.get_candidature(candidature_id, org_id)
        if not candidature:
            raise ValueError(f"Candidature {candidature_id} non trouvée")
        
        # Calculer le checksum
        checksum = hashlib.sha256(file_data).hexdigest()
        
        # Stocker le fichier - essayer S3/R2 d'abord, fallback local si échec
        safe_filename = Path(filename).name
        storage_key = None
        local_temp_path = None
        
        try:
            # Essayer S3/R2
            storage_key = await file_storage_service.store_file(
                file_data=file_data,
                filename=safe_filename,
                org_id=str(org_id),
                folder="ao"
            )
            logger.info(f"✅ Fichier stocké sur S3/R2: {storage_key}")
            
            # Sauvegarder aussi localement temporairement pour OCR
            local_temp_path = f"/tmp/ao/{org_id}/{candidature_id}/{safe_filename}"
            os.makedirs(os.path.dirname(local_temp_path), exist_ok=True)
            with open(local_temp_path, 'wb') as f:
                f.write(file_data)
            logger.debug(f"📁 Copie locale pour OCR: {local_temp_path}")
            
        except Exception as s3_error:
            # Fallback: stockage local temporaire (pour développement/test)
            logger.warning(f"⚠️ S3/R2 échoué, fallback local: {s3_error}")
            
            # Créer le chemin local
            local_temp_path = f"/tmp/ao/{org_id}/{candidature_id}/{safe_filename}"
            os.makedirs(os.path.dirname(local_temp_path), exist_ok=True)
            
            # Sauvegarder localement
            with open(local_temp_path, 'wb') as f:
                f.write(file_data)
            
            storage_key = local_temp_path
            logger.info(f"📁 Fichier stocké localement: {local_temp_path}")
        
        # Détecter le type MIME si non fourni
        if not mime_type:
            mime_type = self._detect_mime_type(Path(filename).suffix)
        
        # Créer le document en DB
        doc_data = {
            "candidature_id": str(candidature_id),
            "org_id": str(org_id),
            "nom_fichier": filename,
            "type_doc": AODocumentType.AUTRE.value,
            "url_stockage": storage_key,
            "mime_type": mime_type,
            "taille_bytes": len(file_data),
            "checksum": checksum,
            "statut_traitement": AOTraitementStatus.PENDING.value,
            "uploaded_by": str(uploaded_by) if uploaded_by else None
        }
        
        response = self.client.table("ao_documents").insert(doc_data).execute()
        document = response.data[0]
        document_id = UUID(document["id"])
        
        logger.info(f"✅ Document créé: {document_id}")
        
        result = {
            "document_id": str(document_id),
            "filename": filename,
            "mime_type": mime_type,
            "size": len(file_data),
            "ocr_status": "pending",
            "vectorization_status": "pending"
        }
        
        # Lancer l'OCR si demandé
        if process_ocr:
            try:
                ocr_result = await self.extract_document_text(document_id, org_id)
                result["ocr_status"] = "completed"
                result["text_length"] = ocr_result.get("text_length", 0)
                
                # Lancer la vectorisation si OCR réussi
                if vectorize and ocr_result.get("text_length", 0) > 0:
                    vector_result = await self.vectorize_document(
                        document_id, org_id, candidature_id
                    )
                    result["vectorization_status"] = "completed"
                    result["chunks_created"] = vector_result.get("chunks_created", 0)
                    
            except Exception as e:
                logger.error(f"❌ Erreur traitement document: {e}")
                result["ocr_status"] = "error"
                result["error"] = str(e)
        
        return result
    
    async def process_existing_document(
        self,
        document_id: UUID,
        org_id: UUID,
        process_ocr: bool = True,
        vectorize: bool = True
    ) -> Dict[str, Any]:
        """
        Traite un document existant (OCR + vectorisation).
        Utile pour re-traiter des documents ou traiter en arrière-plan.
        
        Args:
            document_id: ID du document
            org_id: ID de l'organisation
            process_ocr: Si True, lance l'OCR
            vectorize: Si True, vectorise le document
            
        Returns:
            Résultat du traitement
        """
        logger.info(f"🔄 Traitement document existant: {document_id}")
        
        # Récupérer le document
        doc_response = self.client.table("ao_documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise ValueError(f"Document {document_id} non trouvé")
        
        document = doc_response.data
        candidature_id = UUID(document["candidature_id"])
        
        result = {
            "document_id": str(document_id),
            "filename": document["nom_fichier"]
        }
        
        # OCR si demandé
        if process_ocr:
            try:
                ocr_result = await self.extract_document_text(document_id, org_id)
                result["ocr"] = ocr_result
            except Exception as e:
                result["ocr_error"] = str(e)
        
        # Vectorisation si demandée et contenu existe
        if vectorize:
            try:
                # Vérifier si du contenu existe
                if document.get("contenu_texte") or result.get("ocr", {}).get("text_length", 0) > 0:
                    vector_result = await self.vectorize_document(
                        document_id, org_id, candidature_id
                    )
                    result["vectorization"] = vector_result
                else:
                    result["vectorization"] = {"skipped": True, "reason": "no_content"}
            except Exception as e:
                result["vectorization_error"] = str(e)
        
        return result

    # =========================================================================
    # UPLOAD DOSSIER ZIP + CREATION AUTO CANDIDATURE
    # =========================================================================

    async def analyze_and_create_from_folder(
        self,
        org_id: UUID,
        folder_path: str,
        uploaded_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Analyse un dossier contenant des documents AO, extrait les métadonnées clés,
        crée une candidature et lie tous les documents.

        Args:
            org_id: ID de l'organisation
            folder_path: Chemin du dossier contenant les documents
            uploaded_by: ID de l'utilisateur

        Returns:
            Candidature créée avec résumé des documents
        """
        logger.info(f"📁 Analyse dossier AO: {folder_path}")

        folder = Path(folder_path)
        logger.info(f"  Folder exists: {folder.exists()}, is_dir: {folder.is_dir()}")
        
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Dossier non trouvé: {folder_path}")

        # Lister tous les fichiers (récursivement)
        all_items = list(folder.rglob('*'))
        logger.info(f"  Total items found (rglob): {len(all_items)}")
        
        # Debug: afficher tous les items trouvés
        logger.debug(f"  DEBUG - Tous les items rglob:")
        for i, item in enumerate(all_items[:20]):  # Limiter à 20 pour éviter trop de logs
            logger.debug(f"    {i+1}. {item.relative_to(folder)} (is_file: {item.is_file()}, is_dir: {item.is_dir()}, suffix: {item.suffix})")
        
        fichiers = [
            f for f in all_items
            if f.is_file() and not f.name.startswith('.') and f.suffix.lower() != '.zip'
        ]

        logger.info(f"📄 {len(fichiers)} fichiers trouvés: {[str(f.relative_to(folder)) for f in fichiers[:10]]}")

        if not fichiers:
            # Debug: lister le contenu du dossier
            logger.error(f"  DEBUG - Contenu de {folder}:")
            for item in folder.iterdir():
                logger.error(f"    {item.name} (is_file: {item.is_file()}, is_dir: {item.is_dir()})")
            raise ValueError("Aucun fichier trouvé dans le dossier")

        logger.info(f"📄 {len(fichiers)} fichiers trouvés")

        # Phase 1: Analyser les documents pour extraire les métadonnées clés
        # On analyse d'abord le RC et le BPU pour extraire les infos
        analyse_result = await self._analyze_folder_metadata(folder_path, fichiers)

        # Phase 2: Créer la candidature avec les métadonnées extraites
        candidature_data = AOCandidatureCreate(
            nom_projet=analyse_result.get("nom_projet", f"AO Import - {folder.name}"),
            client_nom=analyse_result.get("client_nom"),
            reference_ao=analyse_result.get("reference_ao"),
            description=analyse_result.get("description"),
            date_limite_remise=analyse_result.get("date_limite_remise"),
            montant_total=analyse_result.get("montant_total"),
            duree_travaux_jours=analyse_result.get("duree_travaux_jours"),
        )

        candidature = await self.create_candidature(
            org_id=org_id,
            data=candidature_data,
            created_by=uploaded_by
        )

        candidature_id = UUID(candidature["id"])
        logger.info(f"✅ Candidature créée: {candidature_id}")

        # Phase 3: Ingérer et traiter tous les documents
        documents_crees = []
        documents_errors = []

        for fichier in fichiers:
            try:
                # Utiliser le chemin relatif pour conserver la structure
                relative_path = fichier.relative_to(folder)
                
                # Upload avec OCR et vectorisation
                with open(fichier, 'rb') as f:
                    file_data = f.read()

                result = await self.upload_document(
                    candidature_id=candidature_id,
                    org_id=org_id,
                    file_data=file_data,
                    filename=str(relative_path),
                    uploaded_by=uploaded_by,
                    process_ocr=True,
                    vectorize=True
                )

                documents_crees.append({
                    "filename": str(relative_path),
                    "document_id": result.get("document_id"),
                    "type_doc": self._detect_document_type(fichier.name),
                    "status": "success"
                })

            except Exception as e:
                logger.error(f"❌ Erreur traitement {fichier.name}: {e}")
                documents_errors.append({
                    "filename": str(relative_path),
                    "error": str(e)
                })

        # Phase 4: Extraire les postes pricing si BPU présent
        postes_extraits = 0
        bpu_docs = [d for d in documents_crees if d.get("type_doc") == "BPU"]
        for bpu in bpu_docs:
            try:
                extract_result = await self.extract_pricing_data(
                    UUID(bpu["document_id"]),
                    org_id
                )
                postes_extraits += extract_result.get("postes_extraits", 0)
            except Exception as e:
                logger.warning(f"⚠️ Extraction pricing échouée: {e}")

        logger.info(f"✅ Traitement terminé: {len(documents_crees)} docs, {postes_extraits} postes")

        return {
            "candidature": candidature,
            "documents_created": len(documents_crees),
            "documents_errors": documents_errors,
            "postes_extraits": postes_extraits,
            "metadata_extracted": analyse_result
        }

    async def _analyze_folder_metadata(
        self,
        folder_path: str,
        fichiers: List[Path]
    ) -> Dict[str, Any]:
        """
        Analyse les documents du dossier pour extraire les métadonnées clés.
        Lit les fichiers RC et BPU pour extraire les infos structurées.
        """
        logger.info("🔍 Extraction métadonnées du dossier...")

        # Chercher le fichier RC ou un fichier qui semble être le RC
        rc_file = None
        bpu_file = None

        for f in fichiers:
            name_upper = f.name.upper()
            if "RC" in name_upper or "REGLEMENT" in name_upper:
                rc_file = f
            if "BPU" in name_upper or "PRIX" in name_upper or f.suffix.lower() == '.csv':
                bpu_file = f

        metadata = {
            "nom_projet": None,
            "client_nom": None,
            "reference_ao": None,
            "description": None,
            "date_limite_remise": None,
            "montant_total": None,
            "duree_travaux_jours": None,
        }

        # Analyser le RC avec Gemini pour extraire les métadonnées
        if rc_file:
            try:
                logger.info(f"📄 Analyse RC: {rc_file.name}")

                # Utiliser Gemini pour extraire les métadonnées
                gemini = self._get_gemini_flash()

                with open(rc_file, 'rb') as f:
                    file_data = f.read()

                from google.genai import types

                prompt = """Analyse ce document de consultation (RC ou DAO) et extrais les informations suivantes en JSON:
{
  "nom_projet": "Nom du projet",
  "client_nom": "Nom du maître d'ouvrage/client",
  "reference_ao": "Référence de l'appel d'offres",
  "description": "Description courte du projet",
  "date_limite_remise": "YYYY-MM-DD",
  "duree_travaux_jours": nombre,
  "montant_maximum": nombre (si mentionné)
}

Retourne UNIQUEMENT le JSON, sans autre texte."""

                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_bytes(data=file_data, mime_type="application/pdf")
                        ]
                    )
                ]

                config = types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                    response_mime_type="application/json"
                )

                response = gemini._client.models.generate_content(
                    model=gemini.model_name,
                    contents=contents,
                    config=config
                )

                result = json.loads(response.text)

                # Mapper les résultats
                metadata["nom_projet"] = result.get("nom_projet")
                metadata["client_nom"] = result.get("client_nom")
                metadata["reference_ao"] = result.get("reference_ao")
                metadata["description"] = result.get("description")

                if result.get("date_limite_remise"):
                    try:
                        from datetime import datetime
                        metadata["date_limite_remise"] = datetime.strptime(
                            result["date_limite_remise"], "%Y-%m-%d"
                        ).date()
                    except:
                        pass

                if result.get("duree_travaux_jours"):
                    metadata["duree_travaux_jours"] = int(result["duree_travaux_jours"])

                logger.info(f"✅ Métadonnées extraites: {metadata['nom_projet']}")

            except Exception as e:
                logger.warning(f"⚠️ Erreur extraction métadonnées RC: {e}")

        # Analyser le BPU pour extraire le montant total
        if bpu_file:
            try:
                logger.info(f"📊 Analyse BPU: {bpu_file.name}")

                with open(bpu_file, 'rb') as f:
                    file_data = f.read()

                # Pour CSV, lire directement
                if bpu_file.suffix.lower() == '.csv':
                    try:
                        content = file_data.decode('utf-8')
                        # Chercher le montant total dans les dernières lignes
                        lines = content.split('\n')
                        for line in reversed(lines[-5:]):
                            if 'TOTAL' in line.upper():
                                # Extraire le dernier nombre
                                import re
                                numbers = re.findall(r'[\d\s]+,?\d*', line)
                                if numbers:
                                    montant_str = numbers[-1].replace(' ', '').replace(',', '.')
                                    try:
                                        metadata["montant_total"] = float(montant_str)
                                        break
                                    except:
                                        pass
                    except:
                        pass
                else:
                    # Pour PDF, utiliser Gemini
                    gemini = self._get_gemini_flash()

                    from google.genai import types

                    prompt = "Extrais le montant total HT du bordereau des prix. Réponds uniquement avec le nombre."

                    contents = [
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=prompt),
                                types.Part.from_bytes(data=file_data, mime_type="application/pdf")
                            ]
                        )
                    ]

                    response = gemini._client.models.generate_content(
                        model=gemini.model_name,
                        contents=contents
                    )

                    try:
                        metadata["montant_total"] = float(response.text.strip())
                    except:
                        pass

            except Exception as e:
                logger.warning(f"⚠️ Erreur extraction montant BPU: {e}")

        # Fallback: utiliser le nom du dossier si pas de nom de projet
        if not metadata["nom_projet"]:
            folder_name = Path(folder_path).name
            metadata["nom_projet"] = f"AO - {folder_name}"

        return metadata

    def _detect_document_type(self, filename: str) -> str:
        """Détecte le type de document basé sur le nom."""
        name_upper = filename.upper()
        if "RC" in name_upper or "REGLEMENT" in name_upper:
            return "RC"
        if "CCTP" in name_upper:
            return "CCTP"
        if "BPU" in name_upper or "PRIX" in name_upper:
            return "BPU"
        if "DAO" in name_upper:
            return "DAO"
        if "MEMOIRE" in name_upper:
            return "MEMOIRE"
        if "DQE" in name_upper:
            return "DQE"
        return "AUTRE"

    async def upload_and_create_from_zip(
        self,
        org_id: UUID,
        zip_data: bytes,
        filename: str,
        uploaded_by: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Décompresse un ZIP, analyse le contenu et crée une candidature.

        Args:
            org_id: ID de l'organisation
            zip_data: Données binaires du fichier ZIP
            filename: Nom du fichier ZIP
            uploaded_by: ID de l'utilisateur

        Returns:
            Résultat de la création avec candidature et documents
        """
        import zipfile
        import tempfile

        logger.info(f"📦 Décompression ZIP: {filename}")

        # Créer un dossier temporaire
        tmpdir = tempfile.mkdtemp()
        try:
            zip_path = Path(tmpdir) / filename

            # Sauvegarder le ZIP
            with open(zip_path, 'wb') as f:
                f.write(zip_data)

            # Extraire
            extract_folder = Path(tmpdir) / "extracted"
            extract_folder.mkdir()

            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_folder)
                    logger.info(f"  Extraction réussie: {len(zip_ref.namelist())} fichiers")
            except zipfile.BadZipFile:
                raise ValueError("Fichier ZIP invalide")

            # Trouver le dossier racine (s'il y a un seul dossier à la racine)
            root_items = list(extract_folder.iterdir())
            logger.info(f"  Éléments à la racine: {[i.name for i in root_items]}")
            
            if len(root_items) == 1 and root_items[0].is_dir():
                folder_to_process = root_items[0]
            else:
                folder_to_process = extract_folder

            # Lancer l'analyse et création
            result = await self.analyze_and_create_from_folder(
                org_id=org_id,
                folder_path=str(folder_to_process),
                uploaded_by=uploaded_by
            )
            
            return result
            
        finally:
            # Nettoyer le dossier temporaire
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# Instance singleton
ao_service = AOService()
