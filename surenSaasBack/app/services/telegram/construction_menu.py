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
                "text": "📄 Opérations",
                "callback_data": "op:list:pending",
            },
            {
                "text": "📋 Mes tâches",
                "callback_data": "menu:sub:taches",
            },
        ],
        [
            {
                "text": "📄 Situations/Factures",
                "callback_data": "menu:sub:situations",
            },
            {
                "text": "💵 Dépenses",
                "callback_data": "menu:sub:depenses",
            },
        ],
        [
            {
                "text": "📈 Avancement chantier",
                "callback_data": "avancement:list",
            },
            {
                "text": "📊 Indicateurs",
                "callback_data": "stats:show",
            },
        ],
        [
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


def build_pointages_date_menu() -> Dict[str, Any]:
    texte = "📅 *Sélectionne la date du pointage*"
    lignes = [
        [
            {"text": "📅 Aujourd'hui", "callback_data": "pointage:date:today"},
            {"text": "📅 J-1", "callback_data": "pointage:date:j-1"},
        ],
        [
            {"text": "📅 J-2", "callback_data": "pointage:date:j-2"},
        ],
        [
            {"text": "← Retour au menu", "callback_data": "menu:main"},
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
                "text": "📅 Changer de date",
                "callback_data": "pointage:date:select",
            },
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


def build_situations_submenu() -> Dict[str, Any]:
    texte = "📄 *Situations / Factures client*\n\nChoisis une option :"
    lignes = [
        [
            {
                "text": "📤 Envoyer une facture",
                "callback_data": "service:invoice_upload",
            },
        ],
        [
            {
                "text": "📊 Voir situations",
                "callback_data": "situation:list",
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


def build_depenses_submenu() -> Dict[str, Any]:
    texte = "💵 *Dépenses chantier*\n\nChoisis une option :"
    lignes = [
        [
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
    "menu:sub:situations": "handle_sub_situations",
    "menu:sub:depenses": "handle_sub_depenses",
    "menu:help": "handle_menu_help",
    # Chantier
    "chantier:list": "handle_chantier_list",
    "chantier:select:": "handle_chantier_select",
    # Opérations
    "op:create:": "handle_create_operation",
    "op:list:pending": "handle_list_pending_operations",
    # Pointages
    "pointage:date:select": "handle_pointage_date_select",
    "pointage:date:today": "handle_pointage_date_today",
    "pointage:date:j-1": "handle_pointage_date_j1",
    "pointage:date:j-2": "handle_pointage_date_j2",
    "pointage:list:human": "handle_pointage_list_human",
    "pointage:list:machine": "handle_pointage_list_machine",
    "pointage:list:recent": "handle_pointage_list_recent",
    # Tâches
    "tache:list:": "handle_tache_list",
    "tache:ask_done": "handle_tache_ask_done",
    # Dépenses
    "depense:create": "handle_depense_create",
    "depense:list:month": "handle_depense_list_month",
    # Statistiques
    "stats:show": "handle_stats_show",
    # Avancements
    "avancement:list": "handle_avancement_list",
    "avancement:situation:": "handle_avancement_situation",
    "avancement:final_save": "handle_avancement_final_save",
    # Factures
    "service:invoice_upload": "handle_invoice_upload_menu",
}
