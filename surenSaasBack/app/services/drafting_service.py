"""
Service Drafting Sandbox - Génération et itération de réponses email.

Responsabilités:
- Générer des drafts de réponse avec Gemini
- Itérer sur les drafts via "Petit Prompt"
- Appliquer des Smart Chips (actions rapides)
- Pas de persistance DB (état temporaire)
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.core.config import settings
from app.api.auth import get_supabase
from app.agents.base.gemini_client import GeminiClient
from app.models.dossiers import (
    DraftGenerationRequest, DraftIterationRequest,
    DraftResponse, DraftIterationResponse, DraftSmartChipAction
)

logger = get_logger(__name__)


class DraftingService:
    """Service de génération de drafts de réponse."""
    
    def __init__(self):
        self.client = get_supabase()
        self._gemini_client: Optional[GeminiClient] = None
    
    def _get_gemini_client(self) -> GeminiClient:
        """Initialise et retourne le client Gemini (lazy loading)."""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model="gemini-2.5-flash-lite",
                temperature=0.4,  # Un peu créatif mais cohérent
                max_output_tokens=2048
            )
        return self._gemini_client
    
    async def generate_draft(
        self,
        thread_id: UUID,
        org_id: UUID,
        request: DraftGenerationRequest
    ) -> DraftResponse:
        """
        Génère un draft initial de réponse à un thread.
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            request: Paramètres de génération (context_level, tone)
            
        Returns:
            DraftResponse avec contenu HTML et suggestions
        """
        logger.info(f"✏️ Génération draft pour thread {thread_id}")
        
        # Récupérer le contexte du thread
        thread_context = await self._build_thread_context(thread_id, org_id, request.context_level)
        
        # Construire le prompt
        system_prompt = self._load_prompt_template("drafting_generation")
        user_prompt = self._build_generation_prompt(thread_context, request.tone)
        
        # Appel Gemini
        gemini = self._get_gemini_client()
        
        from google.genai import types
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )
        ]
        
        config = types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=2048,
            response_mime_type="application/json"
        )
        
        try:
            response = gemini._client.models.generate_content(
                model=gemini.model_name,
                contents=contents,
                config=config
            )
            
            # Parser la réponse
            result = json.loads(response.text)
            
            draft_content = result.get("content", "")
            plain_text = result.get("plain_text", self._html_to_text(draft_content))
            suggestions = result.get("suggestions", ["shorten", "formal", "add_signature"])
            
            draft_id = f"draft-{uuid4().hex[:8]}"
            
            logger.info(f"✅ Draft généré: {draft_id}")
            
            return DraftResponse(
                draft_id=draft_id,
                content=draft_content,
                plain_text=plain_text,
                suggestions=suggestions,
                generated_at=datetime.utcnow(),
                model_used="gemini-2.5-flash-lite"
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur génération draft: {e}")
            # Fallback: message générique
            return DraftResponse(
                draft_id=f"draft-{uuid4().hex[:8]}",
                content="<p>Bonjour,</p><p>Merci pour votre message. Je reviens vers vous rapidement.</p><p>Cordialement,</p>",
                plain_text="Bonjour,\n\nMerci pour votre message. Je reviens vers vous rapidement.\n\nCordialement,",
                suggestions=["formal", "add_signature"],
                generated_at=datetime.utcnow(),
                model_used="fallback"
            )
    
    async def iterate_draft(
        self,
        request: DraftIterationRequest
    ) -> DraftIterationResponse:
        """
        Itère sur un draft existant (Petit Prompt).
        
        Args:
            request: Contenu actuel + instruction
            
        Returns:
            Draft mis à jour avec résumé des changements
        """
        logger.info(f"🔄 Itération draft: {request.instruction[:50]}...")
        
        # Construire le prompt d'itération
        system_prompt = self._load_prompt_template("drafting_iteration")
        
        user_prompt = f"""Draft actuel:
{request.current_content}

Instruction de modification:
{request.instruction}

