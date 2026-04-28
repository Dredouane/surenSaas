import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

api_key = os.getenv("TEST_GOOGLE_GEMINI_CREDENTIALS_B64") or os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)


def _get_model():
    return genai.GenerativeModel('gemini-1.5-flash')


SYSTEM_PROMPT_BASE = (
    "Tu es un assistant spécialisé dans l'extraction de données de chantier de construction. "
    "L'utilisateur envoie un message textuel décrivant une situation de travail. "
    "Tu dois extraire les informations structurées et les retourner UNIQUEMENT au format JSON. "
    "Ne réponds rien d'autre que le JSON. "
    "Utilise des clés en français (snake_case). "
    "Ne fabrique jamais de données, mets null si absent."
)


async def extract_with_llm(text: str, workflow_type: str, extra_prompt: str = "") -> Dict[str, Any]:
    """Extraction LLM générique avec prompt métier dédié et fallback."""
    if not api_key:
        return {"_raw": text, "_workflow": workflow_type, "_fallback": True, "_error": "Pas de clé API"}

    prompt = f"{SYSTEM_PROMPT_BASE}\n\nContexte: {extra_prompt}\n\nMessage: {text}\n\nJSON:"
    try:
        model = _get_model()
        response = model.generate_content(prompt)
        raw = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        parsed = json.loads(raw)
        parsed["_raw"] = text
        parsed["_workflow"] = workflow_type
        return parsed
    except Exception as e:
        logger.error(f"Erreur LLM extraction ({workflow_type}): {e}")
        return {"_raw": text, "_workflow": workflow_type, "_fallback": True, "_error": str(e)}


AVANCEMENT_PROMPT = (
    "Extrais les informations d'avancement de chantier depuis le message. "
    "Retourne un JSON avec ces clés : description (str), quantite (number ou null), "
    "unite (str ou null, ex: m2, m3, ml, u), prix_unitaire (number ou null), "
    "avancement_pourcentage (number entre 0 et 100 ou null). "
    "Si le message mentionne une somme d'argent, mets-la dans prix_unitaire. "
    "Pourcentage : cherche le nombre suivi de '%'."
)


async def extract_avancement(text: str) -> Dict[str, Any]:
    return await extract_with_llm(text, "avancement", AVANCEMENT_PROMPT)


AVANCEMENT_REFINE_PROMPT = (
    "Voici un avancement saisi par l'utilisateur et la première extraction LLM. "
    "Retourne un JSON à présenter en français à l'utilisateur pour validation. "
    "Clés : description (str), quantite (str ou null, ex: '50 m2'), "
    "prix_unitaire (str ou null, ex: '25 €/m2'), avancement_pourcentage (str ou null, ex: '80%'), "
    "montant_total (str, ex: '1250.00€'), avancement_montant (str, ex: '1000.00€'). "
    "Calcule montant_total = quantite * prix_unitaire, et avancement_montant = montant_total * avancement_pourcentage / 100."
)


async def extract_and_refine_avancement(text: str) -> Dict[str, Any]:
    raw = await extract_avancement(text)
    if raw.get("_fallback"):
        return raw
    refine_prompt = f"{AVANCEMENT_REFINE_PROMPT}\n\nMessage original: {text}\nExtraction brute: {json.dumps(raw, indent=2, ensure_ascii=False)}\n\nJSON:"
    try:
        model = _get_model()
        response = model.generate_content(refine_prompt)
        refined = json.loads(response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())
        refined["_raw"] = raw
        return refined
    except Exception as e:
        logger.error(f"Erreur refine avancement: {e}")
        return raw


async def extract_operation(text: str) -> Dict[str, Any]:
    prompt = (
        "Extrais les informations d'une opération de chantier depuis le message. "
        "Retourne un JSON avec : description (str), type (str parmi: demolition, nettoyage, pose_bso, commande, achat_materiel, sous_traitance, autre), "
        "montant (number ou null), quantite (number ou null), unite (str ou null)."
    )
    return await extract_with_llm(text, "operation", prompt)


async def extract_depense(text: str) -> Dict[str, Any]:
    prompt = (
        "Extrais les informations d'une dépense de chantier depuis le message. "
        "Retourne un JSON avec : fournisseur (str ou null), montant (number ou null), "
        "description (str), categorie (str parmi: sous_traitant, fournisseur, autre). "
        "Si un montant en euros est mentionné, mets-le dans montant. "
        "Si un nom d'entreprise/fournisseur est mentionné, mets-le dans fournisseur."
    )
    return await extract_with_llm(text, "depense", prompt)
