"""Action Registry : Traduit les réponses du LLM en actions structurées pour Telegram."""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool


class ActionType(str, Enum):
    """Actions possibles pour l'interface Telegram."""
    DISPLAY_TEXT = "DISPLAY_TEXT"
    DISPLAY_MENU = "DISPLAY_MENU"
    INIT_FORM = "INIT_FORM"
    CONFIRM_ACTION = "CONFIRM_ACTION"


class FormatResponseSchema(BaseModel):
    """Schéma que le LLM doit remplir pour structurer sa réponse."""
    text: str = Field(description="Le message texte à afficher à l'utilisateur")
    action: ActionType = Field(description="L'action à exécuter")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Données additionnelles selon l'action (options, form_id, steps, etc.)"
    )


class ParsedResponse(BaseModel):
    """Réponse parsée prête à être envoyée à Telegram."""
    text: str
    action: ActionType = ActionType.DISPLAY_TEXT
    payload: Dict[str, Any] = Field(default_factory=dict)


@tool("format_response", args_schema=FormatResponseSchema)
def format_response(text: str, action: ActionType, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Structure la réponse du bot avec une action et des métadonnées pour l'interface Telegram.
    
    Args:
        text: Message texte à afficher
        action: Type d'action (DISPLAY_TEXT, DISPLAY_MENU, INIT_FORM, CONFIRM_ACTION)
        payload: Données additionnelles (options de menu, étapes de formulaire, etc.)
    """
    return {
        "text": text,
        "action": action.value if isinstance(action, ActionType) else action,
        "payload": payload
    }


class ActionRegistry:
    """Registre des actions : parse les réponses du LLM et les convertit en actions exécutables."""

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Extrait le texte d'un contenu AIMessage (str ou liste multimodale)."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(part.get("text", ""))
            return " ".join(texts)
        return str(content) if content else ""

    @staticmethod
    def parse_response(msg_or_messages) -> ParsedResponse:
        """Analyse un message ou une pile de messages pour extraire une action structurée.
        
        Accepte soit :
        - Un message unique (AIMessage ou ToolMessage)
        - Une liste de messages (pile) : regarde le dernier, puis l'avant-dernier si besoin
        """
        # Normaliser en liste de messages
        if isinstance(msg_or_messages, list):
            messages = msg_or_messages
        else:
            messages = [msg_or_messages]
        
        if not messages:
            return ParsedResponse(text="", action=ActionType.DISPLAY_TEXT, payload={})
        
        msg = messages[-1]
        
        # Cas 1 : ToolMessage avec contenu JSON (résultat de format_response)
        if isinstance(msg, ToolMessage):
            import json
            try:
                data = json.loads(msg.content)
                if isinstance(data, dict) and "action" in data:
                    return ParsedResponse(
                        text=data.get("text", ""),
                        action=ActionType(data.get("action", "DISPLAY_TEXT")),
                        payload=data.get("payload", {})
                    )
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Cas 2 : AIMessage avec tool_calls (format_response dans le message actuel)
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            text_content = ActionRegistry._extract_text(msg.content)
            for tc in msg.tool_calls:
                if tc.get("name") == "format_response":
                    args = tc.get("args", {})
                    return ParsedResponse(
                        text=args.get("text", text_content),
                        action=ActionType(args.get("action", "DISPLAY_TEXT")),
                        payload=args.get("payload", {})
                    )
        
        # Cas 3 : Chercher dans l'avant-dernier message (pile de messages)
        if len(messages) >= 2:
            prev_msg = messages[-2]
            if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
                for tc in prev_msg.tool_calls:
                    if tc.get("name") == "format_response":
                        args = tc.get("args", {})
                        return ParsedResponse(
                            text=args.get("text", ActionRegistry._extract_text(prev_msg.content)),
                            action=ActionType(args.get("action", "DISPLAY_TEXT")),
                            payload=args.get("payload", {})
                        )
        
        # Cas 3.5 : AIMessage avec contenu JSON structuré (résultat de tool_result_formatter)
        if isinstance(msg, AIMessage) and isinstance(getattr(msg, 'content', None), str):
            import json as _json
            try:
                data = _json.loads(msg.content)
                if isinstance(data, dict) and "action" in data:
                    return ParsedResponse(
                        text=data.get("text", ""),
                        action=ActionType(data.get("action", "DISPLAY_TEXT")),
                        payload=data.get("payload", {}),
                    )
            except (_json.JSONDecodeError, TypeError):
                pass

        # Cas 4 : Fallback vers texte simple
        text_content = ActionRegistry._extract_text(getattr(msg, 'content', '') or '')
        return ParsedResponse(
            text=text_content,
            action=ActionType.DISPLAY_TEXT,
            payload={}
        )

    @staticmethod
    def build_keyboard(options: List[str], callback_prefix: str = "act") -> Dict[str, Any]:
        """Construit un clavier inline Telegram à partir d'une liste d'options.
        Le callback_data est limité à 64 octets par Telegram.
        Pour les chantiers, on extrait la référence (ex: 'CH-016') comme callback_data court."""
        rows = []
        for opt in options:
            # Extraire la référence courte (ex: "CH-016" depuis "CH-016 - Bureaux...")
            ref = opt.split(" - ")[0] if " - " in opt else opt[:30]
            callback_data = f"{callback_prefix}:{ref}"
            rows.append([{"text": opt, "callback_data": callback_data}])
        return {"inline_keyboard": rows}
