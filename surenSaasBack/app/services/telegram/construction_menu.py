"""Construction Menu — logique des menus et mapping callbacks → handlers."""
from typing import Dict, Any, Optional, List, Callable, Awaitable

CallbackHandler = Callable[..., Awaitable[Dict[str, Any]]]


def build_main_menu(
    chantier_nom: Optional[str] = None,
    chantier_count: int = 0,
) -> Dict[str, Any]:
    texte_parts = ["📋 *Menu principal*"]

    if chantier_nom:
        texte_parts.append(f"\n🏗️ Chantier actif : *{chantier_nom}*")
    elif chantier_count > 0:
        texte_parts.append(
            "\n_💡 Sélectionne d'abord un chantier avec le bouton ci-dessous_"
        )
    else:
        texte_parts.append(
            "\n_💡 Aucun chantier trouvé. Contacte ton administrateur._"
        )

    texte_parts.append("\nQue souhaites-tu faire ?")

    lignes = [
        [
            {
                "text": "📸 Signaler une opération",
                "callback_data": "menu:sub:operations",
            },
            {
                "text": "👷‍♂️ Pointer présence",
                "callback_data": "menu:sub:pointages",
            },
        ],
        [
            {
                "text": "📄 Opérations en attente",
                "callback_data": "op:list:pending",
            },
            {
                "text": "📋 Mes tâches",
                "callback_data": "menu:sub:taches",
            },
        ],
        [
            {
                "text": "💰 Factures & Dépenses",
                "callback_data": "menu:sub:finances",
            },
            {
                "text": "📅 Réunions",
                "callback_data": "menu:sub:receptions",
            },
        ],
        [
            {
                "text": "📊 Indicateurs",
                "callback_data": "stats:show",
            },
            {
                "text": "🏗️ Changer de chantier",
                "callback_data": "chantier:list",
            },
        ],
        [
            {
                "text": "❓ Aide",
                "callback_data": "menu:help",
            },
        ],
    ]

    return {
        "text": "\n".join(texte_parts),
        "keyboard": {"inline_keyboard": lignes},
    }


def build_operations_submenu() -> Dict[str, Any]:
    texte = (
        "📸 *Signaler une opération*\n\n"
        "Choisis le type d'opération à signaler :"
    )
    lignes = [
        [
            {
                "text": "🏗️ Démolition",
                "callback_data": "op:create:demolition",
            },
            {
                "text": "🧹 Nettoyage",
                "callback_data": "op:create:nettoyage",
            },
        ],
        [
            {
                "text": "🪟 Pose BSO",
                "callback_data": "op:create:pose_bso",
            },
            {
                "text": "📦 Commande",
                "callback_data": "op:create:commande",
            },
        ],
        [
            {
                "text": "🛒 Achat matériel",
                "callback_data": "op:create:achat_materiel",
            },
            {
                "text": "🔧 Sous-traitance",
                "callback_data": "op:create:sous_traitance",
            },
        ],
        [
            {
                "text": "📝 Autre",
                "callback_data": "op:create:autre",
            },
        ],
        [
            {
                "text": "← Retour au menu",
                "callback_data": "menu:main",
            },
        ],
    ]
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


def build_pointages_submenu(date_str: str) -> Dict[str, Any]:
    texte = f"👷‍♂️ *Pointages du {date_str}*\n\nChoisis une catégorie :"
    lignes = [
        [
            {
                "text": "👷‍♂️ Ressources Humaines",
                "callback_data": "pointage:list:human",
            },
            {
                "text": "🚜 Machines",
                "callback_data": "pointage:list:machine",
            },
        ],
        [
            {
                "text": "← Retour au menu",
                "callback_data": "menu:main",
            },
        ],
    ]
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


