import logging
from typing import Dict, Any
from app.api.telegram_core import send_message_with_keyboard, answer_callback, get_bot_token, send_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected
from datetime import date

logger = logging.getLogger(__name__)

async def _get_today_pointage(supabase, chantier_id, org_id):
    """Récupère ou crée le pointage du jour."""
    today = date.today().isoformat()
    # Chercher un pointage pour aujourd'hui
    res = supabase.table("chantier_pointages").select("id").eq("chantier_id", chantier_id).eq("date", today).execute()
    if res.data:
        return res.data[0]['id']
    
    # Créer un pointage s'il n'existe pas
    new_pt = supabase.table("chantier_pointages").insert({
        "chantier_id": chantier_id, 
        "org_id": org_id, 
        "date": today,
        "commentaires": "Auto-généré"
    }).execute()
    return new_pt.data[0]['id']

async def _build_resource_keyboard(res_list: list, pt_ressources: list, page: int = 0, type_filter: str = "homme"):
    keyboard = []
    pt_map = {pr['ressource_id']: pr['presence'] for pr in pt_ressources}
    
    # Pagination
    PAGE_SIZE = 5
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = res_list[start:end]
    
    for r in page_items:
        presence = pt_map.get(r['id'], True)
        status = "✅" if presence else "❌"
        # callback_data compact pour rester sous 64 octets
        keyboard.append([{"text": f"{status} {r['nom']}", "callback_data": f"pt:t:{r['id']}:{page}:{type_filter}"}])
    
    # Navigation
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
    pt_id = await _get_today_pointage(supabase, chantier['id'], org_id)
    
    resources = supabase.table("chantier_ressources").select("*").eq("org_id", org_id).eq("type", "homme").execute().data
    pt_res = supabase.table("chantier_pointage_ressources").select("*").eq("pointage_id", pt_id).execute().data
    
    keyboard = await _build_resource_keyboard(resources, pt_res, page, "homme")
    
    # Utilisation de editMessageText via helper ou envoi classique si premier message
    await send_message_with_keyboard(telegram_id, bot_config, f"👷‍♂️ Pointage Ressources Humaines (Page {page+1})", keyboard)
    return {"ok": True}

async def handle_list_machine(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str, page: int = 0):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    pt_id = await _get_today_pointage(supabase, chantier['id'], org_id)
    
    resources = supabase.table("chantier_ressources").select("*").eq("org_id", org_id).eq("type", "machine").execute().data
    pt_res = supabase.table("chantier_pointage_ressources").select("*").eq("pointage_id", pt_id).execute().data
    
    keyboard = await _build_resource_keyboard(resources, pt_res, page, "machine")
    await send_message_with_keyboard(telegram_id, bot_config, f"🚜 Pointage Machines (Page {page+1})", keyboard)
    return {"ok": True}



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
    pt_id = await _get_today_pointage(supabase, chantier['id'], org_id)
    
    # 1. Vérifier si l'entrée existe pour cette ressource dans ce pointage
    existing = supabase.table("chantier_pointage_ressources") \
        .select("id, presence") \
        .eq("pointage_id", pt_id) \
        .eq("ressource_id", res_id) \
        .execute().data
    
    # 2. Toggle logique
    if existing:
        new_val = not existing[0]['presence']
        supabase.table("chantier_pointage_ressources") \
            .update({"presence": new_val}) \
            .eq("id", existing[0]['id']) \
            .execute()
    else:
        # Création de l'entrée si elle n'existe pas, on initialise à False
        supabase.table("chantier_pointage_ressources").insert({
            "pointage_id": pt_id, 
            "ressource_id": res_id, 
            "org_id": org_id, 
            "presence": False
        }).execute()
    
    # Rafraîchir l'interface (pagination maintenue)
    if t_type == "homme":
        return await handle_list_human(telegram_id, bot_config, supabase, org_id, page)
    return await handle_list_machine(telegram_id, bot_config, supabase, org_id, page)


async def handle_validate_pointage(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    """Marque le pointage du jour comme 'en_attente_validation'."""
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    pt_id = await _get_today_pointage(supabase, chantier['id'], org_id)
    
    try:
        supabase.table("chantier_pointages") \
            .update({"statut": "en_attente_validation"}) \
            .eq("id", pt_id) \
            .execute()
        await send_simple_message(telegram_id, bot_config, "✅ Pointage soumis pour validation.")
        from app.api.bot_construction_commands import send_menu_message
        await send_menu_message(telegram_id, bot_config, supabase, org_id)
    except Exception as e:
        logger.error(f"Erreur validation pointage: {e}")
        await send_simple_message(telegram_id, bot_config, "❌ Erreur lors de la validation.")
    return {"ok": True}

