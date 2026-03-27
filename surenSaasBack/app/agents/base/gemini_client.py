"""
Client Google Gemini pour l'extraction de documents.

Utilise uniquement google-genai (pas google.cloud.aiplatform).
Supporte deux modes :
1. Vertex AI avec Service Account (via google-genai)
2. Google AI Studio avec API Key
"""

import os
import base64
import json
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """
    Client pour interagir avec l'API Google Gemini via google-genai.
    
    Supporte :
    - Vertex AI avec Service Account
    - Google AI Studio avec API Key
    """
    
    def __init__(
        self,
        credentials_b64: Optional[str] = None,
        project_id: Optional[str] = None,
        location: str = "europe-west1",
        model: str = "gemini-1.5-flash-001",
        temperature: float = 0.1,
        max_output_tokens: int = 8192
    ):
        """
        Initialise le client Gemini.
        
        Args:
            credentials_b64: Service Account JSON encodé en base64 (Vertex AI)
            project_id: ID du projet GCP (pour Vertex AI)
            location: Région GCP
            model: Nom du modèle Gemini
            temperature: Créativité (0.0 = déterministe)
            max_output_tokens: Tokens max en sortie
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location
        self.model_name = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self._client = None
        self._types = None
        self._credentials_file = None
        
        # Importer ici pour éviter les erreurs si non installé
        from google import genai
        from google.genai import types
        
        self._genai = genai
        self._types = types
        
        # Détecter le mode d'authentification
        if credentials_b64:
            # Mode Vertex AI avec Service Account
            self._init_vertex_ai(credentials_b64)
        elif os.getenv("GEMINI_API_KEY"):
            # Mode AI Studio avec API Key
            self._init_ai_studio(os.getenv("GEMINI_API_KEY"))
        else:
            raise ValueError(
                "Aucune méthode d'authentification Gemini configurée. "
                "Veuillez définir GOOGLE_GEMINI_CREDENTIALS_B64 ou GEMINI_API_KEY"
            )
        
        logger.info(f"✅ GeminiClient initialisé - Model: {model}, Location: {location}")
    
    def _init_vertex_ai(self, credentials_b64: str):
        """Initialise Vertex AI avec Service Account via google-genai."""
        try:
            # Décoder les credentials
            credentials_json = base64.b64decode(credentials_b64).decode('utf-8')
            credentials_info = json.loads(credentials_json)
            
            # Extraire project_id si non fourni
            project_id = self.project_id or credentials_info.get("project_id")
            if not project_id:
                raise ValueError("Project ID non trouvé dans les credentials")
            
            # Créer fichier temporaire pour les credentials
            fd, self._credentials_file = tempfile.mkstemp(suffix='.json')
            with os.fdopen(fd, 'w') as f:
                json.dump(credentials_info, f)
            
            # Définir la variable d'environnement pour l'authentification
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._credentials_file
            
            # Initialiser le client Vertex AI avec google-genai
            self._client = self._genai.Client(
                vertexai=True,
                project=project_id,
                location=self.location
            )
            
            logger.info(f"✅ Vertex AI initialisé - Project: {project_id}, Location: {self.location}")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Vertex AI: {e}")
            raise
    
    def _init_ai_studio(self, api_key: str):
        """Initialise AI Studio avec API Key."""
        try:
            self._client = self._genai.Client(api_key=api_key)
            logger.info(f"✅ AI Studio initialisé avec API Key")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation AI Studio: {e}")
            raise
    
    def _create_config(self):
        """Crée la configuration de génération."""
        return self._types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            response_mime_type="application/json"
        )
    
    def extract_from_image(self, image_data: bytes, prompt: str, mime_type: str = "image/jpeg") -> str:
        """Extrait du texte depuis une image."""
        try:
            config = self._create_config()
            
            # Créer le contenu avec texte + image
            contents = [
                self._types.Content(
                    role="user",
                    parts=[
                        self._types.Part.from_text(text=prompt),
                        self._types.Part.from_bytes(data=image_data, mime_type=mime_type)
                    ]
                )
            ]
            
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction image: {e}")
            raise
    
    def extract_from_pdf(self, pdf_data: bytes, prompt: str) -> str:
        """Extrait du texte depuis un PDF."""
        try:
            config = self._create_config()
            
            # Créer le contenu avec texte + PDF
            contents = [
                self._types.Content(
                    role="user",
                    parts=[
                        self._types.Part.from_text(text=prompt),
                        self._types.Part.from_bytes(data=pdf_data, mime_type="application/pdf")
                    ]
                )
            ]
            
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction PDF: {e}")
            raise
    
    def extract_from_file(self, file_path: str, prompt: str) -> str:
        """Extrait du texte depuis un fichier local."""
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
            
            # Lire le fichier
            with open(path, 'rb') as f:
                file_data = f.read()
            
            logger.info(f"📄 Fichier lu: {len(file_data)} bytes")
            
            # Détecter le type et extraire
            extension = path.suffix.lower()
            if extension == '.pdf':
                return self.extract_from_pdf(file_data, prompt)
            elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                mime_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }.get(extension, 'image/jpeg')
                return self.extract_from_image(file_data, prompt, mime_type)
            else:
                raise ValueError(f"Type de fichier non supporté: {extension}")
                
        except Exception as e:
            logger.error(f"❌ Erreur extraction fichier: {e}")
            raise
    
    def close(self):
        """Ferme le client et nettoie les ressources."""
        if self._credentials_file and os.path.exists(self._credentials_file):
            try:
                os.remove(self._credentials_file)
                logger.debug("🗑️ Credentials temporaires supprimés")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de supprimer les credentials: {e}")
    
    def __del__(self):
        """Destructeur."""
        self.close()


if __name__ == "__main__":
    print("🧪 Test GeminiClient")
    print("Pour tester: python -m pytest tests/test_ocr_integration.py -v")