Modifie le draft selon l'instruction en préservant le sens et les faits."""
        
        # Appel Gemini
        gemini = self._get_gemini_client()
        
        from google.genai import types
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}")]
            )
        ]
        
        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=2048,
            response_mime_type="application/json"
        )
        
        try:
            response = gemini._client.models.generate_content(
                model=gemini.model_name,
                contents=contents,
                config=config
            )
            
            result = json.loads(response.text)
            
            new_content = result.get("content", request.current_content)
            changes_summary = result.get("changes_summary", "Modifications appliquées")
            
            draft_id = f"draft-{uuid4().hex[:8]}"
            
            return DraftIterationResponse(
                draft_id=draft_id,
                content=new_content,
                plain_text=self._html_to_text(new_content),
                suggestions=result.get("suggestions", []),
                generated_at=datetime.utcnow(),
                model_used="gemini-2.5-flash-lite",
                changes_summary=changes_summary
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur itération draft: {e}")
            return DraftIterationResponse(
                draft_id=f"draft-{uuid4().hex[:8]}",
                content=request.current_content,
                plain_text=self._html_to_text(request.current_content),
                suggestions=[],
                generated_at=datetime.utcnow(),
                model_used="fallback",
                changes_summary="Impossible d'appliquer les modifications"
            )
    
    async def apply_smart_chip(
        self,
        action: DraftSmartChipAction
    ) -> DraftIterationResponse:
        """
        Applique une action Smart Chip prédéfinie.
        
        Args:
            action: Chip ID + contenu actuel
            
        Returns:
            Draft modifié
        """
        chip_instructions = {
            "shorten": "Raccourcir le texte de 30%, aller à l'essentiel, phrases plus courtes",
            "formal": "Rendre le ton plus formel et professionnel, ajouter des formules de politesse",
            "friendly": "Rendre le ton plus chaleureux et accessible, tout en restant professionnel",
            "technical": "Ajouter des détails techniques et utiliser le vocabulaire BTP approprié",
            "add_signature": "Ajouter une signature professionnelle à la fin du message"
        }
        
        instruction = chip_instructions.get(
            action.chip_id,
            "Améliorer le texte"
        )
        
        return await self.iterate_draft(DraftIterationRequest(
            current_content=action.current_content,
            instruction=instruction,
            action="apply_chip"
        ))
    
    async def _build_thread_context(
        self,
        thread_id: UUID,
        org_id: UUID,
        context_level: str
    ) -> Dict[str, Any]:
        """
        Construit le contexte d'un thread pour la génération.
        
        Args:
            thread_id: ID du thread
            org_id: ID de l'organisation
            context_level: full | summary | minimal
            
        Returns:
            Contexte structuré
        """
        # Récupérer le thread
        thread_response = self.client.table("email_threads")\
            .select("*")\
            .eq("id", str(thread_id))\
            .eq("org_id", str(org_id))\
            .single()\
            .execute()
        
        if not thread_response.data:
            return {"error": "Thread not found"}
        
        thread = thread_response.data
        
        context = {
            "thread_id": str(thread_id),
            "subject": thread.get("subject", ""),
            "ai_summary": thread.get("ai_summary", ""),
            "participants": {
                "emails": thread.get("participant_emails", []),
                "names": thread.get("participant_names", [])
            }
        }
        
        if context_level == "minimal":
            return context
        
        # Ajouter les emails du thread
        emails_response = self.client.table("emails")\
            .select("*")\
            .eq("gmail_thread_id", thread["gmail_thread_id"])\
            .eq("org_id", str(org_id))\
            .order("sent_at", desc=False)\
            .execute()
        
        if context_level == "summary":
            # Juste les sujets et expéditeurs
            context["emails"] = [
                {
                    "sender": e.get("sender_email"),
                    "sender_name": e.get("sender_name"),
                    "subject": e.get("subject"),
                    "sent_at": e.get("sent_at")
                }
                for e in emails_response.data
            ]
        else:  # full
            # Contenu complet des emails
            context["emails"] = [
                {
                    "sender": e.get("sender_email"),
                    "sender_name": e.get("sender_name"),
                    "subject": e.get("subject"),
                    "content": e.get("content_text", "")[:1000],  # Limité
                    "sent_at": e.get("sent_at"),
                    "has_attachments": e.get("has_attachments", False)
                }
                for e in emails_response.data
            ]
            
            # Ajouter les PJ si présentes
            if emails_response.data:
                email_ids = [e["id"] for e in emails_response.data]
                attachments_response = self.client.table("email_attachments")\
                    .select("filename, ocr_text")\
                    .in_("email_id", email_ids)\
                    .execute()
                
                if attachments_response.data:
                    context["attachments"] = [
                        {
                            "filename": a["filename"],
                            "ocr_preview": a.get("ocr_text", "")[:500] if a.get("ocr_text") else None
                        }
                        for a in attachments_response.data[:5]  # Max 5
                    ]
        
        return context
    
    def _build_generation_prompt(
        self,
        context: Dict[str, Any],
        tone: str
    ) -> str:
        """Construit le prompt de génération."""
        tone_instructions = {
            "professional": "Ton professionnel et courtois",
            "formal": "Ton très formel, respectueux, langage soutenu",
            "friendly": "Ton chaleureux et accessible, proche mais professionnel",
            "technical": "Ton technique avec jargon BTP approprié"
        }
        
        return f"""Contexte du thread:
Sujet: {context.get('subject', 'N/A')}
Résumé IA: {context.get('ai_summary', 'N/A')}
Participants: {', '.join(context.get('participants', {}).get('names', []))}

{tone_instructions.get(tone, 'Ton professionnel')}

Génère une réponse au dernier email du thread."""
    
    def _load_prompt_template(self, template_name: str) -> str:
        """Charge un template de prompt."""
        # Templates inline pour simplifier
        templates = {
            "drafting_generation": """Tu es un assistant de rédaction commerciale pour le BTP.
Règles:
- Style professionnel mais accessible
- Répondre précisément aux questions posées dans l'historique
- Proposer des suites si pertinent
- Format HTML simple (p, br, strong, ul/li)
- Longueur: 100-300 mots

Retourne un JSON:
{
  "content": "<html>...</html>",
  "plain_text": "Texte brut...",
  "suggestions": ["shorten", "formal", "add_signature"]
}""",
            
            "drafting_iteration": """Tu es un éditeur de texte professionnel.
Règles:
- Modifier le draft selon l'instruction
- Préserver les faits et informations clés
- Ne pas inventer de nouvelles informations
- Maintenir le ton professionnel

Retourne un JSON:
{
  "content": "<html>...</html>",
  "changes_summary": "Description des modifications"
}"""
        }
        
        return templates.get(template_name, "")
    
    def _html_to_text(self, html: str) -> str:
        """Convertit HTML simple en texte brut."""
        import re
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'</p>', '\n\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()


# Instance singleton
drafting_service = DraftingService()
