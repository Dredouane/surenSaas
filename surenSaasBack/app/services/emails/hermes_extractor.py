"""
Hermès Extractor — Extraction structurée + Dispatch automatique.

Pipeline:
  1. LangChain with_structured_output → HermesExtractionResult (Pydantic)
  2. Dispatch vers les services existants :
       - tasks    → _manage_taches_internal()
       - expenses → _create_depense_internal()
       - notifications → NotificationService.notify_admins()
  3. Audit dans hermes_dispatch_log
"""

import asyncio
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import json

from app.core.logging import get_logger
from app.api.auth import get_supabase

logger = get_logger(__name__)


class ExtractedTask(BaseModel):
    titre: str = Field(description="Titre concis de la tâche (max 80 chars)")
    description: str = Field(default="", description="Description détaillée")
    priorite: str = Field(default="moyenne", description="Priorité : 'basse', 'moyenne' ou 'haute'")
    echeance: Optional[str] = Field(default=None, description="Date d'échéance ISO 8601 (YYYY-MM-DD)")

    @validator('priorite')
    def validate_priorite(cls, v):
        if v not in ['basse', 'moyenne', 'haute']:
            return 'moyenne'
        return v

    @validator('echeance')
    def validate_echeance(cls, v):
        if v:
            try:
                date.fromisoformat(v)
                return v
            except ValueError:
                return None
        return None


class ExtractedExpense(BaseModel):
    fournisseur: str = Field(description="Nom du fournisseur ou prestataire")
    montant: float = Field(default=0.0, description="Montant TTC en euros")
    categorie: str = Field(default="autre", description="Catégorie parmi : fournisseur, sous_traitant, achat_direct, location, carburant, divers, autre")
    description: str = Field(default="", description="Description de la dépense")
    facture_ref: Optional[str] = Field(default=None, description="Référence de facture si mentionnée")

    @validator('categorie')
    def validate_categorie(cls, v):
        allowed = ['fournisseur', 'sous_traitant', 'achat_direct', 'location', 'carburant', 'divers', 'autre']
        if v not in allowed:
            return 'autre'
        return v

    @validator('montant')
    def validate_montant(cls, v):
        return max(0.0, v)


class ExtractedNotification(BaseModel):
    message: str = Field(description="Message de l'alerte (1-2 phrases)")
    urgence: str = Field(default="info", description="Niveau : 'info', 'warning' ou 'critical'")
    titre: str = Field(default="Alerte Hermès", description="Titre court de la notification")

    @validator('urgence')
    def validate_urgence(cls, v):
        if v not in ['info', 'warning', 'critical']:
            return 'info'
        return v


class HermesExtractionResult(BaseModel):
    tasks: List[ExtractedTask] = Field(default_factory=list)
    expenses: List[ExtractedExpense] = Field(default_factory=list)
    notifications: List[ExtractedNotification] = Field(default_factory=list)
    should_ignore: bool = Field(default=False)
    summary: str = Field(default="")


EXTRACTION_PROMPT = """Tu es l'agent Hermès, assistant IA d'une entreprise du BTP.

Tu analyses les emails reçus pour un chantier spécifique et tu en extrais les informations structurées.

EMAIL À ANALYSER :
- De : {sender}
- Date : {sent_at}
- Sujet : {subject}
- Corps :
{body}

CHANTIER CONCERNÉ : {chantier_nom} (ref: {chantier_ref})

INSTRUCTIONS D'EXTRACTION :
1. **tasks** : Crée une tâche si l'email mentionne une action concrète à réaliser (livraison à planifier, réunion à organiser, document à envoyer, travaux à effectuer, etc.). N'invente pas de tâches. Le titre doit être court (max 80 chars).
2. **expenses** : Détecte les montants financiers (devis, factures, bons de commande). Un montant vague ne suffit pas — il faut un chiffre précis.
3. **notifications** : Envoie une alerte uniquement pour des événements critiques : refus d'un avenant, litige, blocage de chantier, délai non respecté, urgence client explicite.
4. **should_ignore** : True pour accusé de réception automatique, newsletter, spam, out-of-office, ou email sans contenu exploitable.
5. **summary** : Résume l'information principale de l'email en une phrase.

Réponds UNIQUEMENT avec le JSON structuré correspondant aux schémas Pydantic fournis. Ne rajoute aucun texte avant ou après le JSON.
"""


