"""
Client Google Gemini pour l'extraction de documents.

Utilise uniquement google-genai (pas google.cloud.aiplatform).
Supporte deux modes :
1. Vertex AI avec Service Account (via google-genai, startup centralisé)
2. Google AI Studio avec API Key
"""

import os
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from app.core.logging import get_logger
from app.core import vertex as vertex_service

logger = get_logger(__name__)


class GeminiClient:
    """
    Client pour interagir avec l'API Google Gemini via google-genai.
    
    Supporte :
    - Vertex AI avec Service Account (credentials gérés par app.core.vertex)
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
            credentials_b64: Ignoré en mode Vertex AI (géré par vertex.py)
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
        
        from google.genai import types
        
        self._types = types
        
        # Détecter le mode d'authentification
        if os.getenv("GEMINI_API_KEY") and not credentials_b64:
            self._init_ai_studio(os.getenv("GEMINI_API_KEY"))
        else:
            # Mode Vertex AI — utilise le singleton centralisé
            vertex_service.startup()
            self._client = vertex_service.get_genai_client()
        
        logger.info(f"✅ GeminiClient initialisé - Model: {model}, Location: {location}")
    
    def _init_ai_studio(self, api_key: str):
        """Initialise AI Studio avec API Key."""
        try:
            from google import genai as _genai
            self._client = _genai.Client(api_key=api_key)
            logger.info("✅ AI Studio initialisé avec API Key")
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
        """Extrait du texte depuis un PDF complet."""
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
    
    def extract_from_pdf_pages(
        self, 
        pdf_data: bytes, 
        prompt: str,
        page_range: Optional[Tuple[int, int]] = None,
        max_pages: Optional[int] = None,
        fallback_on_error: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extrait des données de pages spécifiques d'un PDF.
        
        Args:
            pdf_data: Données binaires du PDF
            prompt: Prompt d'extraction
            page_range: Plage de pages à extraire (start, end) inclusif
            max_pages: Nombre maximum de pages à traiter
            fallback_on_error: Continuer si une page échoue
            
        Returns:
            Liste de dictionnaires avec résultats par page
        """
        try:
            results = []
            
            # Créer un prompt spécifique pour l'extraction par page
            page_prompt = prompt + "\n\nINSTRUCTION IMPORTANTE: Cette extraction concerne une page spécifique du document. " \
                "Indique clairement dans ta réponse le numéro de page analysé."
            
            config = self._create_config()
            
            # Pour l'instant, on envoie le PDF complet avec instructions
            # Note: L'API Gemini 1.5 Flash peut analyser des pages spécifiques
            # mais nécessite une approche différente pour l'isolation des pages
            
            contents = [
                self._types.Content(
                    role="user",
                    parts=[
                        self._types.Part.from_text(text=page_prompt),
                        self._types.Part.from_bytes(data=pdf_data, mime_type="application/pdf")
                    ]
                )
            ]
            
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            # Pour la compatibilité, on retourne un résultat pour la "page 1"
            # Dans une implémentation avancée, on pourrait splitter le PDF
            page_result = {
                "page_number": 1,
                "response_text": response.text,
                "status": "success"
            }
            
            results.append(page_result)
            
            logger.info(f"✅ Extraction PDF pages: {len(results)} pages traitées")
            return results
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction PDF pages: {e}")
            
            if fallback_on_error:
                logger.warning(f"⚠️  Fallback: retourne un résultat vide pour continuer")
                return [{
                    "page_number": 1,
                    "response_text": "",
                    "status": "error",
                    "error": str(e)
                }]
            else:
                raise
    
    def extract_from_text(self, text: str, prompt: str) -> str:
        """Extrait des données depuis du texte pur."""
        try:
            config = self._create_config()
            
            # Créer le contenu avec texte seulement
            contents = [
                self._types.Content(
                    role="user",
                    parts=[
                        self._types.Part.from_text(text=prompt + "\n\nTEXTE À ANALYSER:\n" + text)
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
            logger.error(f"❌ Erreur extraction texte: {e}")
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
        """Ferme le client. Les credentials sont gérés par app.core.vertex."""
        pass

    def __del__(self):
        """Destructeur."""
        pass


if __name__ == "__main__":
    print("🧪 Test GeminiClient")
    print("Pour tester: python -m pytest tests/test_ocr_integration.py -v")
