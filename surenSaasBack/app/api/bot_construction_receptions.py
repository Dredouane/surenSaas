import logging
from typing import Dict, Any
from app.api.telegram_core import send_simple_message, send_message_with_keyboard
from app.services.telegram.construction_menu import build_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected
from datetime import date

logger = logging.getLogger(__name__)

async def handle_list_receptions(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    """Liste les prochaines réunions."""
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        from app.api.bot_construction_commands import _handle_chantier_list
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    aujourd_hui = date.today().isoformat()
    try:
        r = supabase.table("chantier_receptions") \
            .select("date, type, statut") \
            .eq("org_id", org_id) \
            .eq("chantier_id", chantier["id"]) \
            .gte("date", aujourd_hui) \
            .order("date") \
            .execute()
        recs = r.data or []
    except Exception as e:
        logger.error(f"Erreur réceptions: {e}")
        recs = []

    texte = f"📅 *Prochaines réunions* — {chantier.get('nom', 'Chantier')}\n\n"
    for r_ in recs:
        texte += f"• {r_['date']} — {r_.get('type', 'Réunion')} ({r_.get('statut', '')})\n"
    
    await send_simple_message(telegram_id, bot_config, texte)
    return {"ok": True}

async def handle_add_point_reception(telegram_id: int, bot_config: Dict):
    """Demande un point à ajouter."""
    await send_simple_message(telegram_id, bot_config, "📝 *Noter un point à régler*\n\nDécris le point à aborder.")
    return {"ok": True}
