
import operator
import time
import uuid as _uuid
import json
import copy
import os
import logging
from datetime import date as _today_date
from typing import Annotated, Sequence, TypedDict, Union, Optional, Dict, Any, List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings as _settings
from app.core import vertex as vertex_service
from app.services import llm_provider

from app.api.auth import get_supabase
from app.services.agents.audio_service import AudioExpertService
from app.services.agents.vision_service import VisionExpertService
from app.services.agents.actions import ActionRegistry, ActionType, format_response
from app.services.agents.form_engine import PendingForm
from app.services.agents.tools import (
    get_user_chantiers, 
    get_chantier_details, 
    create_operation,
    manage_attendance,
    report_progress,
    manage_tasks,
    search_chantiers,
)
from app.agents.tools.depense_tools import create_depense
from app.agents.tools.attendance_tools import match_resources, upsert_attendance

logger = logging.getLogger(__name__)

# --- STATE DEFINITION ---

class AgentState(TypedDict):
    # L'historique des messages
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # Contexte métier
    org_id: str
    chantier_id: Optional[str]
    user_name: str
    # Corrélation pour les logs
    correlation_id: str
    # Mémoire long terme
    summary: str
    # États de contrôle
    last_action_status: str # idle, busy, pending_confirm, confirmed, cancelled
    is_urgent: bool
    # --- Champs Multimodaux ---
    voice_bytes: Optional[bytes]
    image_bytes: Optional[bytes]
    audio_meta: Dict[str, Any]
    vision_meta: Dict[str, Any]
    # --- HITL ---
    pending_tool_call: Optional[Dict[str, Any]]
    hitl_choice: Optional[str]
    # --- Interface structurée ---
    pending_form: Optional[Dict[str, Any]]  # État du formulaire en cours (sérialisé)
    # --- Buffer de contexte (Phase 2.6) ---
    buffer_data: Optional[Dict[str, Any]]  # Données en attente de chantier

# --- NODES ---

def log_transition(state: AgentState, node_name: str):
    """Log la transition du nœud dans logs_agents."""
    try:
        corr_id = state.get("correlation_id")
        try:
            _uuid.UUID(corr_id)
        except:
            corr_id = str(_uuid.uuid4())
        
        # Ne pas insérer entity_id si ce n'est pas un UUID valide
        entity_id = state.get("chantier_id")
        if entity_id:
            try:
                _uuid.UUID(str(entity_id))
            except (ValueError, AttributeError):
                entity_id = None
        
        get_supabase().table("logs_agents").insert({
            "org_id": state.get("org_id", ""),
            "correlation_id": corr_id,
            "agent_type": "custom",
            "model": "gemini-2.5-flash",
            "user_prompt": str(state["messages"][-1].content) if state.get("messages") else "System action",
            "status": "completed",
            "entity_table": "agents_nodes",
            "entity_id": entity_id
        }).execute()
    except Exception as e:
        print(f"Erreur logging transition {node_name}: {e}")

def classify_input_node(state: AgentState):
    """Analyse l'entrée et prépare le routage."""
    log_transition(state, "classifier")
    return state

async def audio_expert_node(state: AgentState):
    """Transcription et normalisation audio."""
    log_transition(state, "audio_expert")
    if not state.get("voice_bytes"):
        return state
    
    audio_service = AudioExpertService()
    start_time = time.time()
    try:
        transcript = await audio_service.transcribe(state["voice_bytes"])
        chantiers = get_user_chantiers.invoke({"org_id": state["org_id"]})["data"]
        norm_result = await audio_service.normalize_text(transcript, chantiers)
        
        return {
            "messages": [HumanMessage(content=norm_result["text"])],
            "is_urgent": norm_result["is_urgent"],
            "voice_bytes": None,
            "audio_meta": {"latency_ms": (time.time() - start_time) * 1000, "transcript": transcript}
        }
    except Exception as e:
        return {"messages": [HumanMessage(content="[Erreur Audio] Échec traitement.")], "voice_bytes": None}

