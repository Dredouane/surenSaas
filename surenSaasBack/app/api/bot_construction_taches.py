import logging
from typing import Dict, Any
from app.api.telegram_core import send_simple_message, send_message_with_keyboard
from app.services.telegram.construction_menu import build_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected

logger = logging.getLogger(__name__)

from app.services.telegram.base_workflow import BaseTelegramWorkflow
from app.api.auth import get_supabase
from app.services.telegram.notification_service import NotificationService
from app.services.telegram.audit_service import TelegramAuditService

workflow = BaseTelegramWorkflow(get_supabase(), TelegramAuditService(get_supabase()), NotificationService(get_supabase()))

async def handle_list_taches(telegram_id: int, statut: str, bot_config: Dict, supabase: Any, org_id: str):
    """Liste les tâches par statut."""
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        from app.api.bot_construction_commands import _handle_chantier_list
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    # Récupérer les tâches
    taches = supabase.table("chantier_taches").select("id, titre, echeance").eq("org_id", org_id).eq("chantier_id", chantier["id"]).eq("statut", statut).execute().data
    
    if not taches:
        menu = build_simple_message(f"✅ Aucune tâche {statut}.")
    else:
        texte = f"📋 *Tâches {statut}* — {chantier['nom']}\n\n"
        for t in taches:
            texte += f"• *{t['titre']}* (ID: `{t['id'][:4]}`)\n"
        menu = build_simple_message(texte, bouton_retour=True)

    await send_message_with_keyboard(telegram_id, bot_config, menu["text"], menu["keyboard"])
    return {"ok": True}

async def handle_ask_done(telegram_id: int, bot_config: Dict):
    await send_simple_message(telegram_id, bot_config, "📝 Envoie l'ID de la tâche à marquer faite.")
    return {"ok": True}

async def handle_validate_tache(telegram_id: int, tache_id: str, bot_config: Dict, supabase: Any, org_id: str):
    supabase.table("chantier_taches").update({"statut": "terminee"}).eq("id", tache_id).execute()
    await send_simple_message(telegram_id, bot_config, "✅ Tâche terminée.")
    return {"ok": True}
