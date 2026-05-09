"""
Module centralisé d'initialisation Vertex AI.

Startup : décode le secret Base64 → écrit /tmp/suren-vertex-key.json → vertexai.init()
Singleton : instance unique ChatGoogleGenerativeAI pour tout le graph
Shutdown : supprime le fichier JSON

Conçu pour le cycle de vie FastAPI (lifespan).
"""

import os
import json
import base64
import atexit
import logging
import time
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

CREDENTIALS_PATH = "/tmp/suren-vertex-key.json"

_llm_instance = None  # ChatGoogleGenerativeAI | None — lazy import
_initialized = False
_genai_client_instance = None
_genai_client_created_at = 0
GENAI_CLIENT_TTL = 3000  # 50 minutes — rafraîchit le token Google avant expiration


def _decode_credentials() -> dict | None:
    """Decode et retourne les credentials GCP depuis le settings."""
    raw = settings.gemini_api_key
    if not raw:
        logger.warning("gemini_api_key non défini dans les settings")
        return None

    if raw.startswith("AIza"):
        logger.info("gemini_api_key est une clé API AI Studio (pas de credentials GCP)")
        return None

    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Impossible de décoder gemini_api_key en credentials JSON: %s", e)
        return None


def _write_credentials_file(creds: dict) -> str:
    """Écrit les credentials JSON dans /tmp/suren-vertex-key.json."""
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(creds, f)
    os.chmod(CREDENTIALS_PATH, 0o600)
    logger.debug("Credentials écrits dans %s", CREDENTIALS_PATH)
    return CREDENTIALS_PATH


def _cleanup_credentials():
    """Supprime le fichier de credentials temporaire."""
    if os.path.exists(CREDENTIALS_PATH):
        try:
            os.remove(CREDENTIALS_PATH)
            logger.info("Fichier de credentials supprimé: %s", CREDENTIALS_PATH)
        except OSError as e:
            logger.warning("Impossible de supprimer %s: %s", CREDENTIALS_PATH, e)


def startup():
    global _initialized

    if _initialized:
        logger.debug("Vertex AI déjà initialisé, skip")
        return

    creds = _decode_credentials()
    if creds:
        _write_credentials_file(creds)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

    project_id = settings.gcp_project_id or (creds.get("project_id") if creds else None)
    location = settings.gemini_location or "europe-west1"

    _initialized = True
    logger.info(
        "Vertex AI startup OK — project=%s location=%s creds=%s",
        project_id, location, CREDENTIALS_PATH if creds else "none (API key mode)",
    )

    # Warm-up: effectuer un vrai appel LLM pour préchauffer la connexion gRPC
    logger.info("🔄 Warm-up Vertex AI LLM (cold start with real invoke)...")
    try:
        llm = get_chat_model()
        from langchain_core.messages import HumanMessage
        llm.invoke([HumanMessage(content="Hello")])
        logger.info("✅ Vertex AI LLM warm-up terminé (invoke OK)")
    except Exception as e:
        logger.warning("⚠️ Vertex AI LLM warm-up échoué: %s", e)


def get_chat_model():
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    if not _initialized:
        startup()

    from langchain_google_genai import ChatGoogleGenerativeAI

    project_id = settings.gcp_project_id
    if not project_id and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) as f:
                creds = json.load(f)
            project_id = creds.get("project_id")
        except Exception:
            pass

    _llm_instance = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        vertexai=True,
        project=project_id,
        location=settings.gemini_location or "europe-west1",
    )
    logger.debug("ChatGoogleGenerativeAI singleton créé")
    return _llm_instance


def get_genai_client():
    """Retourne un client google.genai.Client avec cache TTL.

    Le client est recréé toutes les ``GENAI_CLIENT_TTL`` secondes
    pour éviter les tokens expirés.
    """
    global _genai_client_instance, _genai_client_created_at

    if not _initialized:
        startup()

    now = time.time()
    if _genai_client_instance is None or (now - _genai_client_created_at) > GENAI_CLIENT_TTL:
        from google import genai as _genai

        project_id = settings.gcp_project_id
        if not project_id and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) as f:
                    creds = json.load(f)
                project_id = creds.get("project_id")
            except Exception:
                pass

        _genai_client_instance = _genai.Client(
            vertexai=True,
            project=project_id,
            location=settings.gemini_location or "europe-west1",
        )
        _genai_client_created_at = now
        logger.debug("Nouveau client genai créé (TTL=%ss)", GENAI_CLIENT_TTL)

    return _genai_client_instance