async def vision_expert_node(state: AgentState):
    """OCR et classification d'images / documents PDF."""
    log_transition(state, "vision_expert")
    if not state.get("image_bytes"):
        return state

    import tempfile, os

    vision_service = VisionExpertService()
    start_time = time.time()
    try:
        chantiers = get_user_chantiers.invoke({"org_id": state["org_id"]})["data"]
        image_bytes = state["image_bytes"]

        # Détection PDF : si le fichier commence par %PDF, on utilise l'extracteur générique
        is_pdf = image_bytes[:4] == b"%PDF"
        if is_pdf:
            from app.agents.generic_extractor import create_invoice_extractor
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            try:
                extractor = create_invoice_extractor()
                result = await extractor.extract(tmp_path)
                import json as _json
                extracted_data = result.raw_data.get("extracted_data", {})
                msg = (
                    "[SYSTEM-DATA-EXTRACTION]\n"
                    "STATUS: SUCCESS\n"
                    "SOURCE: VISION-OCR\n"
                    f"RAW_JSON_DATA: {_json.dumps(extracted_data, ensure_ascii=False)}\n"
                    "INSTRUCTION: Analyse ce JSON, présente les informations importantes "
                    "à l'utilisateur (fournisseur, montants, numéros, etc.) "
                    "et propose de valider."
                )
            finally:
                os.unlink(tmp_path)
        else:
            result = await vision_service.process_photo(image_bytes, chantiers)
            if not result.is_document:
                msg = f"👷 Photo de chantier : {result.description}"
            elif result.besoin_clarification or not result.montant_ttc:
                msg = f"🧐 J'ai vu un ticket chez {result.fournisseur or 'un fournisseur'}, mais le montant est illisible. Tu peux me le donner ?"
            else:
                msg = f"💰 Ticket détecté : {result.fournisseur} pour {result.montant_ttc}€ TTC le {result.date}."

        return {
            "messages": [AIMessage(content=msg)],
            "image_bytes": None,
            "vision_meta": {"latency_ms": (time.time() - start_time) * 1000, "data": {} if is_pdf else result.model_dump()}
        }
    except Exception as e:
        return {"messages": [AIMessage(content=f"[Erreur Vision] Échec analyse: {e}")], "image_bytes": None}

