import os
import pytest
from app.services.agents.menu_manager import MenuManager, MenuContext

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


def test_no_chantier_shows_select_menu():
    """Sans chantier sélectionné, le menu propose de sélectionner un chantier."""
    ctx = MenuContext(chantier_id=None, user_role="conducteur")
    menu = MenuManager.get_dynamic_menu(ctx)

    assert len(menu) > 0
    assert any("Sélectionner" in b["text"] or "chantier" in b["text"].lower() for b in menu)


def test_conducteur_sees_field_menu():
    """Un conducteur sur un chantier voit les actions terrain."""
    ctx = MenuContext(chantier_id="CH-001", user_role="conducteur")
    menu = MenuManager.get_dynamic_menu(ctx)

    texts = [b["text"] for b in menu]
    assert "👷 Pointer" in texts
    assert "📸 Photo facture" in texts
    assert "📈 Avancement" in texts


def test_gerant_sees_management_menu():
    """Un gérant voit des actions de gestion en plus."""
    ctx = MenuContext(chantier_id="CH-001", user_role="gerant")
    menu = MenuManager.get_dynamic_menu(ctx)

    texts = [b["text"] for b in menu]
    assert "💰 Dépenses" in texts
    assert "✅ Valider" in texts or "📋 Tâches" in texts


def test_menu_returns_inline_keyboard():
    """Le menu retourne un clavier inline Telegram valide."""
    ctx = MenuContext(chantier_id="CH-001", user_role="conducteur")
    keyboard = MenuManager.get_inline_keyboard(ctx)

    assert "inline_keyboard" in keyboard
    assert len(keyboard["inline_keyboard"]) > 0
    for row in keyboard["inline_keyboard"]:
        for btn in row:
            assert "text" in btn
            assert "callback_data" in btn
