"""
Sélectionne le provider LLM selon la configuration.

- ``"gemini"`` (défaut) : Vertex AI via ``app.core.vertex``
- ``"deepseek"`` : API DeepSeek directe (compatible OpenAI)

Utilisation ::
    from app.services import llm_provider
    response = llm_provider.invoke(messages, tools, force_tool=False)
"""

import json
import logging

from openai import OpenAI

from app.core.config import settings
from app.core import vertex as vertex_service

logger = logging.getLogger(__name__)


def invoke(messages, tools, force_tool: bool = False):
    """Appelle le LLM configuré (Gemini ou DeepSeek).

    Args:
        messages: Liste de ``BaseMessage`` LangChain.
        tools: Liste d'outils LangChain à binder.
        force_tool: Si True, force l'appel d'outil (``tool_choice``).

    Returns:
        Un ``AIMessage`` LangChain standard, avec ``tool_calls``
        si le modèle a choisi un outil.
    """
    if settings.is_deepseek():
        return _invoke_deepseek(messages, tools)
    return vertex_service.invoke_gemini_native(
        messages=messages,
        tools=tools,
        force_tool=force_tool,
    )


def _invoke_deepseek(messages, tools):
    """Appelle DeepSeek via l'API OpenAI-compatible.

    Conversion complète des types LangChain → OpenAI.
    """
    api_key = settings.deepseek_api_key
    if not api_key:
        raise RuntimeError(
            "deepseek_api_key non définie — impossible d'appeler DeepSeek"
        )

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # ── Conversion des messages LangChain → OpenAI ─────────────────────
    openai_msgs = []
    for msg in messages:
        role_map = {
            "SystemMessage": "system",
            "HumanMessage": "user",
            "AIMessage": "assistant",
        }
        role = role_map.get(type(msg).__name__, "user")
        content = str(msg.content) if msg.content else ""
        openai_msgs.append({"role": role, "content": content})

    # ── Conversion des outils ──────────────────────────────────────────
    # On retire org_id des schémas — le LLM ne doit pas gérer l'org_id
    # (il mettrait un placeholder). L'org_id sera injecté par
    # pre_reflector_node ou tool_node côté backend.
    OPENAI_ORG_ID_FIELDS = {"org_id", "organisation_id"}

    openai_tools = []
    for t in tools:
        raw_schema = t.get_input_schema().model_json_schema()
        clean_properties = {}
        for prop_name, prop_info in raw_schema.get("properties", {}).items():
            if prop_name in OPENAI_ORG_ID_FIELDS:
                continue
            ptype = prop_info.get("type", "string")
            if ptype in ("array", "object"):
                continue
            clean_properties[prop_name] = {
                "type": ptype,
                "description": prop_info.get("description", ""),
            }
        clean_params = {"type": "object", "properties": clean_properties}
        if raw_schema.get("required"):
            clean_params["required"] = [
                r for r in raw_schema["required"] if r not in OPENAI_ORG_ID_FIELDS
            ]

        openai_tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": clean_params,
            },
        })

    # ── Forcer l'outil search_chantiers si demandé ────────────────────
    tool_choice = {
        "type": "function",
        "function": {"name": "search_chantiers"},
    }

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=openai_msgs,
        tools=openai_tools,
        tool_choice=tool_choice,
        temperature=0,
    )

    choice = resp.choices[0]
    msg = choice.message

    tool_calls = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
                tool_calls.append({
                    "name": tc.function.name,
                    "args": args,
                    "id": tc.id,
                    "type": "tool_call",
                })
            except Exception as e:
                logger.error("Erreur parsing tool_call DeepSeek: %s — raw=%s", e, tc.function.arguments)

    from langchain_core.messages import AIMessage
    return AIMessage(content=msg.content or "", tool_calls=tool_calls if tool_calls else None)