def call_model_node(state: AgentState):
    """Cerveau principal."""
    log_transition(state, "agent")
    
    # 1. Résumé et mémoire
    summary_context = f"\nRésumé précédent : {state.get('summary')}" if state.get("summary") else ""
    urgency = "\n🚨 PRIORITÉ HAUTE" if state.get("is_urgent") else ""
    
    # Garde-fou : si la liste des messages est vide, on initialise un message par défaut
    if not state.get("messages"):
        return {
            "messages": [AIMessage(content="Je suis prêt à analyser votre document.")],
            "buffer_data": state.get("buffer_data"),
        }

    buffer_context = ""
    buf = state.get("buffer_data")
    if buf:
        summary = buf.get("summary", "") if isinstance(buf, dict) else ""
        if summary:
            buffer_context = (
    f"\n📋 ACTION EN COURS : {summary}.\n"
    "LIMITE DE DOMAINE : Tu es un assistant spécialisé dans la gestion de chantier. "
    "Si un message utilisateur est hors de ton domaine (questions générales, météo, etc.) "
    "ou ne permet pas de faire progresser l'action en cours : "
    "décline poliment en rappelant ton rôle, puis recentre immédiatement "
    "sur l'action ou la donnée en attente."
)
        else:
            buffer_context = f"\n📋 CONTEXTE EN ATTENTE : Tu avais commencé à traiter une opération avant de demander le chantier. Infos collectées : {buf}. Complète maintenant l'action."
    print(f"[STATE_CHECK] call_model_node | buffer_data keys: {list(buf.keys()) if buf else 'EMPTY'} | chantier_id={state.get('chantier_id', 'None')}")
    
    system_prompt = (
        f"Tu es l'assistant de chantier Suren, ton de 'collègue de terrain' (direct, pro, emojis 👷🏗️). "
        f"Contexte : {state.get('user_name', 'Chef')}, Org: {state.get('org_id', 'Non défini')}, Chantier: {state.get('chantier_id') or 'Non défini'}. "
        f"{summary_context}{urgency}"
        f"{buffer_context}\n\n"
        "RÈGLE DE RÉSONANCE : Ton message texte (content) doit être le miroir "
        "de tes actions techniques. Si tu extrais, valides ou manipules des données "
        "(montants, noms, dates, chantiers, etc.), tu DOIS les citer explicitement "
        "dans ton texte. L'utilisateur ne voit pas tes appels d'outils, "
        "il ne voit que tes mots.\n\n"
        f"Aujourd'hui c'est le {_today_date.today().isoformat()}. Si une date correspond "
        f"à aujourd'hui dans ta réponse, appelle-la 'aujourd'hui'.\n\n"
        "TRAITEMENT DOCUMENT : Après l'extraction d'un document, "
        "présente toujours les données trouvées (montant, fournisseur, etc.) "
        "et propose les options Valider/Modifier/Annuler via format_response, "
        "même si des champs sont vides ou à compléter.\n\n"
        "--- PROTOCOLE DE DÉCISION ---\n"
        "1. IDENTIFICATION : Si le chantier n'est pas identifié, "
        "appelle search_chantiers avant toute action d'écriture.\n"
        "3. SÉQUENÇAGE : Ne crée rien (create_depense) sans avoir "
        "la certitude du chantier (ID ou sélection unique).\n"
        "4. FALLBACK : Si une catégorie n'est pas claire, "
        "utilise 'autre' (catégories acceptées : sous_traitant, fournisseur, autre).\n"
        "---\n"
        "PROTOCOLE DE COMMUNICATION : Tout appel d'outil doit obligatoirement "
        "inclure l'argument context_summary. Ce champ doit contenir une phrase "
        "récapitulant les données extraites (montant, fournisseur, objet) "
        "pour informer l'utilisateur de ce que tu as compris.\n"
        "---\n"
        "RÈGLES TECHNIQUES :\n"
        "1. Toute action d'écriture (créer, modifier) doit passer par un Tool.\n"
        '5. IMPORTANT : Tu DOIS utiliser l\'outil **format_response** '
        'pour structurer tes interactions : '
        'DISPLAY_MENU pour les choix, INIT_FORM pour les saisies, '
        'CONFIRM_ACTION pour les validations. '
        'Si aucune action spéciale n\'est requise, réponds normalement en texte.\n'
        '6. OBLIGATOIRE : Tu DOIS appeler format_response avec DISPLAY_MENU '
        'dès que tu as une liste de chantiers. '
        'Interdiction formelle de répondre en texte seul dans ce cas.\n'
        '7. DÉTERMINISME : Dès qu\'une action métier (dépense, pointage, rapport) '
        'est demandée avec un chantier identifiable (ex: "CH-016", "CRF"), '
        'interdiction de poser une question de clarification. '
        'Tu DOIS immédiatement proposer la confirmation '
        'via format_response avec CONFIRM_ACTION.\n'
        'EXEMPLE : Message "Aujourd\'hui j\'ai dépensé 150€ pour le béton '
        'sur CH-016" → format_response(CONFIRM_ACTION, '
        '"Confirmer la dépense : 150€ béton sur CH-016 ?")\n'
        'Le chantier est déjà nommé → ne demande PAS "Sur quel chantier ?".\n'
        '8. ACCUEIL DOCUMENT : Si l\'utilisateur mentionne vouloir enregistrer '
        'une facture, un reçu ou un document sans l\'avoir encore envoyé, '
        'tu DOIS l\'encourager et lui demander explicitement d\'envoyer '
        'le fichier (PDF ou Image).\n'
        '9. PROTOCOLE SYSTEM-DATA : '
        'Tout message commençant par [SYSTEM-DATA-EXTRACTION] '
        'est une transmission directe de l\'outil d\'OCR. '
        'Le champ RAW_JSON_DATA contient toutes les données extraites. '
        'Analyse ce JSON et présente les informations importantes à l\'utilisateur '
        '(fournisseur, montants, numéros, etc.) et propose de valider. '
        'Ne discute pas la validité du statut SUCCESS.\n'
    )
    
    msgs = [SystemMessage(content=system_prompt)]
    for m in list(state["messages"][-10:]):
        msgs.append(copy.deepcopy(m))

    if buf:
        summary = buf.get("summary", "") if isinstance(buf, dict) else ""
        if summary and msgs and isinstance(msgs[-1], HumanMessage) and msgs[-1].content:
            original = str(msgs[-1].content)
            msgs[-1].content = (
                f"📝 CONTEXTE MÉTIER : {summary}\n"
                f"MESSAGE UTILISATEUR : {original}\n"
                f"⚠️ INSTRUCTION : Tu DOIS répondre au MESSAGE UTILISATEUR. "
                f"S'il est hors-sujet (météo, question générale), décline poliment "
                f"et recentre sur le CONTEXTE MÉTIER ci-dessus."
            )
    
    tools = [get_user_chantiers, get_chantier_details, create_depense, create_operation, manage_attendance, report_progress, manage_tasks, format_response, match_resources, upsert_attendance, search_chantiers]
    
    force_tool = any(
        kw in str(state["messages"][-1].content).lower()
        for kw in ["chantier", "recherche", "trouve"]
    )
    
    response = llm_provider.invoke(
        messages=msgs,
        tools=tools,
        force_tool=force_tool,
    )
    
    # Injection early-stage de context_summary dans les tool_calls
    # Garantit que le tool_result_formatter pourra afficher les données
    # utilisateur, quel que soit le chemin dans le graphe (whitelist ou HITL)
    if response.tool_calls:
        last_user_content = ""
        if state.get("messages"):
            last_msg = state["messages"][-1]
            last_user_content = str(last_msg.content) if last_msg.content else ""
        for tc in response.tool_calls:
            args = tc.get("args", {})
            if "context_summary" not in args or not args.get("context_summary"):
                truncated = last_user_content[:120]
                if len(last_user_content) > 120:
                    truncated += "..."
                args["context_summary"] = truncated
    
    # Sonde sortante (silencieuse sauf si DEBUG_LLM est défini)
    if os.environ.get("DEBUG_LLM"):
        content_preview = str(response.content)[:200] if response.content else "(no content)"
        tool_names = [tc.get("name", "?") for tc in (response.tool_calls or [])]
        print(f"[LLM_RESPONSE] content={content_preview} | tools={tool_names}")

    return {"messages": [response]}

