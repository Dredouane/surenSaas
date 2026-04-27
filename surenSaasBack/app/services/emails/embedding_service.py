"""
Service de vectorisation avec Vertex AI.

Génère les embeddings avec text-embedding-004 et stratégie Matryoshka.
"""

import os
import asyncio
import json
import base64
import tempfile
from typing import List, Dict, Any, Optional
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger
from app.services.email_database_service import email_db

logger = get_logger(__name__)

# Import Vertex AI (sera installé via requirements)
try:
    import vertexai
    from vertexai.language_models import TextEmbeddingModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logger.warning("Vertex AI not available, embeddings will fail")


class EmbeddingService:
    """Service de génération d'embeddings avec Vertex AI."""
    
    def __init__(self):
        self.model = None
        self.chunk_size = int(os.getenv("EMBEDDING_CHUNK_SIZE", 500))
        self.chunk_overlap = int(os.getenv("EMBEDDING_CHUNK_OVERLAP", 50))
        self.embedding_size = int(os.getenv("EMBEDDING_SIZE", 768))
        
        # Initialisation lazy du modèle
        self._initialized = False
    
    def _init_vertex_ai(self):
        """Initialise Vertex AI (appelé une seule fois)."""
        if self._initialized or not VERTEX_AI_AVAILABLE:
            return
        
        from app.core.config import settings
        
        project_id = os.getenv("VERTEX_AI_PROJECT_ID") or settings.gcp_project_id
        location = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
        credentials_info = None
        
        # Essayer d'extraire depuis les credentials Gemini si toujours pas de project_id
        if settings.gemini_api_key:
            try:
                creds_json = base64.b64decode(settings.gemini_api_key)
                credentials_info = json.loads(creds_json)
                if not project_id:
                    project_id = credentials_info.get("project_id")
            except Exception as e:
                logger.warning(f"Could not decode Gemini credentials: {e}")
        
        if not project_id:
            raise ValueError("VERTEX_AI_PROJECT_ID or GCP_PROJECT_ID not set")
        
        # Créer fichier temporaire pour les credentials si on a des credentials_info
        if credentials_info:
            fd, creds_file = tempfile.mkstemp(suffix='.json')
            with os.fdopen(fd, 'w') as f:
                json.dump(credentials_info, f)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file
            logger.debug(f"Credentials temp file created")
        
        vertexai.init(project=project_id, location=location)
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        self._initialized = True
        self._creds_file = creds_file  # Stocker pour suppression plus tard
        logger.info(f"Vertex AI embedding model initialized - Project: {project_id}, Location: {location}")
        
        # Restreindre les permissions du fichier (chmod 600)
        try:
            os.chmod(creds_file, 0o600)
            logger.debug("Credentials file permissions restricted to 600")
        except Exception as e:
            logger.warning(f"Could not restrict credentials file permissions: {e}")
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Découpe le texte en chunks avec overlap.
        
        Args:
            text: Texte à découper
            
        Returns:
            Liste de chunks
        """
        # Tokenization simple (approximation par mots)
        # Pour une tokenization plus précise, utiliser tiktoken ou autre
        words = text.split()
        
        chunks = []
        start = 0
        
        while start < len(words):
            # Extraire chunk
            end = min(start + self.chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            
            # Avancer avec overlap
            start += self.chunk_size - self.chunk_overlap
            
            # Éviter les chunks vides à la fin
            if start >= len(words):
                break
        
        return chunks
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Génère l'embedding pour un texte.
        
        Args:
            text: Texte à vectoriser
            
        Returns:
            Vecteur d'embeddings (768 dimensions)
        """
        if not VERTEX_AI_AVAILABLE:
            raise RuntimeError("Vertex AI not available")
        
        self._init_vertex_ai()
        
        # Vertex AI n'est pas async nativement, on wrap dans un thread
        loop = asyncio.get_event_loop()
        
        def _embed():
            embeddings = self.model.get_embeddings([text])
            return embeddings[0].values
        
        vector = await loop.run_in_executor(None, _embed)
        
        # Matryoshka slicing (si on veut réduire, mais 768 est déjà optimal)
        if self.embedding_size < len(vector):
            vector = vector[:self.embedding_size]
        
        return vector
    
    async def vectorize_email_async(self, email_id: str):
        """
        Vectorise un email de manière asynchrone.
        
        Cette méthode est conçue pour être appelée via asyncio.create_task()
        afin de ne pas bloquer le flux principal.
        
        Args:
            email_id: UUID de l'email à vectoriser
        """
        try:
            logger.info(f"Starting vectorization for email {email_id}")
            
            # 1. Récupérer l'email
            email = await email_db.get_email_by_id(email_id)
            
            if not email:
                logger.error(f"Email {email_id} not found")
                return
            
            org_id = email["org_id"]
            company_id = email["company_id"]
            content_text = email.get("content_text", "")
            
            # 2. Mettre à jour le statut
            await email_db.update_email_status(email_id, "processing")
            
            # 3. Vectoriser le corps de l'email
            if content_text:
                chunks = self.chunk_text(content_text)
                
                for idx, chunk in enumerate(chunks):
                    vector = await self.generate_embedding(chunk)
                    
                    await email_db.create_embedding({
                        "org_id": org_id,
                        "company_id": company_id,
                        "email_id": email_id,
                        "source_type": "email_body",
                        "source_id": email_id,
                        "content_chunk": chunk,
                        "embedding": vector,
                        "chunk_index": idx,
                        "chunk_total": len(chunks),
                        "model_name": "text-embedding-004"
                    })
            
            # 4. Vectoriser les pièces jointes (OCR)
            attachments = await email_db.get_attachments_by_email(email_id)
            
            for attachment in attachments:
                ocr_text = attachment.get("ocr_text", "")
                if ocr_text:
                    chunks = self.chunk_text(ocr_text)
                    
                    for idx, chunk in enumerate(chunks):
                        vector = await self.generate_embedding(chunk)
                        
                        await email_db.create_embedding({
                            "org_id": org_id,
                            "company_id": company_id,
                            "email_id": email_id,
                            "source_type": "attachment",
                            "source_id": attachment["id"],
                            "content_chunk": chunk,
                            "embedding": vector,
                            "chunk_index": idx,
                            "chunk_total": len(chunks),
                            "model_name": "text-embedding-004"
                        })
            
            # 5. Mettre à jour le statut final
            await email_db.update_email_status(email_id, "vectorized")
            
            logger.info(f"Vectorization completed for email {email_id}")
            
            # 6. Déclencher l'analyse par la Secrétaire IA (asynchrone)
            try:
                from app.services.secretariat_service import secretariat_service
                asyncio.create_task(
                    secretariat_service.analyze_new_email(email_id)
                )
                logger.info(f"🤖 Secrétaire: Analyse déclenchée pour email {email_id}")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de déclencher la Secrétaire: {e}")
            
        except Exception as e:
            logger.error(f"Error vectorizing email {email_id}: {e}")
            
            # Mettre à jour le statut d'erreur
            await email_db.update_email_status(email_id, "error", str(e))
            
            raise
    
    def close(self):
        """Ferme le service et nettoie les ressources."""
        if hasattr(self, '_creds_file') and self._creds_file and os.path.exists(self._creds_file):
            try:
                os.remove(self._creds_file)
                logger.debug("Credentials temp file deleted")
            except Exception as e:
                logger.warning(f"Could not delete temp credentials file: {e}")
    
    def __del__(self):
        """Destructeur - nettoie les ressources."""
        self.close()


# Instance singleton
embedding_service = EmbeddingService()
