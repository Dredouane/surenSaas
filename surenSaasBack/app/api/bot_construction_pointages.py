import logging
from typing import Dict, Any, Optional
from app.api.telegram_core import send_message_with_keyboard, answer_callback, get_bot_token, send_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected, set_state, get_state
from datetime import date, timedelta

logger = logging.getLogger(__name__)


async def handle_pointage_date_select(telegram_id: int, selected_date: str, bot_config: Dict, supabase: Any, org_id: str):
    """Stocke la date choisie et affiche le sous-menu pointages."""
    from app.services.telegram.construction_menu import build_pointages_submenu

    ok = await set_state(telegram_id, "pointage_date_selected", org_id, supabase, data={"pointage_date": selected_date})
    if not ok:
        logger.error("set_state a échoué pour le choix de date")
    date_display = _format_date_display(selected_date)
    menu = build_pointages_submenu(date_display)
    await send_message_with_keyboard(telegram_id, bot_config, menu["text"], menu["keyboard"])
    return {"ok": True}


def _format_date_display(date_str: str) -> str:
    """Formate une date ISO pour l'affichage."""
    d = date.fromisoformat(date_str)
    return d.strftime("%d/%m/%Y")


async def _get_pointage_for_date(supabase, chantier_id, org_id, pointage_date):
    """Récupère ou crée le pointage pour une date donnée."""
    res = supabase.table("chantier_pointages").select("id").eq("chantier_id", chantier_id).eq("date", pointage_date).execute()
    if res.data:
        return res.data[0]['id']

    new_pt = supabase.table("chantier_pointages").insert({
        "chantier_id": chantier_id,
        "org_id": org_id,
        "date": pointage_date,
        "commentaires": "Auto-généré"
    }).execute()
    return new_pt.data[0]['id']


async def _get_pointage_date(telegram_id: int, supabase: Any, org_id: str) -> str:
    """Récupère la date depuis le state, sinon aujourd'hui."""
    state = await get_state(telegram_id, supabase, org_id)
    if state and state.get('last_state_data', {}).get('pointage_date'):
        return state['last_state_data']['pointage_date']
    return date.today().isoformat()


async def _build_resource_keyboard(res_list: list, pt_ressources: list, page: int = 0, type_filter: str = "homme"):
    keyboard = []
    pt_map = {pr['ressource_id']: pr['presence'] for pr in pt_ressources}

    PAGE_SIZE = 5
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = res_list[start:end]

    for r in page_items:
        presence = pt_map.get(r['id'], True)
        status = "✅" if presence else "❌"
        keyboard.append([{"text": f"{status} {r['nom']}", "callback_data": f"pt:t:{r['id']}:{page}:{type_filter}"}])

    nav = []
    if page > 0:
        nav.append({"text": "◀️", "callback_data": f"pt:p:{page-1}:{type_filter}"})
    if end < len(res_list):
        nav.append({"text": "▶️", "callback_data": f"pt:p:{page+1}:{type_filter}"})
    if nav:
        keyboard.append(nav)

    keyboard.append([{"text": "🚀 Valider", "callback_data": "pointage:validate"}])
    keyboard.append([{"text": "← Retour", "callback_data": "menu:sub:pointages"}])
    return {"inline_keyboard": keyboard}


async def handle_list_human(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str, page: int = 0):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    pointage_date = await _get_pointage_date(telegram_id, supabase, org_id)
    pt_id = await _get_pointage_for_date(supabase, chantier['id'], org_id, pointage_date)

    resources = supabase.table("chantier_ressources").select("*").eq("org_id", org_id).eq("type", "homme").execute().data
    pt_res = supabase.table("chantier_pointage_ressources").select("*").eq("pointage_id", pt_id).execute().data

    keyboard = await _build_resource_keyboard(resources, pt_res, page, "homme")
    date_display = _format_date_display(pointage_date)
    await send_message_with_keyboard(telegram_id, bot_config, f"👷‍♂️ Pointage Ressources Humaines ({date_display}, Page {page+1})", keyboard)
    return {"ok": True}


async def handle_list_machine(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str, page: int = 0):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    pointage_date = await _get_pointage_date(telegram_id, supabase, org_id)
    pt_id = await _get_pointage_for_date(supabase, chantier['id'], org_id, pointage_date)

    resources = supabase.table("chantier_ressources").select("*").eq("org_id", org_id).eq("type", "machine").execute().data
    pt_res = supabase.table("chantier_pointage_ressources").select("*").eq("pointage_id", pt_id).execute().data

    keyboard = await _build_resource_keyboard(resources, pt_res, page, "machine")
    date_display = _format_date_display(pointage_date)
    await send_message_with_keyboard(telegram_id, bot_config, f"🚜 Pointage Machines ({date_display}, Page {page+1})", keyboard)
    return {"ok": True}


from app.api.telegram_core import get_bot_token
from app.services.telegram.base_workflow import BaseTelegramWorkflow
from app.api.auth import get_supabase
from app.services.telegram.notification_service import NotificationService
from app.services.telegram.audit_service import TelegramAuditService

workflow = BaseTelegramWorkflow(
    supabase_client=get_supabase(),
    audit_service=TelegramAuditService(get_supabase()),
    notification_service=NotificationService(get_supabase())
)


async def handle_toggle_presence(telegram_id: int, res_id: str, page: int, t_type: str, bot_config: Dict, supabase: Any, org_id: str):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    pointage_date = await _get_pointage_date(telegram_id, supabase, org_id)
    pt_id = await _get_pointage_for_date(supabase, chantier['id'], org_id, pointage_date)

    existing = supabase.table("chantier_pointage_ressources") \
        .select("id, presence") \
        .eq("pointage_id", pt_id) \
        .eq("ressource_id", res_id) \
        .execute().data

    if existing:
        new_val = not existing[0]['presence']
        supabase.table("chantier_pointage_ressources") \
            .update({"presence": new_val}) \
            .eq("id", existing[0]['id']) \
            .execute()
    else:
        supabase.table("chantier_pointage_ressources").insert({
            "pointage_id": pt_id,
            "ressource_id": res_id,
            "org_id": org_id,
            "presence": False,
            "periode": "journee"
        }).execute()

    if t_type == "homme":
        return await handle_list_human(telegram_id, bot_config, supabase, org_id, page)
    return await handle_list_machine(telegram_id, bot_config, supabase, org_id, page)


async def handle_validate_pointage(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    """Marque le pointage comme 'en_attente_validation'."""
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    pointage_date = await _get_pointage_date(telegram_id, supabase, org_id)
    pt_id = await _get_pointage_for_date(supabase, chantier['id'], org_id, pointage_date)

    try:
        supabase.table("chantier_pointages") \
            .update({"statut": "en_attente_validation"}) \
            .eq("id", pt_id) \
            .execute()

        notif = NotificationService(supabase, get_bot_token(bot_config))
        await notif.notify_admins(
            org_id=org_id,
            title="Nouveau pointage",
            message=f"Pointage du {pointage_date} soumis pour validation",
            action_url=f"/dashboard/chantiers/{chantier['id']}?tab=pointages",
            action_label="Voir les pointages"
        )

        await send_simple_message(telegram_id, bot_config, "✅ Pointage soumis pour validation.")
        from app.api.bot_construction_commands import send_menu_message
        await send_menu_message(telegram_id, bot_config, supabase, org_id)
    except Exception as e:
        logger.error(f"Erreur validation pointage: {e}")
        await send_simple_message(telegram_id, bot_config, "❌ Erreur lors de la validation.")
    return {"ok": True}