def build_taches_submenu() -> Dict[str, Any]:
    texte = "📋 *Mes tâches*\n\nChoisis une option :"
    lignes = [
        [
            {
                "text": "⏳ En attente",
                "callback_data": "tache:list:en_attente",
            },
            {
                "text": "🔄 En cours",
                "callback_data": "tache:list:en_cours",
            },
        ],
        [
            {
                "text": "✅ Terminées",
                "callback_data": "tache:list:terminee",
            },
            {
                "text": "📝 Marquer comme faite",
                "callback_data": "tache:ask_done",
            },
        ],
        [
            {
                "text": "← Retour au menu",
                "callback_data": "menu:main",
            },
        ],
    ]
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


def build_finances_submenu() -> Dict[str, Any]:
    texte = "💰 *Factures & Dépenses*\n\nChoisis une option :"
    lignes = [
        [
            {
                "text": "📄 Envoyer une facture",
                "callback_data": "service:invoice_upload",
            },
            {
                "text": "💵 Signaler une dépense",
                "callback_data": "depense:create",
            },
        ],
        [
            {
                "text": "📊 Voir dépenses du mois",
                "callback_data": "depense:list:month",
            },
        ],
        [
            {
                "text": "← Retour au menu",
                "callback_data": "menu:main",
            },
        ],
    ]
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


def build_receptions_submenu() -> Dict[str, Any]:
    texte = "📅 *Réunions & Réceptions*\n\nChoisis une option :"
    lignes = [
        [
            {
                "text": "📋 Prochaines réunions",
                "callback_data": "rec:list:upcoming",
            },
        ],
        [
            {
                "text": "📝 Noter un point à régler",
                "callback_data": "rec:add_point",
            },
        ],
        [
            {
                "text": "← Retour au menu",
                "callback_data": "menu:main",
            },
        ],
    ]
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


def build_chantier_list(chantiers: List[Dict[str, Any]]) -> Dict[str, Any]:
    texte = "🏗️ *Choisis un chantier*\n\nSélectionne le chantier sur lequel tu travailles :"
    lignes = []
    for c in chantiers:
        lignes.append(
            [
                {
                    "text": f"🏗️ {c.get('nom', c.get('ref', 'Chantier'))}",
                    "callback_data": f"chantier:select:{c['id']}",
                }
            ]
        )
    lignes.append(
        [
            {
                "text": "← Retour au menu",
                "callback_data": "menu:main",
            }
        ]
    )
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


def build_simple_message(texte: str, bouton_retour: bool = True) -> Dict[str, Any]:
    lignes = []
    if bouton_retour:
        lignes.append(
            [
                {
                    "text": "← Retour au menu",
                    "callback_data": "menu:main",
                }
            ]
        )
    return {"text": texte, "keyboard": {"inline_keyboard": lignes}}


# Mapping des callbacks → handlers (utilisé comme lookup table dans le dispatcher)
# Chaque handler reçoit les kwargs: chat_id, bot_config, supabase, org_id, chantier_id, ...
CALLBACK_ROUTES: Dict[str, str] = {
    # Navigation
    "menu:main": "handle_menu_main",
    "menu:sub:operations": "handle_sub_operations",
    "menu:sub:pointages": "handle_sub_pointages",
    "menu:sub:taches": "handle_sub_taches",
    "menu:sub:finances": "handle_sub_finances",
    "menu:sub:receptions": "handle_sub_receptions",
    "menu:help": "handle_menu_help",
    # Chantier
    "chantier:list": "handle_chantier_list",
    "chantier:select:": "handle_chantier_select",
    # Opérations
    "op:create:": "handle_create_operation",
    "op:list:pending": "handle_list_pending_operations",
    # Pointages
    "pointage:list:recent": "handle_pointage_list_recent",
    # Tâches
    "tache:list:": "handle_tache_list",
    "tache:ask_done": "handle_tache_ask_done",
    # Dépenses
    "depense:create": "handle_depense_create",
    "depense:list:month": "handle_depense_list_month",
    # Réceptions
    "rec:list:upcoming": "handle_rec_list_upcoming",
    "rec:add_point": "handle_rec_add_point",
    # Statistiques
    "stats:show": "handle_stats_show",
    # Factures (inchangé via service:invoice_upload, mais aussi depuis bot_construction.py)
    "service:invoice_upload": "handle_invoice_upload_menu",
}
