import logging
from typing import Dict, Any
from app.api.telegram_core import send_simple_message, send_message_with_keyboard, escape_markdown
from app.services.telegram.construction_menu import build_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected, set_state, get_state
from app.services.ai.extractor import extract_depense
from datetime import date

logger = logging.getLogger(__name__)

from app.api.telegram_core import get_bot_token
from app.services.telegram.base_workflow import BaseTelegramWorkflow
from app.api.auth import get_supabase
from app.services.telegram.notification_service import NotificationService
from app.services.telegram.audit_service import TelegramAuditService

workflow = BaseTelegramWorkflow(get_supabase(), TelegramAuditService(get_supabase()), NotificationService(get_supabase()))


def build_depense_type_menu() -> Dict[str, Any]:
    texte = "💵 *Nouvelle dépense*\n\nChoisis le type de dépense :"
    lignes = [
        [
            {"text": "🔧 Sous-traitant", "callback_data": "depense:type:sous_traitant"},
            {"text": "📦 Fournisseur", "callback_data": "depense:type:fournisseur"},
        ],
        [
            {"text": "📝 Autre", "callback_data": "depense:type:autre"},
        ],
        [
            {"text": "← Retour", "callback_data": "menu:sub:depenses"},
        ],
    ]
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


async def handle_depense_create(telegram_id: int, bot_config: Dict, supabase: Any = None, org_id: str = None):
    """Affiche le choix du type de dépense."""
    menu = build_depense_type_menu()
    await send_message_with_keyboard(telegram_id, bot_config, menu["text"], menu["keyboard"])
    return {"ok": True}


async def handle_depense_type_selected(telegram_id: int, categorie: str, bot_config: Dict, supabase: Any, org_id: str):
    """Stocke la catégorie choisie et demande la description."""
    ok = await set_state(telegram_id, "depense_awaiting_description", org_id, supabase, data={"categorie": categorie})
    if not ok:
        logger.error("set_state a échoué pour le type de dépense")
    await send_simple_message(telegram_id, bot_config, f"💵 *Dépense ({categorie})*\n\nDécris la dépense (fournisseur, montant) :")
    return {"ok": True}


async def handle_depense_media(message: Dict, bot_config: Dict, supabase: Any, org_id: str, state: Dict):
    telegram_id = message.get('chat', {}).get('id')
    text = message.get("text") or message.get("caption") or ""

    if not text:
        await send_simple_message(telegram_id, bot_config, "❌ Veuillez envoyer une description textuelle.")
        return {"ok": True}

    categorie = state.get('last_state_data', {}).get('categorie', 'autre')
    extracted = await extract_depense(text)

    if extracted.get("_fallback"):
        await set_state(telegram_id, "depense_awaiting_validation", org_id, supabase, data={
            "categorie": categorie, "description": text, "fournisseur": "Telegram", "montant": 0})
        await send_message_with_keyboard(telegram_id, bot_config,
            f"⚠️ *Extraction IA indisponible*\n\n{escape_markdown(text)}\n\nValide ou annule :",
            {"inline_keyboard": [[{"text": "✅ Valider", "callback_data": "depense:final_save"}], [{"text": "❌ Annuler", "callback_data": "menu:main"}]]})
        return {"ok": True}

    fournisseur = extracted.get("fournisseur") or "Telegram"
    montant = float(extracted.get("montant") or 0)
    description = extracted.get("description") or text

    await set_state(telegram_id, "depense_awaiting_validation", org_id, supabase, data={
        "categorie": extracted.get("categorie", categorie),
        "fournisseur": fournisseur,
        "montant": montant,
        "description": description
    })

    text_res = f"💵 *Confirmer cette dépense ?*\n\nFournisseur: {escape_markdown(fournisseur)}\nMontant: {montant:.2f}€\nType: {escape_markdown(extracted.get('categorie', categorie))}\nDesc: {escape_markdown(description)}"
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Valider", "callback_data": "depense:final_save"}],
            [{"text": "❌ Annuler", "callback_data": "menu:main"}]
        ]
    }

    await send_message_with_keyboard(telegram_id, bot_config, text_res, keyboard)
    return {"ok": True}


async def handle_save_depense(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    """Insère la dépense dans la DB après validation et notifie les gérants."""
    state = await get_state(telegram_id, supabase, org_id)
    if not state:
        logger.error("❌ Aucune donnée d'état trouvée pour la sauvegarde de dépense")
        return {"ok": False}

    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    data = state.get('last_state_data', {})

    depense_data = {
        "chantier_id": chantier["id"],
        "org_id": org_id,
        "description": data.get('description', 'Description manquante'),
        "fournisseur": data.get('fournisseur', 'Telegram'),
        "montant": float(data.get('montant', 0)),
        "date": date.today().isoformat(),
        "categorie": data.get('categorie', 'autre')
    }

    logger.info(f"DEBUG: Tentative d'insertion dépense: {depense_data}")
    try:
        supabase.table("chantier_depenses").insert(depense_data).execute()

        notif = NotificationService(supabase, get_bot_token(bot_config))
        await notif.notify_admins(
            org_id=org_id,
            title="Nouvelle dépense",
            message=f"Dépense {data.get('categorie', 'autre')} en attente : {data.get('description', '')[:80]}",
            action_url=f"/dashboard/chantiers/{chantier['id']}?tab=depenses",
            action_label="Voir les dépenses"
        )

        await send_simple_message(telegram_id, bot_config, "✅ Dépense enregistrée.")
        await set_state(telegram_id, "idle", org_id, supabase)
        from app.api.bot_construction_commands import send_menu_message
        await send_menu_message(telegram_id, bot_config, supabase, org_id)
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'insertion en DB: {e}")
        await send_simple_message(telegram_id, bot_config, "❌ Erreur base de données.")

    return {"ok": True}


async def handle_list_depenses(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    """Liste les dépenses du mois."""
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        from app.api.bot_construction_commands import _handle_chantier_list
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    debut_mois = date.today().replace(day=1).isoformat()
    try:
        r = supabase.table("chantier_depenses") \
            .select("fournisseur, montant, categorie, date") \
            .eq("org_id", org_id) \
            .eq("chantier_id", chantier["id"]) \
            .gte("date", debut_mois) \
            .order("date", desc=True) \
            .execute()
        depenses = r.data or []
    except Exception as e:
        logger.error(f"Erreur dépenses: {e}")
        depenses = []

    texte = f"💵 *Dépenses du mois* — {chantier.get('nom', 'Chantier')}\n\n"
    total = 0
    for d in depenses:
        montant = float(d.get("montant", 0))
        total += montant
        texte += f"• {d['date']} | {d['fournisseur']} | {montant}€\n"
    texte += f"\n*Total : {total:,.2f}€*"

    await send_simple_message(telegram_id, bot_config, texte)
    return {"ok": True}
