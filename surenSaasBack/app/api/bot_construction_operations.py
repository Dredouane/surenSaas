import logging
from typing import Dict, Any
from app.api.telegram_core import send_simple_message, send_message_with_keyboard, escape_markdown
from app.services.telegram.construction_menu import build_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected, set_state, get_state
from app.services.ai.extractor import extract_operation
from app.services.telegram.base_workflow import BaseTelegramWorkflow
from app.api.auth import get_supabase
from app.services.telegram.notification_service import NotificationService
from app.services.telegram.audit_service import TelegramAuditService
from app.api.bot_construction_commands import _handle_chantier_list, send_menu_message

logger = logging.getLogger(__name__)

notification_service_for_webhook = NotificationService(get_supabase())
workflow = BaseTelegramWorkflow(get_supabase(), TelegramAuditService(get_supabase()), notification_service_for_webhook)


async def handle_create_operation(telegram_id: int, op_type: str, bot_config: Dict, supabase: Any, org_id: str):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    await set_state(telegram_id, "op_awaiting_description", org_id, supabase, data={"op_type": op_type})
    await send_simple_message(telegram_id, bot_config, f"📸 *Nouvelle opération ({op_type})*\n\nDécris l'opération (texte/photo) :")
    return {"ok": True}


async def handle_operation_media(message: Dict, bot_config: Dict, supabase: Any, org_id: str, state: Dict):
    telegram_id = message.get('chat', {}).get('id')
    text = message.get("text") or message.get("caption") or ""

    if not text:
        await send_simple_message(telegram_id, bot_config, "❌ Veuillez envoyer une description textuelle.")
        return {"ok": True}

    op_type = state.get('last_state_data', {}).get('op_type', 'autre')
    extracted = await extract_operation(text)

    photo_url = ""
    if message.get('photo'):
        photo_url = "photo_capturee"

    description = extracted.get("description", text)
    if extracted.get("_fallback"):
        await set_state(telegram_id, "op_awaiting_validation", org_id, supabase, data={
            "op_type": op_type, "description": text, "photo_url": photo_url})
        await send_message_with_keyboard(telegram_id, bot_config,
            f"⚠️ *Extraction IA indisponible*\n\n{escape_markdown(text)}\n\nValide ou annule :",
            {"inline_keyboard": [[{"text": "✅ Valider", "callback_data": "op:final_save"}], [{"text": "❌ Annuler", "callback_data": "menu:main"}]]})
        return {"ok": True}

    montant = extracted.get("montant")
    quantite = extracted.get("quantite")
    unite = extracted.get("unite")

    await set_state(telegram_id, "op_awaiting_validation", org_id, supabase, data={
        "op_type": extracted.get("type", op_type),
        "description": description,
        "montant": montant,
        "quantite": quantite,
        "unite": unite,
        "photo_url": photo_url
    })

    text_res = f"📝 *Confirmer cette opération ?*\n\nType: {escape_markdown(extracted.get('type', op_type))}\nDesc: {escape_markdown(description)}"
    if montant: text_res += f"\nMontant: {montant}€"
    if quantite: text_res += f"\nQté: {quantite} {unite or ''}"

    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Valider", "callback_data": "op:final_save"}],
            [{"text": "❌ Annuler", "callback_data": "menu:main"}]
        ]
    }

    await send_message_with_keyboard(telegram_id, bot_config, text_res, keyboard)
    return {"ok": True}


async def handle_save_operation(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    state = await get_state(telegram_id, supabase, org_id)
    if not state:
        logger.error("❌ Aucune donnée d'état trouvée pour la sauvegarde")
        return {"ok": False}

    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    data = state.get('last_state_data', {})

    op_data = {
        "chantier_id": chantier["id"],
        "org_id": org_id,
        "description": data.get('description', 'Description manquante'),
        "statut": "en_attente",
        "type": data.get('op_type', 'autre'),
        "montant": data.get('montant'),
        "quantite": data.get('quantite'),
        "unite": data.get('unite'),
        "photo_url": data.get('photo_url', '')
    }

    logger.info(f"DEBUG: Tentative d'insertion opération: {op_data}")
    try:
        supabase.table("chantier_operations_htl").insert(op_data).execute()
        notif = NotificationService(supabase, get_bot_token(bot_config))
        await notif.notify_admins(
            org_id=org_id,
            title="Nouvelle opération",
            message=f"Opération {data.get('op_type', 'autre')} en attente de validation",
            action_url=f"/dashboard/chantiers/{chantier['id']}?tab=operations",
            action_label="Voir les opérations"
        )

        await send_simple_message(telegram_id, bot_config, "✅ Opération enregistrée.")
        await set_state(telegram_id, "idle", org_id, supabase)
        await send_menu_message(telegram_id, bot_config, supabase, org_id)
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'insertion en DB: {e}")
        await send_simple_message(telegram_id, bot_config, "❌ Erreur base de données.")

    return {"ok": True}


async def handle_list_pending_operations(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    try:
        result = (
            supabase.table("chantier_operations_htl")
            .select("id, description, type, date, source, statut")
            .eq("org_id", org_id)
            .eq("chantier_id", chantier["id"])
            .order("date", desc=True)
            .limit(20)
            .execute()
        )
        ops = result.data or []
    except Exception as e:
        logger.error(f"Erreur liste opérations: {e}")
        ops = []

    if not ops:
        menu = build_simple_message(
            f"📄 *Aucune opération* sur *{chantier.get('nom', 'le chantier')}*.",
            bouton_retour=True,
        )
    else:
        texte = f"📄 *Opérations* — {escape_markdown(chantier.get('nom', 'Chantier'))}\n\n"
        for op in ops:
            d = escape_markdown(op.get('description', '')[:100])
            t = escape_markdown(op.get('type', 'Opération'))
            s = escape_markdown(op.get('source', ''))
            st = escape_markdown(op.get('statut', ''))
            texte += (
                f"• *{t}* — {d}\n"
                f"  _{op.get('date', '')[:10]} | {s} | {st}_\n\n"
            )
        menu = {
            "text": texte,
            "keyboard": {
                "inline_keyboard": [
                    [{"text": "🔄 Rafraîchir", "callback_data": "op:list:pending"}],
                    [{"text": "← Retour au menu", "callback_data": "menu:main"}],
                ]
            },
        }

    await send_message_with_keyboard(telegram_id, bot_config, menu["text"], menu["keyboard"])
    return {"ok": True}

from app.api.telegram_core import get_bot_token
