
import json
import base64
import os
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from app.core.config import settings

class ExtractedExpense(BaseModel):
    """Structure de données pour une dépense extraite d'une image."""
    fournisseur: Optional[str] = Field(None, description="Nom du fournisseur ou de l'enseigne")
    montant_ttc: Optional[float] = Field(None, description="Montant total TTC")
    tva: Optional[float] = Field(None, description="Montant de la TVA (si lisible)")
    date: Optional[str] = Field(None, description="Date de la facture (YYYY-MM-DD)")
    is_document: bool = Field(False, description="True s'il s'agit d'un document financier (ticket, facture)")
    besoin_clarification: bool = Field(False, description="True si le document est trop flou ou incomplet")
    description: str = Field("", description="Description courte du contenu de l'image")

class VisionExpertService:
    """Service expert pour l'analyse d'images (OCR + Classification Multimodale)."""
    
    def __init__(self):
        self._ensure_credentials()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gemini_location or "europe-west1"
        )

    @staticmethod
    def _ensure_credentials():
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")):
            return
        credentials_b64 = settings.gemini_api_key
        if credentials_b64 and not credentials_b64.startswith("AIza"):
            try:
                credentials_json = base64.b64decode(credentials_b64).decode('utf-8')
                credentials_info = json.loads(credentials_json)
                fd, cred_file = tempfile.mkstemp(suffix='.json')
                with os.fdopen(fd, 'w') as f:
                    json.dump(credentials_info, f)
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_file
            except Exception:
                pass

    async def process_photo(self, image_bytes: bytes, chantiers_context: List[Dict[str, Any]]) -> ExtractedExpense:
        """Analyse une photo pour extraire des données ou la classer comme photo de chantier."""
        
        # Encodage base64 pour Gemini
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        chantiers_str = "\n".join([f"- {c['nom']} (Réf: {c.get('ref', 'N/A')})" for c in chantiers_context])
        today = datetime.utcnow().date().isoformat()
        
        prompt = (
            "Tu es un expert en comptabilité BTP. Analyse cette photo.\n"
            f"DATE DU JOUR : {today}\n"
            "\nCONTEXTE DES CHANTIERS ACTIFS :\n"
            f"{chantiers_str}\n"
            "\nMISSION :\n"
            "1. Détermine s'il s'agit d'un DOCUMENT FINANCIER (ticket de caisse, facture, bon de livraison chiffré) "
            "ou d'une simple PHOTO DE CHANTIER (mur, bétonneuse, ouvriers, etc.).\n"
            "2. Si c'est un DOCUMENT : extrait le fournisseur, le montant TTC, la TVA et la date.\n"
            "3. Si c'est une PHOTO DE CHANTIER : décris brièvement ce que tu vois.\n"
            "4. NORMALISATION : La date doit être au format YYYY-MM-DD. Si tu lis 'hier', base-toi sur la date du jour.\n"
            "5. RÉPONSE : Réponds UNIQUEMENT au format JSON respectant le schéma suivant :\n"
            "{\n"
            "  \"fournisseur\": \"nom ou null\",\n"
            "  \"montant_ttc\": float ou null,\n"
            "  \"tva\": float ou null,\n"
            "  \"date\": \"YYYY-MM-DD ou null\",\n"
            "  \"is_document\": boolean,\n"
            "  \"besoin_clarification\": boolean,\n"
            "  \"description\": \"description courte\"\n"
            "}"
        )
        
        # Format multimodal LangChain
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                },
            ]
        )
        
        response = await self.llm.ainvoke([message])
        
        try:
            content = str(response.content).strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            return ExtractedExpense(**data)
        except Exception as e:
            print(f"Erreur parsing Vision: {e}")
            return ExtractedExpense(
                is_document=False, 
                besoin_clarification=True, 
                description="Erreur lors de l'analyse de l'image."
            )
