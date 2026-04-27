"""Bot Construction — Menu principal, callbacks dispatcher central, handlers de navigation."""
from typing import Dict, Any, Optional
import re
import logging
from datetime import datetime, date

from app.api.telegram_core import (
    send_simple_message,
    send_message_with_keyboard,
    get_bot_token,
    answer_callback,
)
from app.services.telegram.construction_menu import (
    build_main_menu,
    build_operations_submenu,
    build_pointages_submenu,
    build_taches_submenu,
    build_finances_submenu,
    build_receptions_submenu,
    build_chantier_list,
    build_simple_message,
)
from app.services.telegram.chantier_context import (
    get_active_chantier,
    set_active_chantier,
    list_accessible_chantiers,
    ensure_chantier_selected,
)

logger = logging.getLogger(__name__)


# ================================================================
# DISPATCHER CENTRAL — un seul point d'entrée pour tous les callbacks
# ================================================================

async def handle_construction_callback(
    callback_query: Dict[str, Any],
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str,
) -> Dict[str, Any]:
    """Dispatche tous les callbacks du bot construction vers le bon handler."""
    from_user = callback_query.get("from", {})
    chat_id = from_user.get("id")
    data = callback_query.get("data", "")
    logger.info(f"🔘 DISPATCHER CALL: Data='{data}'")
    
    # ... reste du code ...

    # === Factures (nouveau dispatcher) ===
    if data.startswith("invoice:validate:"):
        from app.api.bot_construction_invoices import handle_invoice_validation
        invoice_id = data.split(":", 2)[2]
        return await handle_invoice_validation(chat_id, invoice_id, bot_config, supabase, org_id)
    if data.startswith("invoice:cancel:"):
        from app.api.bot_construction_invoices import handle_invoice_cancellation
        invoice_id = data.split(":", 2)[2]
        return await handle_invoice_cancellation(chat_id, invoice_id, bot_config, supabase, org_id)
    if data.startswith("invoice:edit:"):
        await send_simple_message(
            chat_id,
            bot_config,
            "✏️ *Modifier la facture*\n\nCette fonctionnalité sera disponible prochainement.",
        )
        return {"ok": True}

    # === Navigation ===
    if data == "menu:main":
        return await _handle_menu_main(chat_id, bot_config, supabase, org_id)
    if data == "menu:sub:operations":
        return await _handle_sub_operations(chat_id, bot_config)
    if data == "menu:sub:pointages":
        return await _handle_sub_pointages(chat_id, bot_config, supabase, org_id)
    if data == "menu:sub:taches":
        return await _handle_sub_taches(chat_id, bot_config)
    # === Factures & Dépenses ===
    if data == "menu:sub:finances":
        from app.api.bot_construction_invoices import handle_invoice_menu
        return await handle_invoice_menu(chat_id, bot_config)
    if data.startswith("invoice:edit:"):
        from app.api.bot_construction_invoices import handle_edit_invoice_step1
        invoice_id = data.split(":", 2)[2]
        return await handle_edit_invoice_step1(chat_id, invoice_id, bot_config)
    if data == "menu:sub:receptions":
        return await _handle_sub_receptions(chat_id, bot_config)
    if data == "menu:help":
        return await _handle_menu_help(chat_id, bot_config)
    if data == "service:invoice_upload":
        return await _handle_invoice_upload(chat_id, bot_config)

    # === Chantier ===
    if data == "chantier:list":
        return await _handle_chantier_list(chat_id, bot_config, supabase, org_id)
    if data.startswith("chantier:select:"):
        chantier_id = data.split(":", 2)[2]
        return await _handle_chantier_select(
            chat_id, chantier_id, bot_config, supabase, org_id
        )

    # === Opérations ===
    if data == "op:list:pending":
        from app.api.bot_construction_operations import handle_list_pending_operations
        return await handle_list_pending_operations(chat_id, bot_config, supabase, org_id)
    if data.startswith("op:create:"):
        op_type = data.split(":", 2)[2]
        from app.api.bot_construction_operations import handle_create_operation
        return await handle_create_operation(chat_id, op_type, bot_config, supabase, org_id)
    if data == "op:final_save":
        from app.api.bot_construction_operations import handle_save_operation
        return await handle_save_operation(chat_id, bot_config, supabase, org_id)


    # === Pointages ===
    if data == "pointage:list:human":
        from app.api.bot_construction_pointages import handle_list_human
        return await handle_list_human(chat_id, bot_config, supabase, org_id)
    if data == "pointage:list:machine":
        from app.api.bot_construction_pointages import handle_list_machine
        return await handle_list_machine(chat_id, bot_config, supabase, org_id)
    if data.startswith("pt:t:"):
        from app.api.bot_construction_pointages import handle_toggle_presence
        parts = data.split(":")
        res_id, page, t_type = parts[2], int(parts[3]), parts[4]
        return await handle_toggle_presence(chat_id, res_id, page, t_type, bot_config, supabase, org_id)
    if data.startswith("pt:p:"):
        from app.api.bot_construction_pointages import handle_list_human, handle_list_machine
        parts = data.split(":")
        page, t_type = int(parts[2]), parts[3]
        if t_type == "homme":
            return await handle_list_human(chat_id, bot_config, supabase, org_id, page)
        else:
            return await handle_list_machine(chat_id, bot_config, supabase, org_id, page)
    if data == "pointage:validate":
        from app.api.bot_construction_pointages import handle_validate_pointage
        return await handle_validate_pointage(chat_id, bot_config, supabase, org_id)

    # === Tâches ===
    if data.startswith("tache:list:"):
        from app.api.bot_construction_taches import handle_list_taches
        statut = data.split(":", 2)[2]
        return await handle_list_taches(chat_id, statut, bot_config, supabase, org_id)
    if data == "tache:ask_done":
        from app.api.bot_construction_taches import handle_ask_done
        return await handle_ask_done(chat_id, bot_config)

    # === Dépenses ===
    if data == "depense:create":
        from app.api.bot_construction_depenses import handle_depense_create
        return await handle_depense_create(chat_id, bot_config, supabase, org_id)
    if data == "depense:final_save":
        from app.api.bot_construction_depenses import handle_save_depense
        return await handle_save_depense(chat_id, bot_config, supabase, org_id)
    if data == "depense:list:month":
        from app.api.bot_construction_depenses import handle_list_depenses
        return await handle_list_depenses(chat_id, bot_config, supabase, org_id)

    # === Réceptions ===
    if data == "rec:list:upcoming":
        from app.api.bot_construction_receptions import handle_list_receptions
        return await handle_list_receptions(chat_id, bot_config, supabase, org_id)
    if data == "rec:add_point":
        from app.api.bot_construction_receptions import handle_add_point_reception
        return await handle_add_point_reception(chat_id, bot_config)

    # === Stats ===
    if data == "stats:show":
        return await _handle_stats_show(
            chat_id, bot_config, supabase, org_id
        )

    # Si callback inconnu → menu principal
    logger.warning(f"Callback non reconnu: {data}, redirection vers menu")
    return await _handle_menu_main(chat_id, bot_config, supabase, org_id)


