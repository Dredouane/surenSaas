import logging
from typing import Dict, Any
from app.api.telegram_core import send_simple_message, send_message_with_keyboard
from app.services.telegram.construction_menu import build_finances_submenu

logger = logging.getLogger(__name__)

async def handle_invoice_menu(telegram_id: int, bot_config: Dict):
    """Affiche le sous-menu factures avec options d'édition."""
    menu = build_finances_submenu()
    await send_message_with_keyboard(telegram_id, bot_config, menu["text"], menu["keyboard"])
    return {"ok": True}

async def handle_invoice_validation(chat_id: int, invoice_id: str, bot_config: Dict, supabase: Any, org_id: str):
    """Logique existante de validation."""
    from app.api.bot_construction import handle_invoice_validation as legacy_val
    return await legacy_val(chat_id, invoice_id, bot_config, supabase, org_id)

async def handle_invoice_cancellation(chat_id: int, invoice_id: str, bot_config: Dict, supabase: Any, org_id: str):
    """Logique existante d'annulation."""
    from app.api.bot_construction import handle_invoice_cancellation as legacy_can
    return await legacy_can(chat_id, invoice_id, bot_config, supabase, org_id)


async def handle_edit_invoice_step1(telegram_id: int, invoice_id: str, bot_config: Dict):
    """Étape 1 édition : demander nouveau fournisseur."""
    await send_simple_message(telegram_id, bot_config, "✏️ Quel est le nouveau nom du fournisseur ?")
    # TODO: set_state dans chantier_context pour invoice_edit_supplier:{invoice_id}
    return {"ok": True}

async def handle_edit_invoice_step2(telegram_id: int, invoice_id: str, bot_config: Dict):
    """Étape 2 édition : demander nouveau montant."""
    await send_simple_message(telegram_id, bot_config, "💰 Quel est le nouveau montant TTC ?")
    # TODO: set_state dans chantier_context pour invoice_edit_amount:{invoice_id}
    return {"ok": True}
