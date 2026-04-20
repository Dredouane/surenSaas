"""
Service de reconstruction des threads historiques.

Gère la récupération d'historique d'emails lorsqu'un email arrive
au milieu d'une conversation existante (cas des redirections/forward).

Stratégie:
1. Essayer API Gmail threads (si accès disponible)
2. Extraction IA (Gemini) du corps de l'email si Gmail API échoue
3. Fallback: créer thread minimal avec métadonnées disponibles
4. Ne jamais planter - toujours retourner un résultat utilisable
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.core.config import settings
from app.api.auth import get_supabase
from app.agents.base.gemini_client import GeminiClient

logger = get_logger(__name__)

# Prompt pour l'extraction d'historique
EXTRACTION_SYSTEM_PROMPT = """Tu es un extracteur d'historique d'emails. Analyse ce forward/redirect et extrais les emails cités dans l'historique.

Règles:
- Retourne UNIQUEMENT un JSON valide
- Ne retourne aucun texte avant ou après le JSON
- Si pas d'historique détectable: retourne {"success": false, "emails": [], "confiance": 0, "note": "Aucun historique détecté"}
- Extrais date, expediteur, sujet, snippet (300 chars max) pour chaque email trouvé
- Si une info est manquante, utilise "inconnu"
- La date peut être approximative (format ISO si possible)
- Le snippet doit être le début du message original

