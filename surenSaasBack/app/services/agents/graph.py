
import operator
import time
import uuid as _uuid
import json
from typing import Annotated, Sequence, TypedDict, Union, Optional, Dict, Any, List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings as _settings
from app.core import vertex as vertex_service

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
    """OCR et classification d'images."""
    log_transition(state, "vision_expert")
    if not state.get("image_bytes"):
        return state
        
    vision_service = VisionExpertService()
    start_time = time.time()
    try:
        chantiers = get_user_chantiers.invoke({"org_id": state["org_id"]})["data"]
        result = await vision_service.process_photo(state["image_bytes"], chantiers)
        
        if not result.is_document:
            msg = f"👷 Photo de chantier : {result.description}"
        elif result.besoin_clarification or not result.montant_ttc:
            msg = f"🧐 J'ai vu un ticket chez {result.fournisseur or 'un fournisseur'}, mais le montant est illisible. Tu peux me le donner ?"
        else:
            msg = f"💰 Ticket détecté : {result.fournisseur} pour {result.montant_ttc}€ TTC le {result.date}."
            
        return {
            "messages": [HumanMessage(content=msg)],
            "image_bytes": None,
            "vision_meta": {"latency_ms": (time.time() - start_time) * 1000, "data": result.model_dump()}
        }
    except Exception as e:
        return {"messages": [HumanMessage(content="[Erreur Vision] Échec analyse.")], "image_bytes": None}