def pre_reflector_node(state: AgentState):
    """Vérifie la cohérence avant d'autoriser l'HITL. Injecte automatiquement l'org_id si manquant."""
    log_transition(state, "pre_reflector")
    last_msg = state["messages"][-1]
    
    if not last_msg.tool_calls:
        return state
        
    call = last_msg.tool_calls[0]
    args = call["args"]
    
    # Injection FORCÉE de l'org_id dans le message du LLM
    org_id = state.get("org_id", "")
    if org_id and ("org_id" not in args or not args.get("org_id")):
        args["org_id"] = org_id
    
    # Injection FORCÉE du chantier_id si présent dans le state mais pas dans les args
    chantier_id = state.get("chantier_id")
    if chantier_id and "chantier_id" in args and not args.get("chantier_id"):
        args["chantier_id"] = chantier_id
    
    # Normalisation des dates relatives (ex: "aujourd'hui" → "2026-05-01")
    from datetime import date as _date
    for key in list(args.keys()):
        if "date" in key.lower() and isinstance(args.get(key), str):
            val = args[key].lower().strip()
            if val in ("aujourd'hui", "maintenant", "today", "ce_matin", "hier"):
                args[key] = _date.today().isoformat()
    
    # Garde-fou : Chantier ID obligatoire pour les outils métier
    if "chantier_id" in args and not args.get("chantier_id") and not chantier_id:
        return {"messages": [AIMessage(content="👷 Pour quel chantier tu veux faire ça ? Je n'ai pas le nom ou la référence.")]}
    
    # Injection du context_summary si absent (garantit que le
    # tool_result_formatter peut afficher les données utilisateur,
    # même si le LLM ne remplit pas ce champ)
    if "context_summary" not in args or not args.get("context_summary"):
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage) and msg.content:
                args["context_summary"] = str(msg.content)[:120]
                break
        if not args.get("context_summary"):
            args["context_summary"] = "Action utilisateur"
    
    # Mise à jour des arguments dans le tool_call
    call["args"] = args
    # On recrée un AIMessage avec les tool_calls modifiés pour que le ToolNode les lise
    from langchain_core.messages import AIMessage as _AIMessage
    updated_msg = _AIMessage(content=last_msg.content, tool_calls=[call])
    return {"messages": [updated_msg], "pending_tool_call": call}

