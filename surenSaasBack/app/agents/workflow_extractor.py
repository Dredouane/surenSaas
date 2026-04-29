"""
WorkflowExtractor — Extraction structurée depuis des messages Telegram.

Utilise GeminiClient existant (nouvelle lib google-genai) pour extraire
des données depuis du texte saisi par l'utilisateur, avec support multi-modal
(texte + photo). Les prompts sont chargés depuis agents/prompts/telegram/.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from app.agents.base.gemini_client import GeminiClient
from app.core.config import settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts" / "telegram"


class WorkflowExtractor:
    """
    Extracteur pour les workflows Telegram (avancement, opération, dépense, tâche, pointage).

    Utilise GeminiClient (nouvelle lib) avec un système prompt chargé depuis un fichier txt
    et une instruction spécifique injectée selon le workflow.

    Supporte le mode multi-modal : si un file_path est fourni, envoie texte + image/PDF
    en un seul appel Gemini.
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None, model: Optional[str] = None):
        self._client = gemini_client or self._create_client(model)
        self._system_prompt = self._load_system_prompt()
        self._instructions = self._load_instructions()

    def _create_client(self, model: Optional[str] = None) -> GeminiClient:
        credentials = (
            settings.gemini_api_key
            or os.getenv("SUREN_GOOGLE_GEMINI_CREDENTIALS_B64")
            or os.getenv("GOOGLE_GEMINI_CREDENTIALS_B64")
        )
        return GeminiClient(
            credentials_b64=credentials or os.getenv("GEMINI_API_KEY"),
            model=model or settings.gemini_model or "gemini-1.5-flash-001",
            temperature=0.1,
        )

    def _load_system_prompt(self) -> str:
        path = PROMPTS_DIR / "system_extraction.txt"
        if not path.exists():
            logger.warning(f"Prompt fichier non trouvé: {path}, utilise défaut")
            return "Tu es un assistant d'extraction de données de chantier."
        return path.read_text(encoding="utf-8")

    def _load_instructions(self) -> Dict[str, Any]:
        path = PROMPTS_DIR / "user_instructions.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _get_instruction(self, workflow_type: str) -> str:
        wf = self._instructions.get(workflow_type, {})
        schema = wf.get("schema", {})
        schema_str = "\n".join(f"  - {k}: {v}" for k, v in schema.items())
        instruction = wf.get("instruction", "Extrais les informations pertinentes.")

        prompt = (
            f"Type de workflow: {workflow_type}\n"
            f"Description: {wf.get('description', '')}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Schéma des données à extraire:\n{schema_str}"
        )
        return prompt

    def extract(self, text: str, workflow_type: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extrait des données depuis un message Telegram.

        Args:
            text: Texte saisi par l'utilisateur
            workflow_type: Type de workflow (avancement, operation, depense, tache, pointage)
            file_path: Chemin optionnel vers un fichier (photo/PDF) joint

        Returns:
            Dictionnaire avec les données extraites + métadonnées
            Inclut la clé _fallback=True si l'extraction a échoué
        """
        instruction = self._get_instruction(workflow_type)
        system = self._system_prompt.replace("{workflow_instruction}", instruction)

        prompt = (
            f"{system}\n\n"
            f"MESSAGE À ANALYSER:\n{text}"
        )

        try:
            if file_path and Path(file_path).exists():
                response_text = self._client.extract_from_file(file_path, prompt)
            else:
                response_text = self._client.extract_from_text(text, prompt)

            raw = response_text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            parsed = json.loads(raw)
            parsed["_raw"] = text
            parsed["_workflow"] = workflow_type
            return parsed

        except Exception as e:
            logger.error(f"❌ WorkflowExtractor erreur ({workflow_type}): {e}")
            return {
                "_raw": text,
                "_workflow": workflow_type,
                "_fallback": True,
                "_error": str(e),
                "description": text,
            }

    def extract_multi(self, text: str, workflow_type: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extraction complète avec construction du message de validation.

        Retourne les données structurées prêtes à être affichées à l'utilisateur.
        """
        extracted = self.extract(text, workflow_type, file_path)
        if extracted.get("_fallback"):
            return extracted

        data = extracted.get("extracted_data", extracted)
        return {
            "description": extracted.get("description", text),
            "workflow_type": workflow_type,
            "data": data,
            "metadata": extracted.get("metadata", {}),
            "_raw": extracted,
        }