def invoke_gemini_native(
    messages: list,
    tools: list = None,
    force_tool: bool = False,
) -> "langchain_core.messages.AIMessage":
    """Remplace ChatGoogleGenerativeAI.invoke() par le SDK google-genai natif.

    Convertit l'historique LangChain en ``contents`` Google GenAI,
    appelle le modèle avec ``tool_config`` natif, et retourne un
    ``AIMessage`` LangChain parfaitement compatible avec LangGraph.

    Args:
        messages: Liste de BaseMessage (SystemMessage, HumanMessage, AIMessage...).
        tools: Liste optionnelle d'outils LangChain à binder.
        force_tool: Si True, utilise ``mode='ANY'`` (outil obligatoire).

    Returns:
        Un ``AIMessage`` standard LangChain, avec ``tool_calls`` si le
        modèle a choisi un outil.
    """
    from google.genai import types as _gtypes
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    client = get_genai_client()
    if not client:
        raise RuntimeError("Vertex AI pas initialisé — startup() non appelé")

    # ── 1. Convertir l'historique LangChain → contents Google ─────────
    system_instruction = None
    contents = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_instruction = msg.content
        elif isinstance(msg, HumanMessage):
            parts = [_gtypes.Part.from_text(text=str(msg.content))]
            contents.append(_gtypes.Content(role="user", parts=parts))
        elif isinstance(msg, AIMessage):
            parts = [_gtypes.Part.from_text(text=str(msg.content or ""))]
            contents.append(_gtypes.Content(role="model", parts=parts))
            # Gérer les tool_calls passés (multi-tour)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    fn_call = _gtypes.FunctionCall(
                        name=tc["name"],
                        args=tc["args"],
                    )
                    parts.append(_gtypes.Part(function_call=fn_call))
        elif isinstance(msg, ToolMessage):
            fn_response = _gtypes.FunctionResponse(
                name=msg.name or "unknown_tool",
                response={"result": msg.content},
            )
            parts = [_gtypes.Part(function_response=fn_response)]
            contents.append(_gtypes.Content(role="user", parts=parts))

    # ── 2. Configurer les outils ──────────────────────────────────────
    if tools:
        native_declarations = []
        for t in tools:
            try:
                decl_info = _convert_langchain_tool_to_native(t)
                fd = _gtypes.FunctionDeclaration(**decl_info)
                native_declarations.append(fd)
            except Exception as tool_err:
                logger.error("Erreur conversion outil %s: %s", t.name, tool_err, exc_info=True)

        if native_declarations:
            native_tool = _gtypes.Tool(function_declarations=native_declarations)
            tc = _gtypes.ToolConfig(
                function_calling_config=_gtypes.FunctionCallingConfig(
                    mode="ANY" if force_tool else "AUTO",
                )
            )
            gen_config = _gtypes.GenerateContentConfig(
                tools=[native_tool],
                tool_config=tc,
                temperature=0,
            )
        else:
            gen_config = _gtypes.GenerateContentConfig()
    else:
        gen_config = _gtypes.GenerateContentConfig()
    if system_instruction:
        gen_config.system_instruction = _gtypes.Content(
            parts=[_gtypes.Part.from_text(text=system_instruction)],
        )

    model_name = settings.gemini_model or "gemini-2.5-flash"

    # ── 3. Appeler le modèle ──────────────────────────────────────────
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=gen_config,
        )
    except Exception as api_err:
        logger.error("Erreur API Gemini native: %s", api_err, exc_info=True)
        # Fallback : retourner un AIMessage vide pour ne pas casser le graphe
        from langchain_core.messages import AIMessage as _AIMessage
        return _AIMessage(content=f"[Erreur IA: {api_err}]")

    # ── 4. Convertir la réponse native → AIMessage ────────────────────
    try:
        return _convert_native_response_to_aimessage(response)
    except Exception as conv_err:
        logger.error("Erreur conversion réponse native: %s", conv_err, exc_info=True)
        from langchain_core.messages import AIMessage as _AIMessage
        return _AIMessage(content=f"[Erreur conversion: {conv_err}]")



def _convert_langchain_tool_to_native(tool_def) -> dict:
    """Convertit un outil LangChain (BaseTool) en dict compatible
    ``FunctionDeclaration``.

    Nettoyage strict : ne garde que ``type`` (MAJUSCULES), ``description``
    et ``properties``. Supprime ``title``, ``default``, ``examples``, etc.
    que Pydantic ajoute et que Google Vertex rejette silencieusement.

    Note: ``get_input_schema()`` retourne une classe Pydantic (pas un dict),
    on appele ``.model_json_schema()`` pour obtenir le dict.
    """
    schema_pydantic = tool_def.get_input_schema()
    schema = schema_pydantic.model_json_schema()
    properties = {}
    required = list(schema.get("required", []))

    for prop_name, prop_info in schema.get("properties", {}).items():
        prop = {
            "type": prop_info.get("type", "string").upper(),
            "description": prop_info.get("description", ""),
        }
        properties[prop_name] = prop

    return {
        "name": tool_def.name,
        "description": tool_def.description or "",
        "parameters": {
            "type": "OBJECT",
            "properties": properties,
            "required": required,
        },
    }


def _convert_native_response_to_aimessage(response) -> "langchain_core.messages.AIMessage":
    """Convertit une réponse ``GenerateContentResponse`` native
    en ``AIMessage`` LangChain."""
    from langchain_core.messages import AIMessage

    candidate = response.candidates[0]
    if not candidate:
        return AIMessage(content="")

    parts = candidate.content.parts
    text_parts = []
    tool_calls = []

    for part in parts:
        if hasattr(part, "text") and part.text:
            text_parts.append(part.text)
        if hasattr(part, "function_call") and part.function_call:
            tc = {
                "name": part.function_call.name,
                "args": dict(part.function_call.args),
                "id": f"call_{part.function_call.name}",
                "type": "tool_call",
            }
            tool_calls.append(tc)

    return AIMessage(
        content="\n".join(text_parts),
        tool_calls=tool_calls if tool_calls else None,
    )


def shutdown():
    global _llm_instance, _initialized

    _llm_instance = None
    _initialized = False
    _cleanup_credentials()
    logger.info("Vertex AI shutdown OK")


# Enregistrement du cleanup pour les cas où le lifespan FastAPI ne s'exécute pas
atexit.register(_cleanup_credentials)