def hitl_formatter_node(state: AgentState):
    """Marque l'état pour interruption HITL et parse les actions structurées."""
    log_transition(state, "output_formatter")
    last_msg = state["messages"][-1]
    
    parsed = ActionRegistry.parse_response(last_msg)
    
    updates = {"last_action_status": "idle", "pending_form": None, "pending_tool_call": None, "buffer_data": None}
    
    # Vérifier si le tool_call est format_response ou en lecture seule
    # (ne pas bloquer en HITL pour ces outils)
    is_format_response = False
    is_read_only = False
    if last_msg.tool_calls:
        is_format_response = any(tc.get("name") == "format_response" for tc in last_msg.tool_calls)
        READ_ONLY_TOOLS = {"search_chantiers", "get_user_chantiers", "get_chantier_details", "match_resources"}
        is_read_only = any(tc.get("name") in READ_ONLY_TOOLS for tc in last_msg.tool_calls)
    
    # Cas 1 : Outil métier appelé → interruption HITL (sauf format_response et lecture seule)
    if last_msg.tool_calls and not is_format_response and not is_read_only:
        buf = state.get("buffer_data")
        buf_summary = ""
        if buf:
            buf_summary = buf.get("summary", "") if isinstance(buf, dict) else ""

        msg_text = str(last_msg.content) if last_msg.content else ""
        if buf_summary:
            msg_text = f"📝 {buf_summary}\n\n{msg_text}"

        updates["last_action_status"] = "pending_confirm"
        updates["buffer_data"] = state.get("buffer_data")
        updates["pending_tool_call"] = state.get("pending_tool_call", last_msg.tool_calls[0])
        updates["messages"] = [AIMessage(content=msg_text, tool_calls=last_msg.tool_calls or [])]
        return updates
    
    # Cas 2 : format_response (DISPLAY_MENU, INIT_FORM, CONFIRM_ACTION)
    if parsed.action == ActionType.INIT_FORM:
        from app.services.agents.form_engine import FormEngine
        form = FormEngine.create_from_payload(parsed.payload)
        updates["pending_form"] = form.model_dump()
        updates["last_action_status"] = "awaiting_form"
    elif parsed.action in (ActionType.DISPLAY_MENU, ActionType.CONFIRM_ACTION):
        updates["last_action_status"] = "idle"
    
    return updates


def tool_result_formatter_node(state: AgentState):
    """Transforme le résultat d'un tool métier en format_response pour boutons.
    Remplace le retour au LLM : on formate directement les données structurées."""
    log_transition(state, "tool_result_formatter")
    last_msg = state["messages"][-1]
    
    if not isinstance(last_msg, ToolMessage):
        return state
    
    # Log brut du contenu pour debug (silencieux sauf si DEBUG_LLM est défini)
    if os.environ.get("DEBUG_LLM"):
        print(f"[TOOL_RESULT_RAW] content={str(last_msg.content)[:500]}")
    
    import json
    try:
        res = json.loads(last_msg.content)
    except Exception as e:
        print(f"[TOOL_RESULT_PARSE_ERROR] {e} — raw={str(last_msg.content)[:200]}")
        return state
    
    # Si erreur, on laisse le message d'erreur tel quel
    if not res.get("success"):
        error_detail = res.get('error') or res.get('suggestion') or "erreur inconnue"
        return {"messages": [AIMessage(content=f"❌ {error_detail}")], "last_action_status": "idle"}
    
    data = res.get('data')
    
    # Liste de données (chantiers) → format_response DISPLAY_MENU
    # Smart Merge : récupérer context_summary depuis les arguments de
    # l'AIMessage qui a appelé l'outil (transmet les données extraites
    # par le LLM sans avoir à les redemander)
    ai_content = ""
    for msg in reversed(state.get("messages", [])[:-1]):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            args = msg.tool_calls[0].get("args", {})
            ai_content = args.get("context_summary", "")
            if not ai_content:
                ai_content = str(msg.content) if msg.content else ""
            break
    
    if not ai_content.strip():
        ai_content = "Bien reçu, je prépare ça."
    
    # Extraire le buffer_data potentiel depuis les messages récents
    buffer_info = {}
    for msg in reversed(state.get("messages", [])[-5:]):
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            content = msg.content.lower()
            import re
            montant_match = re.search(r'(\d+[\.,]?\d*)\s*€', content)
            if montant_match:
                buffer_info["montant_detected"] = montant_match.group(0)
                buffer_info["montant_raw"] = montant_match.group(1)
    buffer_info["summary"] = ai_content  # Persistance du contexte
    
    if data and isinstance(data, list) and len(data) > 0:
        try:
            options = [f"{d.get('ref', 'N/A')} - {d.get('nom', d.get('description', ''))}" for d in data]
        except Exception:
            options = [str(d)[:50] for d in data]
        
        # Ajouter bouton Annuler si une action est en cours
        if buffer_info.get("summary", "").strip():
            options.append("❌ Annuler / Reset")
        
        chantier_lines = "\n".join(f"- {opt}" for opt in options if not opt.startswith("❌"))
        full_text = f"{ai_content}\n\nChantiers trouvés :\n{chantier_lines}\n\nSur quel chantier ?"
        return {
            "messages": [AIMessage(
                content=json.dumps({
                    "action": "DISPLAY_MENU",
                    "text": full_text,
                    "payload": {"options": options}
                }),
            )],
            "buffer_data": buffer_info if buffer_info else None,
            "last_action_status": "idle"
        }
    
    # Fallback : pas de chantier trouvé mais on garde le contexte
    if ai_content.strip():
        return {
            "messages": [AIMessage(
                content=json.dumps({
                    "action": "DISPLAY_TEXT",
                    "text": f"Je n'ai pas trouvé de chantier.\n{ai_content}\nPeux-tu préciser le nom ?"
                }),
            )],
            "buffer_data": buffer_info if buffer_info else None,
            "last_action_status": "idle"
        }
    
    # Objet unique → message simple
    if data and isinstance(data, dict):
        nom = data.get('nom', data.get('ref', 'résultat'))
        buf_summary = ""
        if state.get("buffer_data"):
            buf_summary = state["buffer_data"].get("summary", "")
        msg_text = f"✅ {nom} chargé."
        if buf_summary:
            msg_text = f"📝 {buf_summary}\n\n{msg_text}"
        return {"messages": [AIMessage(content=msg_text)], "last_action_status": "idle", "buffer_data": state.get("buffer_data")}
    buf_summary = ""
    if state.get("buffer_data"):
        buf_summary = state["buffer_data"].get("summary", "")
    msg_text = f"✅ {msg}"
    if buf_summary:
        msg_text = f"📝 {buf_summary}\n\n{msg_text}"
    return {"messages": [AIMessage(content=msg_text)], "last_action_status": "idle", "buffer_data": state.get("buffer_data")}

