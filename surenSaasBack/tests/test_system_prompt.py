"""Test que le system prompt de graph.py force l'utilisation du tool format_response."""

import pytest
import inspect
from app.services.agents.graph import call_model_node


def test_format_response_tool_is_available():
    """Vérifie que format_response est référencé dans les tools du graphe."""
    source = inspect.getsource(call_model_node)
    assert "format_response" in source, "format_response doit être dans les tools bindés au LLM"


def test_system_prompt_contains_format_response_instructions():
    """Vérifie que le system_prompt mentionne format_response, DISPLAY_MENU, INIT_FORM, CONFIRM_ACTION."""
    source = inspect.getsource(call_model_node)
    
    assert "format_response" in source, (
        "Le system prompt doit mentionner format_response pour que le LLM l'utilise"
    )
    assert "DISPLAY_MENU" in source, (
        "Le system prompt doit mentionner DISPLAY_MENU pour les menus"
    )
    assert "INIT_FORM" in source, (
        "Le system prompt doit mentionner INIT_FORM pour les formulaires"
    )
    assert "CONFIRM_ACTION" in source, (
        "Le system prompt doit mentionner CONFIRM_ACTION pour les validations"
    )


def test_rule_3_forces_get_user_chantiers():
    """Vérifie que la règle n°3 force l'appel à get_user_chantiers quand chantier manquant."""
    source = inspect.getsource(call_model_node)
    assert "get_user_chantiers" in source, (
        "La règle n°3 doit mentionner get_user_chantiers pour forcer l'appel"
    )
    assert "TU DOIS" in source, (
        "La règle n°3 doit être impérative (TU DOIS)"
    )