class HermesExtractor:
    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from app.core import vertex as vertex_service
            base_llm = vertex_service.get_chat_model()
            self._llm = base_llm.with_structured_output(HermesExtractionResult)
        return self._llm

    async def extract_and_dispatch(self, email_id: str, chantier_id: str, org_id: str) -> dict:
        try:
            sb = get_supabase()
        except ImportError:
            return {"success": False, "error": "supabase_not_available"}

        email_resp = sb.table("emails")\
            .select("subject, sender_email, sender_name, content_text, sent_at")\
            .eq("id", email_id)\
            .maybe_single()\
            .execute()

        if not email_resp or not email_resp.data:
            logger.error(f"[HermesExtractor] Email {email_id} introuvable")
            return {"success": False, "error": "email_not_found"}

        email = email_resp.data

        chantier_resp = sb.table("chantiers")\
            .select("nom, ref")\
            .eq("id", chantier_id)\
            .maybe_single()\
            .execute()

        chantier = chantier_resp.data if chantier_resp and chantier_resp.data else {}
        chantier_nom = chantier.get("nom", "Inconnu")
        chantier_ref = chantier.get("ref", "")

        extraction = await self._run_extraction(email, chantier_nom, chantier_ref)

        if not extraction:
            await self._log_dispatch(sb, email_id, org_id, chantier_id, "extraction_failed", None, {}, False, "LLM extraction failed")
            return {"success": False, "error": "extraction_failed"}

        if extraction.should_ignore:
            logger.info(f"[HermesExtractor] Email {email_id} ignoré par LLM")
            await self._log_dispatch(sb, email_id, org_id, chantier_id, "ignored", None, {"reason": "should_ignore"}, True)
            return {"success": True, "action": "ignored", "summary": extraction.summary}

        dispatch_results = await self._dispatch(extraction, email_id, chantier_id, org_id, sb)

        return {
            "success": True,
            "summary": extraction.summary,
            "tasks_created": dispatch_results["tasks"],
            "expenses_created": dispatch_results["expenses"],
            "notifications_sent": dispatch_results["notifications"],
        }

    async def _run_extraction(self, email: dict, chantier_nom: str, chantier_ref: str) -> Optional[HermesExtractionResult]:
        try:
            prompt = EXTRACTION_PROMPT.format(
                subject=email.get("subject", ""),
                sender=f"{email.get('sender_name', '')} <{email.get('sender_email', '')}>",
                sent_at=email.get("sent_at", ""),
                body=(email.get("content_text") or "")[:3000],
                chantier_nom=chantier_nom,
                chantier_ref=chantier_ref,
            )

            from langchain_core.messages import HumanMessage
            llm = self._get_llm()

            loop = asyncio.get_event_loop()
            result: HermesExtractionResult = await loop.run_in_executor(
                None,
                lambda: llm.invoke([HumanMessage(content=prompt)])
            )
            return result

        except Exception as e:
            logger.error(f"[HermesExtractor] Erreur LLM extraction: {e}", exc_info=True)
            return None

    async def _dispatch(self, extraction: HermesExtractionResult, email_id: str, chantier_id: str, org_id: str, sb) -> dict:
        _create_depense_internal = None
        _manage_taches_internal = None
        NotificationService = None
        try:
            from app.agents.tools.depense_tools import _create_depense_internal
            from app.api.tools_rest import _manage_taches_internal
            from app.services.telegram.notification_service import NotificationService
        except ImportError as e:
            logger.error(f"Erreur d'importation pour le dispatch : {e}")
            return {"tasks": [], "expenses": [], "notifications": []}

        results = {"tasks": [], "expenses": [], "notifications": []}
        loop = asyncio.get_event_loop()

        for task in extraction.tasks:
            try:
                echeance = task.echeance
                if echeance:
                    try:
                        parsed_date = date.fromisoformat(echeance)
                        if parsed_date < date.today():
                            echeance = None
                    except ValueError:
                        echeance = None

                result = await loop.run_in_executor(
                    None,
                    lambda t=task, e=echeance: _manage_taches_internal(
                        org_id=org_id, chantier_id=chantier_id, action="create",
                        titre=t.titre[:80], description=t.description,
                        priorite=t.priorite, date_echeance=e,
                    )
                )

                if result.get("success"):
                    task_id = result.get("data", {}).get("id")
                    results["tasks"].append(task_id)
                    await self._log_dispatch(sb, email_id, org_id, chantier_id, "task_created", task_id, task.model_dump(), True)
                else:
                    await self._log_dispatch(sb, email_id, org_id, chantier_id, "task_created", None, task.model_dump(), False, result.get('error'))

            except Exception as e:
                logger.error(f"[HermesExtractor] Erreur dispatch tâche: {e}", exc_info=True)

        for expense in extraction.expenses:
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda ex=expense: _create_depense_internal(
                        org_id=org_id, chantier_id=chantier_id,
                        description=ex.description or f"Dépense {ex.fournisseur}",
                        montant=ex.montant, fournisseur=ex.fournisseur,
                        categorie=ex.categorie, date_depense=date.today().isoformat(),
                    )
                )

                if result.get("success"):
                    dep_id = result.get("data", {}).get("id")
                    results["expenses"].append(dep_id)
                    await self._log_dispatch(sb, email_id, org_id, chantier_id, "expense_created", dep_id, expense.model_dump(), True)
                else:
                    await self._log_dispatch(sb, email_id, org_id, chantier_id, "expense_created", None, expense.model_dump(), False, result.get('error'))

            except Exception as e:
                logger.error(f"[HermesExtractor] Erreur dispatch dépense: {e}", exc_info=True)

        if extraction.notifications and NotificationService is not None:
            try:
                notif_service = NotificationService(
                    supabase_client=sb, telegram_token=_get_telegram_token()
                )
                for notif in extraction.notifications:
                    result = await notif_service.notify_admins(
                        org_id=org_id, title=notif.titre,
                        message=notif.message, notification_type=f"hermes_{notif.urgence}",
                    )
                    results["notifications"].append(result)
                    await self._log_dispatch(sb, email_id, org_id, chantier_id, "notification_sent", None, notif.model_dump(), True)
            except Exception as e:
                logger.error(f"[HermesExtractor] Erreur dispatch notification: {e}", exc_info=True)

        return results

    async def _log_dispatch(self, sb, email_id: str, org_id: str, chantier_id: Optional[str],
                            action_type: str, action_id: Optional[str], payload: dict,
                            success: bool, error_message: Optional[str] = None):
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: sb.table("hermes_dispatch_log").insert({
                    "org_id": org_id, "email_id": email_id, "chantier_id": chantier_id,
                    "action_type": action_type, "action_id": action_id,
                    "payload": json.dumps(payload), "success": success,
                    "error_message": error_message,
                }).execute()
            )
        except Exception as e:
            logger.warning(f"[HermesExtractor] Échec log dispatch: {e}")


def _get_telegram_token() -> Optional[str]:
    try:
        from app.core.config import settings
        return settings.telegram_construction_bot_token or None
    except Exception:
        return None


hermes_extractor = HermesExtractor()
