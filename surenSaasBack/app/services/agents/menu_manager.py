"""Menu Manager : Gère les menus contextuels dynamiques selon le rôle et le chantier."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

CALLBACK_PREFIX = "act"


class MenuContext(BaseModel):
    """Contexte pour générer un menu dynamique."""
    chantier_id: Optional[str] = Field(None, description="ID du chantier sélectionné")
    user_role: str = Field("conducteur", description="Rôle de l'utilisateur (conducteur, gerant)")
    pending_form: bool = Field(False, description="Un formulaire est en cours")


class MenuManager:
    """Génère des menus contextuels dynamiques pour Telegram."""

    CONDUCTEUR_ACTIONS = [
        ("👷 Pointer", f"{CALLBACK_PREFIX}:pointer"),
        ("📸 Photo facture", f"{CALLBACK_PREFIX}:photo_facture"),
        ("📈 Avancement", f"{CALLBACK_PREFIX}:avancement"),
        ("⚠️ Signaler", f"{CALLBACK_PREFIX}:signaler"),
    ]

    GERANT_ACTIONS = [
        ("💰 Dépenses", f"{CALLBACK_PREFIX}:depenses"),
        ("📋 Tâches", f"{CALLBACK_PREFIX}:taches"),
        ("✅ Valider opérations", f"{CALLBACK_PREFIX}:valider_ops"),
        ("📊 Indicateurs", f"{CALLBACK_PREFIX}:indicateurs"),
    ]

    ROOT_MENU = [
        ("🏗️ Mes chantiers", f"{CALLBACK_PREFIX}:lister_chantiers"),
    ]

    @staticmethod
    def get_dynamic_menu(ctx: MenuContext) -> List[Dict[str, str]]:
        """Retourne la liste des boutons adaptée au contexte."""
        buttons = list(MenuManager.ROOT_MENU)

        if ctx.chantier_id:
            if ctx.user_role == "gerant":
                buttons.extend(MenuManager.GERANT_ACTIONS)
            buttons.extend(MenuManager.CONDUCTEUR_ACTIONS)

        if ctx.pending_form:
            buttons.append(("❌ Annuler saisie", f"{CALLBACK_PREFIX}:cancel_form"))

        return [{"text": text, "callback_data": cb} for text, cb in buttons]

    @staticmethod
    def get_inline_keyboard(ctx: MenuContext) -> Dict[str, Any]:
        """Retourne un clavier inline Telegram formaté."""
        menu = MenuManager.get_dynamic_menu(ctx)
        rows = []
        for item in menu:
            rows.append([item])
        return {"inline_keyboard": rows}
