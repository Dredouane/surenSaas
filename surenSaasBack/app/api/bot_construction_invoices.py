import logging
from typing import Dict, Any
from datetime import date
from app.api.telegram_core import send_simple_message, send_message_with_keyboard, escape_markdown
from app.services.telegram.construction_menu import build_simple_message
from app.services.telegram.chantier_context import ensure_chantier_selected

logger = logging.getLogger(__name__)

async def handle_situation_list(telegram_id: int, bot_config: Dict, supabase: Any, org_id: str):
    """Liste les situations (facturation client) du chantier actif."""
    chantier = await ensure_chantier_selected(telegram_id, supabase, org_id)
    if not chantier:
        from app.api.bot_construction_commands import _handle_chantier_list
        return await _handle_chantier_list(telegram_id, bot_config, supabase, org_id)

    try:
        r = supabase.table("chantier_situations") \
            .select("numero, date, libelle, montant") \
            .eq("org_id", org_id) \
            .eq("chantier_id", chantier["id"]) \
            .order("numero") \
            .execute()
        situations = r.data or []
    except Exception as e:
        logger.error(f"Erreur liste situations: {e}")
        situations = []

    if not situations:
        texte = f"📄 *Aucune situation* sur *{chantier.get('nom', 'le chantier')}*."
    else:
        total = sum(float(s.get("montant", 0)) for s in situations)
        texte = f"📄 *Situations facturées* — {chantier.get('nom', 'Chantier')}\n\n"
        for s in situations:
            texte += f"• N°{s['numero']} — {s['date'][:10]} — *{escape_markdown(s.get('libelle', ''))}* — {float(s.get('montant', 0)):,.2f}€\n"
        texte += f"\n*Total facturé : {total:,.2f}€*"

    menu = build_simple_message(texte, bouton_retour=True)
    await send_message_with_keyboard(telegram_id, bot_config, menu["text"], menu["keyboard"])
    return {"ok": True}

async def handle_invoice_menu(telegram_id: int, bot_config: Dict):
    """Affiche le sous-menu factures avec options d'édition."""
    await send_simple_message(telegram_id, bot_config, "📄 Envoie une photo ou un PDF de ta facture.")
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
