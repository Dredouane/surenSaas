import json
import logging
from typing import Dict, Any
from app.api.telegram_core import send_simple_message, send_message_with_keyboard, escape_markdown
from app.services.telegram.construction_menu import build_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected, set_state, get_state
from datetime import date
from app.api.telegram_core import get_bot_token
from app.services.telegram.notification_service import NotificationService
from app.services.ai.extractor import extract_and_refine_avancement

logger = logging.getLogger(__name__)


async def handle_avancement_choose_situation(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        from app.api.bot_construction_commands import _handle_chantier_list
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    try:
        result = supabase.table("chantier_situations") \
            .select("id, numero, libelle, montant") \
            .eq("org_id", org_id) \
            .eq("chantier_id", chantier["id"]) \
            .eq("statut", "ouverte") \
            .order("numero", desc=True) \
            .execute()
        situations = result.data or []
    except Exception as e:
        logger.error(f"Erreur liste situations ouvertes: {e}")
        situations = []

    if not situations:
        await send_simple_message(telegram_id, bot_config, "📄 *Aucune situation ouverte* sur ce chantier.\n\nCrée d'abord une situation depuis l'application web.")
        return {"ok": True}

    lignes = []
    for s in situations:
        lignes.append([{"text": f"📄 N°{s['numero']} — {escape_markdown(s.get('libelle', ''))[:40]}", "callback_data": f"avancement:situation:{s['id']}"}])
    lignes.append([{"text": "← Retour", "callback_data": "menu:main"}])

    keyboard = {"inline_keyboard": lignes}
    await send_message_with_keyboard(telegram_id, bot_config, "📈 *Choisis une situation ouverte*", keyboard)
    return {"ok": True}


async def handle_avancement_situation_selected(telegram_id: int, situation_id: str, bot_config: Dict, supabase: Any, org_id: str):
    ok = await set_state(telegram_id, "avancement_awaiting_ligne", org_id, supabase, data={"situation_id": situation_id})
    if not ok:
        logger.error("set_state a échoué pour avancement_awaiting_ligne")
    await send_simple_message(telegram_id, bot_config,
        "📈 *Nouvel avancement*\n\n"
        "Décris l'avancement avec ces informations :\n"
        "• Description du travail\n"
        "• Quantité réalisée\n"
        "• Prix unitaire (€)\n"
        "• % d'avancement\n"
        "• Photo (optionnelle)\n\n"
        "Exemple : *Enduit façade 50m2 25€/m2 80%*")
    return {"ok": True}


async def handle_avancement_input_data(message: Dict, bot_config: Dict, supabase: Any, org_id: str, state: Dict):
    telegram_id = message.get('chat', {}).get('id')
    text = message.get("text") or message.get("caption") or ""

    if not text:
        await send_simple_message(telegram_id, bot_config, "❌ Veuillez envoyer une description textuelle.")
        return {"ok": True}

    situation_id = state.get('last_state_data', {}).get('situation_id', '')
    extracted = await extract_and_refine_avancement(text)

    photo_url = ""
    if message.get('photo'):
        photo_url = "photo_capturee"

    if extracted.get("_fallback"):
        description = text
        await set_state(telegram_id, "avancement_awaiting_validation", org_id, supabase, data={
            "situation_id": situation_id,
            "description": description,
            "quantite": 0, "prix_unitaire": 0, "avancement_pourcentage": 0,
            "montant_total": 0, "avancement_montant": 0, "photo_url": photo_url
        })
        await send_message_with_keyboard(telegram_id, bot_config,
            f"⚠️ *Extraction IA indisponible*\n\n{escape_markdown(text)}\n\nValide ou annule :",
            {"inline_keyboard": [[{"text": "✅ Valider", "callback_data": "avancement:final_save"}], [{"text": "❌ Annuler", "callback_data": "menu:main"}]]})
        return {"ok": True}

    description = extracted.get("description") or text
    quantite = float(extracted.get("quantite", 0))
    prix_unitaire = float(extracted.get("prix_unitaire", 0))
    avancement = float(extracted.get("avancement_pourcentage", 0))
    montant_total = float(extracted.get("montant_total", 0))
    avancement_montant = float(extracted.get("avancement_montant", 0))

    await set_state(telegram_id, "avancement_awaiting_validation", org_id, supabase, data={
        "situation_id": situation_id,
        "description": description,
        "quantite": quantite,
        "prix_unitaire": prix_unitaire,
        "avancement_pourcentage": avancement,
        "montant_total": montant_total,
        "avancement_montant": avancement_montant,
        "photo_url": photo_url
    })

    text_res = (
        f"📈 *Confirmer cet avancement ?*\n\n"
        f"Desc: {escape_markdown(description)}\n"
        f"Qté: {quantite}\n"
        f"PU: {prix_unitaire}€\n"
        f"%: {avancement}%\n"
        f"Montant: {montant_total:.2f}€\n"
        f"Avancement: {avancement_montant:.2f}€\n"
    )
    if photo_url:
        text_res += "\n📸 *Photo jointe*"

    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Valider", "callback_data": "avancement:final_save"}],
            [{"text": "❌ Annuler", "callback_data": "menu:main"}]
        ]
    }

    await send_message_with_keyboard(telegram_id, bot_config, text_res, keyboard)
    return {"ok": True}


async def handle_avancement_save(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    state = await get_state(telegram_id, supabase, org_id)
    if not state:
        logger.error("❌ Aucune donnée d'état pour la sauvegarde avancement")
        return {"ok": False}

    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    data = state.get('last_state_data', {})

    ligne_data = {
        "situation_id": data.get('situation_id', ''),
        "org_id": org_id,
        "description": data.get('description', ''),
        "quantite": float(data.get('quantite', 0)),
        "unite": "m2",
        "prix_unitaire": float(data.get('prix_unitaire', 0)),
        "montant_total": float(data.get('montant_total', 0)),
        "avancement_pourcentage": float(data.get('avancement_pourcentage', 0)),
        "avancement_montant": float(data.get('avancement_montant', 0)),
        "photo_url": data.get('photo_url', ''),
        "created_by": "",
    }

    try:
        supabase.table("chantier_situation_lignes").insert(ligne_data).execute()

        notif = NotificationService(supabase, get_bot_token(bot_config))
        await notif.notify_admins(
            org_id=org_id,
            title="Nouvel avancement",
            message=f"Avancement {data.get('avancement_pourcentage', 0)}% sur situation {data.get('situation_id', '')[:8]}",
            action_url=f"/dashboard/chantiers/{chantier['id']}?tab=situations",
            action_label="Voir les avancements"
        )

        await send_simple_message(telegram_id, bot_config, "✅ Avancement enregistré.")
        await set_state(telegram_id, "idle", org_id, supabase)
        from app.api.bot_construction_commands import send_menu_message
        await send_menu_message(telegram_id, bot_config, supabase, org_id)
    except Exception as e:
        logger.error(f"❌ Erreur insertion avancement: {e}")
        await send_simple_message(telegram_id, bot_config, "❌ Erreur base de données.")

    return {"ok": True}
