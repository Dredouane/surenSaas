import logging
from typing import Dict, Any
from app.api.telegram_core import send_simple_message, send_message_with_keyboard, answer_callback
from app.services.telegram.construction_menu import build_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected, set_state, get_state
from app.services.ai.extractor import extract_operation_data
from app.services.telegram.base_workflow import BaseTelegramWorkflow
from app.api.auth import get_supabase
from app.services.telegram.notification_service import NotificationService
from app.services.telegram.audit_service import TelegramAuditService
from app.api.bot_construction_commands import _handle_chantier_list, send_menu_message
from app.api.telegram_core import escape_markdown

logger = logging.getLogger(__name__)

workflow = BaseTelegramWorkflow(get_supabase(), TelegramAuditService(get_supabase()), NotificationService(get_supabase()))

async def handle_create_operation(telegram_id: int, op_type: str, bot_config: Dict, supabase: Any, org_id: str):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    await set_state(telegram_id, "op_awaiting_description", org_id, supabase, data={"op_type": op_type})
    await send_simple_message(telegram_id, bot_config, f"📸 *Nouvelle opération ({op_type})*\n\nDécris l'opération (texte/photo) :")
    return {"ok": True}

async def handle_operation_media(message: Dict, bot_config: Dict, supabase: Any, org_id: str, state: Dict):
    """Gère la saisie textuelle pour une opération en attente."""
    telegram_id = message.get('chat', {}).get('id')
    text = message.get("text") or message.get("caption") or ""
    
    if not text:
        await send_simple_message(telegram_id, bot_config, "❌ Veuillez envoyer une description textuelle.")
        return {"ok": True}

    op_type = state.get('last_state_data', {}).get('op_type', 'autre')
    
    # Stocker la description extraite pour validation finale
    await set_state(telegram_id, "op_awaiting_validation", org_id, supabase, data={
        "op_type": op_type,
        "description": text
    })
    
    text_res = f"📝 *Confirmer cette opération ?*\n\nType: {escape_markdown(op_type)}\nDesc: {escape_markdown(text)}"
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Valider", "callback_data": f"op:final_save"}],
            [{"text": "❌ Annuler", "callback_data": "menu:main"}]
        ]
    }
    
    await send_message_with_keyboard(telegram_id, bot_config, text_res, keyboard)
    return {"ok": True}


async def handle_save_operation(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    """Insère l'opération dans la DB après validation."""
    state = await get_state(telegram_id, supabase, org_id)
    if not state: 
        logger.error("❌ Aucune donnée d'état trouvée pour la sauvegarde")
        return {"ok": False}
    
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    data = state.get('last_state_data', {})
    extracted = data.get('extracted', {})
    
    op_data = {
        "chantier_id": chantier["id"],
        "org_id": org_id,
        "description": data.get('description', 'Description manquante'),
        "statut": "en_attente",
        "type": data.get('op_type', 'autre')
    }

    logger.info(f"DEBUG: Tentative d'insertion opération: {op_data}")
    try:
        supabase.table("chantier_operations_htl").insert(op_data).execute()

        tu_res = supabase.table("telegram_users").select("user_id").eq("telegram_id", telegram_id).eq("org_id", org_id).execute()
        notif_user_id = tu_res.data[0]["user_id"] if tu_res.data else None
        notif_payload = {
            "chantier_id": chantier["id"],
            "org_id": org_id,
            "type": "validation",
            "statut": "envoyee",
            "titre": "Nouvelle opération",
            "message": f"Nouvelle opération en attente : {data.get('op_type', 'autre')}"
        }
        if notif_user_id:
            notif_payload["user_id"] = notif_user_id
        supabase.table("chantier_notifications").insert(notif_payload).execute()
        await send_simple_message(telegram_id, bot_config, "✅ Opération enregistrée.")
        await set_state(telegram_id, "idle", org_id, supabase)
        await send_menu_message(telegram_id, bot_config, supabase, org_id)
    except Exception as e:

        logger.error(f"❌ Erreur lors de l'insertion en DB: {e}")
        await send_simple_message(telegram_id, bot_config, "❌ Erreur base de données.")
        
    return {"ok": True}