def call_model_node(state: AgentState):
    """Cerveau principal - Gemini 2.0 Flash Lite."""
    log_transition(state, "agent")
    
    # 1. Résumé et mémoire
    summary_context = f"\nRésumé précédent : {state.get('summary')}" if state.get("summary") else ""
    urgency = "\n🚨 PRIORITÉ HAUTE" if state.get("is_urgent") else ""
    
    buffer_context = ""
    buf = state.get("buffer_data")
    if buf:
        buffer_context = f"\n📋 CONTEXTE EN ATTENTE : Tu avais commencé à traiter une opération avant de demander le chantier. Infos collectées : {buf}. Complète maintenant l'action."
    print(f"[BUFFER_STATE] buffer_data={json.dumps(buf if buf else {})} | chantier_id={state.get('chantier_id', 'None')}")
    
    system_prompt = (
        f"Tu es l'assistant de chantier Suren, ton de 'collègue de terrain' (direct, pro, emojis 👷🏗️). "
        f"Contexte : {state.get('user_name', 'Chef')}, Org: {state.get('org_id', 'Non défini')}, Chantier: {state.get('chantier_id') or 'Non défini'}. "
        f"{summary_context}{urgency}"
        f"{buffer_context}\n\n"
        "RÈGLES :\n"
        "1. Toute action d'écriture (créer, modifier) doit passer par un Tool.\n"
        "2. Ne fais PAS de phrases de courtoisie ('je vais chercher', 'note bien ça', 'laisse-moi vérifier'). "
        "Appelle l'outil immédiatement sans commentaire préalable.\n"
        '3. Si l\'utilisateur veut enregistrer une opération (dépense, pointage, avancement, tâche) '
        'et qu\'aucun chantier n\'est sélectionné : cherche avec **search_chantiers(query=...)** d\'abord. '
        'Si l\'utilisateur donne un nom (ex: \'CRF\', \'Bureaux Tech\'), appelle search_chantiers. '
        'Si rien trouvé, appelle **get_user_chantiers**. '
        'Ne demande jamais "sur quel chantier" en texte — utilise format_response DISPLAY_MENU.\n'
        '4. NE JAMAIS halluciner de données.\n'
        '5. IMPORTANT : Tu DOIS utiliser l\'outil **format_response** pour structurer tes interactions :\n'
        '   - Pour proposer des choix (menus, listes de chantiers) : action=DISPLAY_MENU, payload={"options": [...]}\n'
        '   - Pour démarrer une saisie (dépense, pointage) : action=INIT_FORM, payload={form_id, steps}\n'
        '   - Pour une validation critique (ex: confirmer une dépense) : action=CONFIRM_ACTION\n'
        '   - Si aucune action spéciale n\'est requise, réponds normalement en texte.\n'
        '6. IMPORTANT : Quand tu reçois des données d\'un outil (liste de chantiers, détails, etc.), '
        'tu DOIS utiliser format_response(action=DISPLAY_MENU, payload={"options": [liste]}) '
        'pour les afficher sous forme de boutons cliquables.\n'
        '7. OBLIGATION : Quand l\'utilisateur te donne une description d\'opération (ex: \'travaux préparatoires\'), '
        'tu DOIS appeler **create_operation** avec cette description. Ne réponds jamais \'je vais enregistrer\' '
        'sans appeler l\'outil. L\'outil fera la sauvegarde réelle.\n'
        '   - De même pour **create_depense**, **manage_attendance**, **report_progress**, **manage_tasks** : '
        'si l\'utilisateur décrit une action, appelle le tool correspondant immédiatement.'
        'EXEMPLE : Si l\'outil te retourne des chantiers, appelle format_response avec les refs : '
        "format_response(action='DISPLAY_MENU', payload={'options': ['CH-001 - Villa', 'CH-002 - Bureaux']})"
        '\n'
        '8. BUFFER_CONTEXT : Si tu vois ci-dessus "📋 CONTEXTE EN ATTENTE" dans le contexte, '
        "c'est que l'utilisateur avait donné des infos (montant, fournisseur, description...) "
        'avant de choisir le chantier. Tu DOIS compléter l\'action avec les données du buffer. '
        "Ex: si le buffer dit 'montant=120, fournisseur=Total' et que le chantier est maintenant connu, "
        'appelle create_depense avec toutes les infos.\n'
        '9. INTERDICTION de répondre "Fait", "👍", "OK" ou tout message de confirmation '
        "tant que search_chantiers ou get_user_chantiers n'a PAS ÉTÉ APPELÉ. "
        "Si un chantier est mentionné (nom, référence ou partie de nom comme 'CRF', 'CH-016'), "
        "tu DOIS appeler search_chantiers(query=...) avant toute autre action. "
        "L'outil search_chantiers accepte les noms partiels — appelle-le toujours. "
        "Ne réponds JAMAIS à l'utilisateur sans avoir appelé au moins un outil.\n"
        '10. GARDE-FOU : Si tu as un outil disponible et une intention claire, '
        'tu DOIS appeler cet outil. Une réponse texte sans outil est considérée '
        'comme une erreur. Ne réponds PAS en texte si un outil peut faire le travail.'
    )
    
    llm = vertex_service.get_chat_model()
    msgs = [SystemMessage(content=system_prompt)] + list(state["messages"][-10:])
    
    tools = [get_user_chantiers, get_chantier_details, create_depense, create_operation, manage_attendance, report_progress, manage_tasks, format_response, match_resources, upsert_attendance, search_chantiers]
    llm_with_tools = llm.bind_tools(tools)
    
    response = llm_with_tools.invoke(msgs)
    
    # Boucle de contrôle robuste : si l'appel initial n'a pas généré de tool_calls,
    # on ré-invoke avec une consigne renforcée
    retry_count = 0
    while not response.tool_calls and retry_count < 2:
        retry_count += 1
        retry_prompt = SystemMessage(
            content=f"ATTENTION (tentative {retry_count}) : Ta réponse précédente n'a pas utilisé d'outil. "
                    "Tu DOIS absolument appeler search_chantiers(query=...) maintenant. "
                    "C'est OBLIGATOIRE. Ne réponds pas en texte."
        )
        response = llm_with_tools.invoke(msgs + [retry_prompt])
    
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
    
    # Vérifier si le tool_call est format_response (ne pas bloquer en HITL)
    is_format_response = False
    if last_msg.tool_calls:
        is_format_response = any(tc.get("name") == "format_response" for tc in last_msg.tool_calls)
    
    # Cas 1 : Outil métier appelé → interruption HITL (sauf format_response)
    if last_msg.tool_calls and not is_format_response:
        updates["last_action_status"] = "pending_confirm"
        updates["buffer_data"] = state.get("buffer_data")  # On garde buffer_data pendant HITL
        # Priorité au pending_tool_call déjà injecté par pre_reflector (qui contient org_id)
        updates["pending_tool_call"] = state.get("pending_tool_call", last_msg.tool_calls[0])
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
    
    import json
    try:
        res = json.loads(last_msg.content)
    except Exception:
        return state
    
    # Si erreur, on laisse le message d'erreur tel quel
    if not res.get("success"):
        error_detail = res.get('error') or res.get('suggestion') or "erreur inconnue"
        return {"messages": [AIMessage(content=f"❌ {error_detail}")], "last_action_status": "idle"}
    
    data = res.get('data')
    
    # Liste de données (chantiers) → format_response DISPLAY_MENU
    if data and isinstance(data, list) and len(data) > 0:
        # Vérifier si le tool appelé est search_chantiers ou get_user_chantiers
        # Dans ce cas, on a besoin de buffer_data pour le contexte ultérieur
        # Chercher des infos de dépense/opération dans les derniers messages
        from datetime import date as _date
        today = _date.today().isoformat()
        
        # Extraire le buffer_data potentiel depuis les messages récents du LLM
        # Le LLM a déjà analysé l'intention avant d'appeler l'outil
        buffer_info = {}
        for msg in reversed(state.get("messages", [])[-5:]):
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                content = msg.content.lower()
                # Détection simple: montant, fournisseur, description dans le message
                import re
                montant_match = re.search(r'(\d+[\.,]?\d*)\s*€', content)
                if montant_match:
                    buffer_info["montant_detected"] = montant_match.group(0)
                    buffer_info["montant_raw"] = montant_match.group(1)
        
        try:
            options = [f"{d.get('ref', 'N/A')} - {d.get('nom', d.get('description', ''))}" for d in data]
        except Exception:
            options = [str(d)[:50] for d in data]
        tool_call_id = f"fmt_{int(time.time())}"
        return {
            "messages": [AIMessage(
                content=f"J'ai trouvé {len(data)} chantier(s) :",
                tool_calls=[{
                    "name": "format_response",
                    "args": {
                        "text": f"Choisis un chantier parmi les {len(data)} disponibles :",
                        "action": "DISPLAY_MENU",
                        "payload": {"options": options}
                    },
                    "id": tool_call_id,
                    "type": "tool_call"
                }]
            )],
            "buffer_data": buffer_info if buffer_info else None,  # Sauvegarde pour reprise
            "last_action_status": "idle"
        }
    
    # Objet unique → message simple
    if data and isinstance(data, dict):
        nom = data.get('nom', data.get('ref', 'résultat'))
        return {"messages": [AIMessage(content=f"✅ {nom} chargé.")], "last_action_status": "idle"}
    
    msg = res.get('message', 'Opération réussie.')
    return {"messages": [AIMessage(content=f"✅ {msg}")], "last_action_status": "idle"}


# --- EDGE ROUTERS (exportés pour les tests) ---

def after_agent(state: AgentState):
    """Route après le LLM : format_response → END (déjà formaté pour l'interface),
    outils métier → pre_reflector (HITL), sinon END."""
    last = state["messages"][-1]
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
    
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["tools"])
