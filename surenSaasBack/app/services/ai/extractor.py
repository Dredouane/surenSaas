import os
import logging
import google.generativeai as genai
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Configurer Gemini
api_key = os.getenv("TEST_GOOGLE_GEMINI_CREDENTIALS_B64") or os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

async def extract_operation_data(text: str) -> Dict[str, Any]:
    """Agent IA avec Fallback manuel robuste."""
    if not api_key:
        return {"raw": text, "structured": f"Description: {text}\n(Saisie manuelle requise)"}
        
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analyse ce message: {text}. Extrais: description, categorie, montant."
        response = model.generate_content(prompt)
        return {"raw": text, "structured": response.text}
    except Exception as e:
        logger.error(f"Erreur Gemini: {e}")
        # FALLBACK : Retourne la description saisie pour ne pas bloquer l'utilisateur
        return {"raw": text, "structured": f"Description: {text}\n(IA indisponible, validation manuelle requise)"}