Format de réponse attendu:
{
  "success": true,
  "confiance": 0.85,
  "emails": [
    {
      "date": "2025-04-10T14:30:00Z",
      "expediteur": "client@example.com",
      "sujet": "Re: Devis",
      "snippet": "Bonjour, voici le devis demandé..."
    }
  ],
  "note": "2 emails antérieurs détectés dans le forward"
}"""


class ThreadReconstructionService:
    """Service de reconstruction des threads historiques."""
    
    def __init__(self):
        self.client = get_supabase()
    
    async def reconstruct_thread(
        self,
        gmail_thread_id: str,
        org_id: UUID,
        company_id: Optional[UUID],
        current_email_id: str
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Reconstruit un thread historique au meilleur de nos capacités.
        
        Returns:
            (success, thread_data, reconstruction_status)
            reconstruction_status: 'complete', 'partial', 'minimal', 'failed'
        """
        logger.info(f"🔍 Reconstruction thread {gmail_thread_id} (email: {current_email_id})")
        
        # 1. Récupérer l'email courant pour analyser les headers
        email_data = await self._get_email_data(current_email_id)
        if not email_data:
            logger.error(f"❌ Email {current_email_id} non trouvé")
            return False, None, "failed"
        
        reconstruction_log = {
            "reconstruction_date": datetime.utcnow().isoformat(),
            "gmail_thread_id": gmail_thread_id,
            "current_email_id": current_email_id,
            "gmail_api_success": False,
            "gemini_extraction": None,
            "fallback_reason": None
        }
        
        # 2. Essayer reconstruction via Gmail API
        try:
            reconstruction_result = await self._reconstruct_from_gmail_api(
                gmail_thread_id=gmail_thread_id,
                org_id=org_id,
                company_id=company_id,
                current_email=email_data
            )
            
            if reconstruction_result["success"]:
                status = "complete" if reconstruction_result["email_count"] > 1 else "minimal"
                logger.info(f"✅ Reconstruction via Gmail API: {status} ({reconstruction_result['email_count']} emails)")
                return True, reconstruction_result["thread_data"], status
                
        except Exception as e:
            logger.warning(f"⚠️ Gmail API reconstruction failed: {e}")
            reconstruction_log["gmail_api_error"] = str(e)
        
        # 3. Tentative d'extraction avec Gemini (IA)
        gemini_result = None
        try:
            logger.info(f"🤖 Tentative extraction avec Gemini pour {current_email_id}")
            gemini_result = await self._extract_history_with_gemini(email_data)
            reconstruction_log["gemini_extraction"] = gemini_result
            
            if gemini_result.get("success"):
                logger.info(f"✅ Gemini a extrait {len(gemini_result.get('emails', []))} emails")
            else:
                logger.info(f"ℹ️ Gemini n'a pas trouvé d'historique extractible")
                
        except Exception as e:
            logger.warning(f"⚠️ Gemini extraction failed: {e}")
            reconstruction_log["gemini_error"] = str(e)
        
        # 4. Fallback: créer thread minimal avec métadonnées
        try:
            minimal_thread = await self._create_minimal_thread(
                gmail_thread_id=gmail_thread_id,
                org_id=org_id,
                company_id=company_id,
                current_email=email_data,
                reconstruction_log=reconstruction_log
            )
            logger.info(f"✅ Thread minimal créé avec logs de reconstruction")
            return True, minimal_thread, "minimal"
            
        except Exception as e:
            logger.error(f"❌ Échec création thread minimal: {e}")
            return False, None, "failed"
    
    async def _reconstruct_from_gmail_api(
        self,
        gmail_thread_id: str,
        org_id: UUID,
        company_id: Optional[UUID],
        current_email: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Essaie de récupérer tous les messages du thread via Gmail API.
        
        Returns:
            {success: bool, email_count: int, thread_data: dict}
        """
        logger.info(f"📧 Tentative récupération thread via Gmail API: {gmail_thread_id}")
        
        try:
            # Importer ici pour éviter dépendance circulaire
            from app.services.emails.gmail_client import create_gmail_client
            from app.services.email_database_service import email_db
            
            # Récupérer le compte email associé
            account_id = current_email.get("email_account_id")
            if not account_id:
                logger.warning("⚠️ Pas de account_id, impossible d'appeler Gmail API")
                return {"success": False, "email_count": 0, "thread_data": None}
            
            account = await email_db.get_email_account(str(account_id))
            if not account:
                logger.warning(f"⚠️ Compte {account_id} non trouvé")
                return {"success": False, "email_count": 0, "thread_data": None}
            
            # Créer client Gmail
            gmail_client = create_gmail_client(account["oauth_refresh_token"])
            await gmail_client.connect()
            
            # Récupérer le thread complet
            thread_data = gmail_client.service.users().threads().get(
                userId='me',
                id=gmail_thread_id
            ).execute()
            
            messages = thread_data.get("messages", [])
            logger.info(f"📨 Thread Gmail contient {len(messages)} messages")
            
            if len(messages) <= 1:
                # Un seul message = pas d'historique utile
                return {"success": True, "email_count": 1, "thread_data": None}
            
            # Récupérer les messages manquants
            imported_count = 0
            for msg in messages:
                msg_id = msg["id"]
                
                # Vérifier si déjà en DB
                existing = await email_db.get_email_by_message_id(msg_id)
                if existing:
                    continue
                
                # Récupérer et stocker le message
                try:
                    message_detail = await gmail_client.get_message(msg_id)
                    
                    # Traiter comme un nouvel email (via sync_service)
                    from app.services.emails.sync_service import sync_service
                    result = await sync_service._process_message(
                        gmail_client=gmail_client,
                        gmail_message={"id": msg_id, "threadId": gmail_thread_id},
                        account_id=str(account_id),
                        org_id=str(org_id)
                    )
                    
                    if result["stored"]:
                        imported_count += 1
                        logger.debug(f"✉️ Message importé: {msg_id}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erreur import message {msg_id}: {e}")
                    continue
            
            logger.info(f"📥 Importés: {imported_count}/{len(messages)} messages")
            
            # Mettre à jour les métriques du thread
            if imported_count > 0:
                from app.services.email_thread_service import thread_service
                thread = thread_service.get_or_create_thread(
                    org_id=org_id,
                    company_id=company_id,
                    gmail_thread_id=gmail_thread_id,
                    subject=current_email.get("subject")
                )
                thread_service.update_thread_metrics(UUID(thread["id"]))
                
                return {
                    "success": True,
                    "email_count": len(messages),
                    "thread_data": thread
                }
            
            return {"success": True, "email_count": 1, "thread_data": None}
            
        except Exception as e:
            logger.warning(f"⚠️ Gmail API error: {e}")
            return {"success": False, "email_count": 0, "thread_data": None}
    
    async def _create_minimal_thread(
        self,
        gmail_thread_id: str,
        org_id: UUID,
        company_id: Optional[UUID],
        current_email: Dict[str, Any],
        reconstruction_log: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crée un thread minimal avec l'email disponible.
        Utilisé comme fallback quand Gmail API échoue.
        """
        logger.info(f"🔧 Création thread minimal pour {gmail_thread_id}")
        
        from app.services.email_thread_service import thread_service
        
        # Créer le thread
        thread = thread_service.get_or_create_thread(
            org_id=org_id,
            company_id=company_id,
            gmail_thread_id=gmail_thread_id,
            subject=current_email.get("subject")
        )
        
        # Préparer les notes historiques
        if reconstruction_log:
            historical_notes = json.dumps(reconstruction_log, indent=2, ensure_ascii=False)
        else:
            historical_notes = json.dumps({
                "reconstruction_date": datetime.utcnow().isoformat(),
                "strategy_used": "minimal_fallback",
                "gmail_api_success": False,
                "note": "Aucune tentative de reconstruction (forward externe probable)"
            }, indent=2, ensure_ascii=False)
        
        # Marquer comme historique partiel
        self.client.table("email_threads").update({
            "is_historical_partial": True,
            "historical_notes": historical_notes,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", thread["id"]).execute()
        
        # Mettre à jour métriques (sera juste 1 email)
        thread_service.update_thread_metrics(UUID(thread["id"]))
        
        return thread
    
    async def _extract_history_with_gemini(
        self,
        email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extrait l'historique des emails du corps du forward avec Gemini.
        
        Args:
            email_data: Données de l'email (content_text, content_html, etc.)
            
        Returns:
            {
                "success": bool,
                "confiance": float,
                "emails": [{"date": "...", "expediteur": "...", "sujet": "...", "snippet": "..."}],
                "note": str
            }
        """
        try:
            # Récupérer le contenu texte de l'email
            email_body = email_data.get("content_text", "") or email_data.get("content_html", "")
            
            if not email_body or len(email_body) < 50:
                logger.info("ℹ️ Corps de l'email trop court pour extraction")
                return {
                    "success": False,
                    "confiance": 0,
                    "emails": [],
                    "note": "Corps de l'email vide ou trop court"
                }
            
            # Limiter la taille pour le prompt (économie de tokens)
            max_length = 8000
            if len(email_body) > max_length:
                email_body = email_body[:max_length] + "\n... [tronqué pour analyse]"
            
            # Initialiser Gemini
            gemini_client = GeminiClient(
                credentials_b64=settings.gemini_api_key,
                project_id=settings.gcp_project_id,
                location=settings.gemini_location or "europe-west1",
                model="gemini-2.5-flash-lite",
                temperature=0.1,  # Très déterministe
                max_output_tokens=2048
            )
            
            # Construire le prompt
            user_prompt = f"""Analyse ce forward d'email et extrais l'historique des messages cités.

Contenu à analyser:
---
{email_body}
---

Extrais tous les emails antérieurs mentionnés dans ce forward (dates, expéditeurs, sujets, extraits)."""

            # Appel Gemini
            from google.genai import types
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"{EXTRACTION_SYSTEM_PROMPT}\n\n{user_prompt}")
                    ]
                )
            ]
            
            config = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
            
            response = gemini_client._client.models.generate_content(
                model=gemini_client.model_name,
                contents=contents,
                config=config
            )
            
            # Parser la réponse JSON
            try:
                result = json.loads(response.text)
                logger.info(f"✅ Gemini extraction: {result.get('note', 'OK')}")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Gemini a retourné du JSON invalide: {e}")
                return {
                    "success": False,
                    "confiance": 0,
                    "emails": [],
                    "note": f"Réponse non-JSON: {str(e)[:100]}"
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur extraction Gemini: {e}")
            return {
                "success": False,
                "confiance": 0,
                "emails": [],
                "note": f"Erreur: {str(e)[:200]}"
            }
    
    async def _get_email_data(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les données d'un email."""
        try:
            response = self.client.table("emails").select("*").eq("id", email_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Erreur récupération email {email_id}: {e}")
            return None
    
    def should_attempt_reconstruction(
        self,
        gmail_thread_id: str,
        org_id: UUID
    ) -> Tuple[bool, str]:
        """
        Détermine si une reconstruction est nécessaire.
        
        Returns:
            (should_reconstruct, reason)
        """
        # Vérifier si le thread existe déjà
        existing = self.client.table("email_threads").select("id, email_count").eq(
            "gmail_thread_id", gmail_thread_id
        ).eq("org_id", str(org_id)).maybe_single().execute()
        
        if existing.data:
            if existing.data.get("email_count", 0) > 1:
                return False, "Thread existe avec historique"
            else:
                # Thread existe mais avec un seul email - potentiellement à enrichir
                return True, "Thread existe mais incomplet"
        
        return True, "Nouveau thread"


# Instance singleton
thread_reconstruction_service = ThreadReconstructionService()