# ================================================================
# HANDLERS DE NAVIGATION
# ================================================================

async def _handle_menu_main(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
) -> Dict[str, Any]:
    """Affiche le menu principal."""
    from_user = None
    chantier = None
    try:
        from_user = (
            supabase.table("telegram_users")
            .select("telegram_id")
            .eq("telegram_id", chat_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )
    except Exception:
        pass

    if from_user and from_user.data:
        chantier = await get_active_chantier(chat_id, supabase, org_id)

    chantiers = await list_accessible_chantiers(chat_id, supabase, org_id)

    menu = build_main_menu(
        chantier_nom=chantier.get("nom") if chantier else None,
        chantier_count=len(chantiers),
    )
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


async def _handle_sub_operations(chat_id: int, bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Sous-menu opérations."""
    menu = build_operations_submenu()
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


async def _handle_sub_pointages(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
) -> Dict[str, Any]:
    """Sous-menu pointages."""
    aujourd_hui = date.today().strftime("%d/%m/%Y")
    
    # Appel simplifié au nouveau menu
    menu = build_pointages_submenu(aujourd_hui)
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


async def _handle_sub_taches(chat_id: int, bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Sous-menu tâches."""
    menu = build_taches_submenu()
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


# (Handlers finances déplacés vers bot_construction_invoices.py)


async def _handle_sub_receptions(chat_id: int, bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Sous-menu réunions."""
    menu = build_receptions_submenu()
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


async def _handle_menu_help(chat_id: int, bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Affiche l'aide."""
    menu = build_simple_message(
        "❓ *Aide*\n\n"
        "• Utilise le menu pour naviguer entre les fonctions.\n"
        "• *Signaler une opération* → Choisis un type, puis décris-la\n"
        "• *Pointer présence* → Marque ta présence du jour\n"
        "• *Mes tâches* → Consulte et marque tes tâches comme faites\n"
        "• *Factures* → Envoie une photo/PDF de ta facture\n\n"
        "Besoin d'aide ? Contacte ton administrateur."
    )
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


async def _handle_invoice_upload(chat_id: int, bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Redirige vers l'upload de facture."""
    menu = build_simple_message(
        "📄 *Envoyer une facture*\n\n"
        "Envoie une photo ou un PDF de ta facture.\n"
        "Je vais l'analyser automatiquement."
    )
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


# ================================================================
# HANDLERS CHANTIER
# ================================================================

async def _handle_chantier_list(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
) -> Dict[str, Any]:
    """Affiche la liste des chantiers pour sélection."""
    chantiers = await list_accessible_chantiers(chat_id, supabase, org_id)
    if not chantiers:
        menu = build_simple_message(
            "🏗️ *Aucun chantier trouvé*\n\n"
            "Tu n'es assigné à aucun chantier pour le moment.\n"
            "Contacte ton administrateur.",
            bouton_retour=True,
        )
        await send_message_with_keyboard(
            chat_id, bot_config, menu["text"], menu["keyboard"]
        )
        return {"ok": True}

    menu = build_chantier_list(chantiers)
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


async def _handle_chantier_select(
    chat_id: int,
    chantier_id: str,
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str,
) -> Dict[str, Any]:
    """Sélectionne un chantier et affiche le menu principal."""
    ok = await set_active_chantier(chat_id, chantier_id, supabase, org_id)
    if not ok:
        await send_simple_message(
            chat_id, bot_config, "❌ Erreur lors de la sélection du chantier."
        )
        return {"ok": False}

    chantier = await get_active_chantier(chat_id, supabase, org_id)
    nom = chantier.get("nom", "Chantier") if chantier else "Chantier"
    await send_simple_message(
        chat_id, bot_config, f"✅ Chantier sélectionné : *{nom}*"
    )
    return await _handle_menu_main(chat_id, bot_config, supabase, org_id)


# ================================================================
# HANDLERS OPÉRATIONS (placeholders — seront détaillés dans PR2)
# ================================================================

async def _handle_op_list_pending(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
) -> Dict[str, Any]:
    """Liste les opérations en attente."""
    chantier = await ensure_chantier_selected(chat_id, supabase, org_id)
    if not chantier:
        return await _handle_chantier_list(chat_id, bot_config, supabase, org_id)

    try:
        result = (
            supabase.table("chantier_operations_htl")
            .select("id, description, type, date, source, montant")
            .eq("org_id", org_id)
            .eq("chantier_id", chantier["id"])
            .eq("statut", "en_attente")
            .order("date", desc=True)
            .limit(10)
            .execute()
        )
        ops = result.data or []
    except Exception as e:
        logger.error(f"Erreur liste opérations: {e}")
        ops = []

    if not ops:
        menu = build_simple_message(
            f"✅ *Aucune opération en attente*\nsur *{chantier.get('nom', 'le chantier')}*.",
            bouton_retour=True,
        )
    else:
        lignes = []
        from app.api.telegram_core import escape_markdown
        texte = f"📄 *Opérations en attente* — {escape_markdown(chantier.get('nom', 'Chantier'))}\n\n"
        for op in ops:
            d = escape_markdown(op.get('description', '')[:80])
            t = escape_markdown(op.get('type', 'Opération'))
            s = escape_markdown(op.get('source', ''))
            texte += (
                f"• *{t}* — {d}\n"
                f"  _{op.get('date', '')[:10]} | {s}_\n\n"
            )
        menu = {
            "text": texte,
            "keyboard": {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔄 Rafraîchir",
                            "callback_data": "op:list:pending",
                        }
                    ],
                    [
                        {
                            "text": "← Retour au menu",
                            "callback_data": "menu:main",
                        }
                    ],
                ]
            },
        }

    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


# (Le handler _handle_op_create a été déplacé vers bot_construction_operations.py)


# ================================================================
# HANDLERS POINTAGES (placeholders)
# ================================================================

# (Handlers pointages déplacés vers bot_construction_pointages.py)


# ================================================================
# HANDLERS TÂCHES (placeholders)
# ================================================================

# (Handlers tâches déplacés vers bot_construction_taches.py)


# ================================================================
# HANDLERS DÉPENSES (placeholders)
# ================================================================

# (Handlers dépenses et réceptions déplacés)



async def _handle_depense_list_month(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
) -> Dict[str, Any]:
    """Affiche les dépenses du mois courant."""
    chantier = await ensure_chantier_selected(chat_id, supabase, org_id)
    if not chantier:
        return await _handle_chantier_list(chat_id, bot_config, supabase, org_id)

    debut_mois = date.today().replace(day=1).isoformat()
    try:
        r = (
            supabase.table("chantier_depenses")
            .select("fournisseur, montant, categorie, date")
            .eq("org_id", org_id)
            .eq("chantier_id", chantier["id"])
            .gte("date", debut_mois)
            .order("date", desc=True)
            .limit(20)
            .execute()
        )
        depenses = r.data or []
    except Exception as e:
        logger.error(f"Erreur liste dépenses: {e}")
        depenses = []

    if not depenses:
        texte = f"💵 *Aucune dépense* enregistrée ce mois sur *{chantier.get('nom', 'le chantier')}*."
    else:
        total = sum(float(d.get("montant", 0)) for d in depenses)
        texte = f"💵 *Dépenses du mois* — {chantier.get('nom', 'Chantier')}\n\n"
        for d in depenses:
            texte += f"• {d['date'][:10]} — *{d['fournisseur']}* — {float(d.get('montant', 0)):,.2f}€ ({d.get('categorie', '')})\n"
        texte += f"\n*Total : {total:,.2f}€*"

    menu = build_simple_message(texte, bouton_retour=True)
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


# ================================================================
# HANDLERS RÉCEPTIONS (placeholders)
# ================================================================

async def _handle_rec_list_upcoming(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
) -> Dict[str, Any]:
    """Liste les prochaines réunions."""
    chantier = await ensure_chantier_selected(chat_id, supabase, org_id)
    if not chantier:
        return await _handle_chantier_list(chat_id, bot_config, supabase, org_id)

    aujourd_hui = date.today().isoformat()
    try:
        r = (
            supabase.table("chantier_receptions")
            .select("id, date, type, statut, participants")
            .eq("org_id", org_id)
            .eq("chantier_id", chantier["id"])
            .gte("date", aujourd_hui)
            .order("date")
            .limit(10)
            .execute()
        )
        recs = r.data or []
    except Exception as e:
        logger.error(f"Erreur liste réceptions: {e}")
        recs = []

    if not recs:
        texte = f"📅 *Aucune réunion* prévue sur *{chantier.get('nom', 'le chantier')}*."
    else:
        texte = f"📅 *Prochaines réunions* — {chantier.get('nom', 'Chantier')}\n\n"
        for r_ in recs:
            texte += f"• {r_['date'][:10]} — *{r_.get('type', 'Réunion')}* — {r_.get('statut', '')}\n"

    menu = build_simple_message(texte, bouton_retour=True)
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


async def _handle_rec_add_point(chat_id: int, bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Ajoute un point à régler (placeholder)."""
    menu = build_simple_message(
        "📝 *Noter un point à régler*\n\n"
        "Décris le point à aborder lors de la prochaine réunion.\n"
        "Cette fonctionnalité sera détaillée dans une version future.",
        bouton_retour=True,
    )
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


# ================================================================
# HANDLERS STATS (placeholder)
# ================================================================

async def _handle_stats_show(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
) -> Dict[str, Any]:
    """Affiche les indicateurs du chantier."""
    chantier = await ensure_chantier_selected(chat_id, supabase, org_id)
    if not chantier:
        return await _handle_chantier_list(chat_id, bot_config, supabase, org_id)

    texte = f"📊 *Indicateurs* — {chantier.get('nom', 'Chantier')}\n\n"
    try:
        info = (
            supabase.table("chantiers")
            .select("montant_base, ts_avenants, montant_revise, situations_facturees, total_depenses, marge_brute, solde_a_facturer")
            .eq("id", chantier["id"])
            .single()
            .execute()
        )
        d = info.data or {}
        avancement = (
            f"{float(d.get('situations_facturees', 0)) / float(d.get('montant_revise', 1)) * 100:.0f}%"
            if d.get("montant_revise")
            else "N/A"
        )
        texte += (
            f"💰 *Avancement facturation :* {avancement}\n"
            f"📉 *Marge brute :* {float(d.get('marge_brute', 0)):,.2f}€\n"
            f"💵 *Total dépenses :* {float(d.get('total_depenses', 0)):,.2f}€\n"
            f"📊 *Solde à facturer :* {float(d.get('solde_a_facturer', 0)):,.2f}€\n"
        )
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        texte += "_(Données non disponibles)_"

    menu = build_simple_message(texte, bouton_retour=True)
    await send_message_with_keyboard(
        chat_id, bot_config, menu["text"], menu["keyboard"]
    )
    return {"ok": True}


# ================================================================
# COMMANDES /START ET WELCOME (inchangé)
# ================================================================

async def handle_start_command(
    message: Dict[str, Any],
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str,
) -> Dict[str, Any]:
    """Gère la commande /start avec user_id."""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    from_user = message.get("from", {})

    parts = text.split(" ", 1)
    if len(parts) < 2:
        logger.warning(f"User ID manquant dans /start de {chat_id}")
        await send_simple_message(
            chat_id,
            bot_config,
            "👋 Bienvenue !\n\nVeuillez utiliser un lien d'invitation valide.\n"
            "Contactez votre administrateur.",
        )
        return {"ok": True}

    user_id = parts[1].strip()
    logger.info(f"🔗 User ID reçu: {user_id}")

    if not re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        user_id.lower(),
    ):
        logger.error(f"Format user_id invalide: {user_id}")
        await send_simple_message(
            chat_id, bot_config, "❌ Lien d'invitation invalide."
        )
        return {"ok": True}

    user_result = (
        supabase.table("users")
        .select("email, full_name")
        .eq("id", user_id)
        .eq("org_id", org_id)
        .execute()
    )
    if not user_result.data:
        logger.error(f"User {user_id} non trouvé")
        await send_simple_message(
            chat_id, bot_config, "❌ Utilisateur non trouvé."
        )
        return {"ok": True}

    user_info = user_result.data[0]
    first_name = from_user.get(
        "first_name", user_info.get("full_name", "Utilisateur")
    )

    telegram_id = from_user.get("id")
    username = from_user.get("username")

    try:
        existing = (
            supabase.table("telegram_users")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("org_id", org_id)
            .execute()
        )
        if not existing.data:
            supabase.table("telegram_users").insert(
                {
                    "org_id": org_id,
                    "user_id": user_id,
                    "telegram_id": telegram_id,
                    "telegram_username": username,
                    "telegram_first_name": from_user.get("first_name"),
                    "telegram_last_name": from_user.get("last_name"),
                    "is_verified": True,
                    "notification_enabled": True,
                    "started_at": "now()",
                    "last_activity_at": "now()",
                }
            ).execute()
            logger.info(f"✅ Compte Telegram lié à l'utilisateur {user_id}")
        else:
            supabase.table("telegram_users").update(
                {"last_activity_at": "now()"}
            ).eq("telegram_id", telegram_id).execute()
    except Exception as e:
        logger.error(f"Erreur liaison compte: {e}")

    await _send_welcome_message(chat_id, first_name, bot_config, supabase, org_id)
    return {"ok": True}


async def send_menu_message(
    chat_id: int, bot_config: Dict[str, Any], supabase: Any, org_id: str
):
    """Point d'entrée public : affiche le menu principal."""
    await _handle_menu_main(chat_id, bot_config, supabase, org_id)


async def _send_welcome_message(
    chat_id: int,
    first_name: str,
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str,
):
    """Envoie le message de bienvenue, puis le menu principal."""
    await send_simple_message(
        chat_id,
        bot_config,
        f"👋 *Bienvenue {first_name} !*\n\n"
        f"Tu es connecté au *Bot Construction*.\n\n"
        f"📋 Sélectionne un chantier pour commencer.",
    )
    await _handle_menu_main(chat_id, bot_config, supabase, org_id)
