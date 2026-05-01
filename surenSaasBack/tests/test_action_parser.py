import os
import json as _json
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from app.services.agents.actions import ActionRegistry, ActionType, FormatResponseSchema, format_response

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


@pytest.mark.asyncio
async def test_format_response_extracts_display_menu():
    """L'Output Parser extrait une action DISPLAY_MENU depuis un tool_call format_response."""
    tool_call = {
        "name": "format_response",
        "args": {
            "text": "Choisis une option :",
            "action": "DISPLAY_MENU",
            "payload": {
                "options": ["Matériaux", "Transport", "Main d'œuvre"],
                "context": {"chantier_id": "CH-001"}
            }
        },
        "id": "call_fmt_001",
        "type": "tool_call"
    }

    msg = AIMessage(content="Je prépare le menu...", tool_calls=[tool_call])

    parsed = ActionRegistry.parse_response(msg)

    assert parsed is not None
    assert parsed.action == ActionType.DISPLAY_MENU
    assert parsed.text == "Choisis une option :"
    assert parsed.payload["options"] == ["Matériaux", "Transport", "Main d'œuvre"]
    assert parsed.payload["context"]["chantier_id"] == "CH-001"


@pytest.mark.asyncio
async def test_parse_response_from_toolmessage():
    """parse_response extrait DISPLAY_MENU depuis un ToolMessage contenant le JSON de format_response."""
    tool_msg = ToolMessage(
        content=_json.dumps({
            "text": "Choisis un chantier :",
            "action": "DISPLAY_MENU",
            "payload": {"options": ["CH-001 - Villa", "CH-002 - Bureaux"]}
        }),
        tool_call_id="call_fmt_test"
    )

    parsed = ActionRegistry.parse_response(tool_msg)

    assert parsed is not None
    assert parsed.action == ActionType.DISPLAY_MENU, f"Attendu DISPLAY_MENU, reçu {parsed.action}"
    assert parsed.text == "Choisis un chantier :"
    assert "CH-001" in parsed.payload["options"][0]


@pytest.mark.asyncio
async def test_parse_response_from_message_stack():
    """parse_response trouve l'intention dans un AIMessage quand le dernier message est un ToolMessage."""
    aim = AIMessage(
        content="Voici les chantiers :",
        tool_calls=[{
            "name": "format_response",
            "args": {
                "text": "Choisis un chantier :",
                "action": "DISPLAY_MENU",
                "payload": {"options": ["CH-001 - Villa"]}
            },
            "id": "call_fmt",
            "type": "tool_call"
        }]
    )
    tool_result = ToolMessage(
        content=_json.dumps({"text": "ok", "action": "DISPLAY_MENU", "payload": {"options": ["CH-001 - Villa"]}}),
        tool_call_id="call_fmt"
    )

    # Pile de messages : dernier = ToolMessage, avant-dernier = AIMessage avec intention
    messages = [aim, tool_result]

    parsed = ActionRegistry.parse_response(messages)

    assert parsed is not None
    assert parsed.action == ActionType.DISPLAY_MENU
    assert "CH-001" in str(parsed.payload)


@pytest.mark.asyncio
async def test_format_response_extracts_init_form():
    """L'Output Parser extrait une action INIT_FORM pour lancer une saisie."""
    tool_call = {
        "name": "format_response",
        "args": {
            "text": "Saisis les infos de la dépense :",
            "action": "INIT_FORM",
            "payload": {
                "form_id": "depense",
                "steps": [
                    {"name": "fournisseur", "label": "Fournisseur", "type": "text"},
                    {"name": "montant", "label": "Montant (€)", "type": "number"},
                    {"name": "categorie", "label": "Catégorie", "type": "select", "options": ["fournisseur", "sous_traitant", "autre"]}
                ]
            }
        },
        "id": "call_fmt_002",
        "type": "tool_call"
    }

    msg = AIMessage(content="Je lance le formulaire...", tool_calls=[tool_call])

    parsed = ActionRegistry.parse_response(msg)

    assert parsed is not None
    assert parsed.action == ActionType.INIT_FORM
    assert parsed.payload["form_id"] == "depense"
    assert len(parsed.payload["steps"]) == 3
    assert parsed.payload["steps"][1]["name"] == "montant"


@pytest.mark.asyncio
async def test_format_response_fallback_to_display_text():
    """Si pas de tool_call, le parseur renvoie un DISPLAY_TEXT par défaut."""
    msg = AIMessage(content="Bonjour, je suis le bot Suren.")

    parsed = ActionRegistry.parse_response(msg)

    assert parsed is not None
    assert parsed.action == ActionType.DISPLAY_TEXT
    assert parsed.text == "Bonjour, je suis le bot Suren."
    assert parsed.payload == {}