def after_agent(state: AgentState):
    """Route après le LLM : format_response → END (déjà formaté pour l'interface),
    outils métier → pre_reflector (HITL), sinon END."""
    last = state["messages"][-1]
    print(f"[ROUTE] after_agent → {'pre_reflector' if last.tool_calls else 'END'}")
    if last.tool_calls:
        if any(tc.get("name") == "format_response" for tc in last.tool_calls):
            return END
        return "pre_reflector"
    return END


def route_input(state: AgentState):
    if state.get("voice_bytes"): return "audio_expert"
    if state.get("image_bytes"): return "vision_expert"
    return "agent"


def after_pre_reflector(state: AgentState):
    has_tools = bool(state["messages"][-1].tool_calls)
    print(f"[ROUTE] after_pre_reflector → {'formatter' if has_tools else 'END'}")
    if isinstance(state["messages"][-1], AIMessage) and not state["messages"][-1].tool_calls:
        return END
    return "formatter"

# --- GRAPH CONSTRUCTION ---

def create_agent_graph(checkpointer):
    workflow = StateGraph(AgentState)
    
    # Ajout des nœuds
    workflow.add_node("classifier", classify_input_node)
    workflow.add_node("audio_expert", audio_expert_node)
    workflow.add_node("vision_expert", vision_expert_node)
    workflow.add_node("agent", call_model_node)
    workflow.add_node("pre_reflector", pre_reflector_node)
    workflow.add_node("formatter", hitl_formatter_node)
    workflow.add_node("tools", ToolNode([get_user_chantiers, get_chantier_details, create_depense, create_operation, manage_attendance, report_progress, manage_tasks, format_response, match_resources, upsert_attendance, search_chantiers]))
    workflow.add_node("tool_result_formatter", tool_result_formatter_node)
    
    # --- Edges ---
    workflow.add_edge(START, "classifier")
    
    workflow.add_conditional_edges("classifier", route_input, {"audio_expert": "audio_expert", "vision_expert": "vision_expert", "agent": "agent"})
    workflow.add_edge("audio_expert", "agent")
    workflow.add_edge("vision_expert", "agent")
    
    workflow.add_conditional_edges("agent", after_agent, {"pre_reflector": "pre_reflector", END: END})
    
    workflow.add_conditional_edges("pre_reflector", after_pre_reflector, {"formatter": "formatter", END: END})
    
    # Formatter → Tools → Tool Result Formatter → END
    workflow.add_edge("formatter", "tools")
    workflow.add_edge("tools", "tool_result_formatter")
    workflow.add_edge("tool_result_formatter", END)
    
    return workflow.compile(checkpointer=checkpointer)
