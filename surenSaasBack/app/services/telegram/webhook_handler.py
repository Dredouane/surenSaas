"""
Service: Webhook Handler

Gestion des webhooks entrants de Telegram.
Dispatche les requêtes vers les services appropriés.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
import logging


from app.services.agents.persistence import agent_persistence
from app.services.agents.graph import create_agent_graph
from app.services.agents.actions import ActionRegistry, ActionType, ParsedResponse
from app.services.agents.form_engine import PendingForm, FormEngine
from app.services.agents.menu_manager import MenuManager, MenuContext
from app.services.telegram.interface import TelegramInterface
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

class WebhookHandlerService:
    """Handler pour les webhooks Telegram entrants orchestrés par LangGraph."""
    
    def __init__(self, supabase_client, audit_service, bot_manager, upload_invoice_service):
        self.supabase = supabase_client
        self.audit = audit_service
        self.bot_manager = bot_manager
        self.upload_invoice = upload_invoice_service
        self.tg_interface = None # Initialisé par bot_id

    async def handle_update(self, bot_id: str, update: Dict[str, Any], bot_token: Optional[str] = None, org_id: Optional[str] = None) -> Dict[str, Any]:
        # Initialiser l'interface Telegram pour ce bot
        if bot_token is None:
            bot_token = await self._get_bot_token(bot_id)
        self.tg_interface = TelegramInterface(bot_token)
        self._org_id = org_id  # Stocké pour les méthodes enfants

        user_id = self._extract_user_id(update)
        import uuid as _uuid
        thread_id = str(user_id)  # Thread persistant par utilisateur pour garder le contexte
        correlation_id = str(_uuid.uuid4())

        # Audit initial (non bloquant si la table n'existe pas)
        try:
            await self.audit.create_log(
                bot_id=bot_id,
                telegram_user_id=user_id,
                interaction_type=self._determine_interaction_type(update),
                payload=update
            )
        except Exception as e:
            logger.warning(f"⚠️ Audit log non enregistré (table manquante ?): {e}")

        try:
            saver = await agent_persistence.get_saver()
            graph = create_agent_graph(saver)
            config = {"configurable": {"thread_id": thread_id}}

            # Vérifier si on est en callback (bouton cliqué)
            callback_query = update.get('callback_query')
            if callback_query:
                return await self._process_graph_callback(graph, config, callback_query, correlation_id)

            # Message texte normal
            if 'message' not in update:
                return {"status": "ignored"}

            message = update['message']
            return await self._process_graph_message(graph, config, message, correlation_id)

        except Exception as e:
            logger.error(f"Erreur Graphe: {e}", exc_info=True)
            await self.tg_interface.send_message(user_id, f"❌ Désolé, une erreur est survenue : {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def _get_bot_token(self, bot_id: str) -> str:
        # Récupérer depuis Supabase
        res = self.supabase.table("telegram_bots").select("token").eq("id", bot_id).single().execute()
        return res.data["token"] if res.data else ""

    async def _process_graph_message(self, graph, config, message, correlation_id):
        user_id = message['from']['id']
        text = message.get('text', '')
        
        voice_bytes = None
        if 'voice' in message:
            file_id = message['voice']['file_id']
            file_info = await self.tg_interface.get_file(file_id)
            if 'file_path' in file_info:
                voice_bytes = await self.tg_interface.download_file(file_info['file_path'])
        
        image_bytes = None
        if 'photo' in message:
            file_id = message['photo'][-1]['file_id']
            file_info = await self.tg_interface.get_file(file_id)
            if 'file_path' in file_info:
                image_bytes = await self.tg_interface.download_file(file_info['file_path'])

        # Context métier initial
        org_id = self._org_id or await self._get_user_org(user_id) or ""
        
        input_data = {
            "messages": [HumanMessage(content=text)] if text else [],
            "correlation_id": correlation_id,
            "user_name": message['from'].get('first_name', 'Utilisateur'),
            "org_id": org_id,
            "voice_bytes": voice_bytes,
            "image_bytes": image_bytes,
            "is_urgent": False,
            "audio_meta": {},
            "vision_meta": {},
            "summary": "",
                "last_action_status": "idle",
                "pending_tool_call": None,
                "hitl_choice": None,
                "pending_form": None
            }

        # Nettoyage automatique si l'historique est trop grand (évite la noyade du LLM)
        try:
            state_check = await graph.aget_state(config)
            if state_check.values and len(state_check.values.get("messages", [])) > 20:
                old_msgs = state_check.values["messages"]
                await graph.aupdate_state(config, {"messages": old_msgs[-10:]})
                logger.debug(f"🧹 Historique nettoyé : {len(old_msgs)} → 10 messages")
        except Exception:
            pass

        # Lancer le graphe et CAPTURER le dernier état
        final_state_values = None
        async for event in graph.astream(input_data, config, stream_mode="values"):
            final_state_values = event

        # Fallback sécurité
        if not final_state_values:
            final_state = await graph.aget_state(config)
            final_state_values = final_state.values

        all_messages = final_state_values.get("messages", [])
        if all_messages:
            last_msg = all_messages[-1]
            import logging as _logging
            logger.debug(f"🔍 Parsing: type={type(last_msg).__name__}, content={str(getattr(last_msg, 'content', ''))[:200]}")
            # Passer toute la pile de messages pour que parse_response puisse chercher dans l'historique
            parsed = ActionRegistry.parse_response(all_messages)
            reply_markup = None

            # Cas 1 : Action structurée du LLM (prioritaire)
            if parsed.action == ActionType.DISPLAY_MENU:
                # Si le payload contient des options, on les utilise pour construire les boutons
                options = parsed.payload.get("options")
                if options:
                    reply_markup = ActionRegistry.build_keyboard(options, callback_prefix="chantier")
                else:
                    # Menu contextuel générique
                    user_role = await self._get_user_role(user_id)
                    ctx = MenuContext(
                        chantier_id=final_state_values.get("chantier_id"),
                        user_role=user_role,
                        pending_form=final_state_values.get("pending_form") is not None
                    )
                    reply_markup = MenuManager.get_inline_keyboard(ctx)

            # Cas 2 : Formulaire en cours
            elif parsed.action == ActionType.INIT_FORM:
                form = FormEngine.create_from_payload(parsed.payload)
                prompt = form.get_current_prompt()
                step = form.current_step_info()
                if step and step.options:
                    reply_markup = ActionRegistry.build_keyboard(step.options, callback_prefix="form")

            # Cas 3 : Confirmation d'action
            elif parsed.action == ActionType.CONFIRM_ACTION:
                reply_markup = self.tg_interface.build_inline_keyboard([
                    {"text": "✅ Confirmer", "callback_data": "hitl:confirm"},
                    {"text": "❌ Annuler", "callback_data": "hitl:cancel"}
                ])

            # Cas 4 : HITL en attente (tool métier, pas format_response)
            elif final_state_values.get("last_action_status") == "pending_confirm":
                reply_markup = self.tg_interface.build_inline_keyboard([
                    {"text": "✅ C'est bon", "callback_data": "hitl:confirm"},
                    {"text": "❌ Annuler", "callback_data": "hitl:cancel"}
                ])

            # Fallback texte : priorité au texte parsé, puis au texte du payload, puis au contenu du message
            payload_text = parsed.payload.get("text", "") if parsed.payload else ""
            msg_text = ""
            if final_state_values.get("messages"):
                last_content = final_state_values["messages"][-1].content
                if isinstance(last_content, str):
                    msg_text = last_content
                elif isinstance(last_content, list):
                    msg_text = " ".join(p.get("text", "") for p in last_content if isinstance(p, dict))
                else:
                    msg_text = str(last_content)
            text_to_send = parsed.text or payload_text or msg_text or "👍 Fait."
            if not parsed.text and not payload_text and not msg_text:
                logger.debug(f"Fallback texte utilisé. parsed.text='{parsed.text}', payload_text='{payload_text}', last_msg_type={type(final_state_values['messages'][-1]).__name__}")
            logger.info(f"📤 Envoi à {user_id}: action={parsed.action}, text={text_to_send[:100]}...")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"📤 Full state: messages={len(final_state_values.get('messages', []))}, "
                             f"last_action_status={final_state_values.get('last_action_status')}, "
                             f"pending_form={final_state_values.get('pending_form') is not None}")
            await self.tg_interface.send_message(user_id, text_to_send, reply_markup=reply_markup)
        # Inclure le texte + boutons dans le return pour les tests E2E (mode sync)
        reply_text = text_to_send if all_messages else None
        reply_action = str(parsed.action) if all_messages and parsed else None
        reply_markup_json = json.dumps(reply_markup) if reply_markup else None
        return {
            "status": "ok",
            "reply_text": reply_text,
            "reply_action": reply_action,
            "reply_markup": reply_markup_json,
        }

    async def _process_graph_callback(self, graph, config, callback_query, correlation_id):
        user_id = callback_query['from']['id']
        callback_query_id = callback_query.get('id', '')
        data = callback_query.get('data', '')

        # Accuser réception du callback pour que le bouton arrête de "charger"
        if callback_query_id:
            await self._answer_callback(callback_query_id)

        # Routage des callbacks HITL
        if data.startswith("hitl:"):
            choice = data.split(":")[1]
            current_state = await graph.aget_state(config)
            has_state = bool(current_state.values and current_state.values.get("messages"))

            if choice == "confirm" and has_state:
                await graph.aupdate_state(config, {"hitl_choice": "confirm"})
                cb_state_values = None
                try:
                    async for event in graph.astream(None, config, stream_mode="values"):
                        cb_state_values = event
                        logger.debug(f"📌 CALLBACK STREAM: next={event.get('next', '?')}, "
                                     f"last_action_status={event.get('last_action_status')}, "
                                     f"messages={len(event.get('messages', []))}")
                except Exception as e:
                    logger.error(f"Erreur reprise graphe après callback: {e}")
                    await self.tg_interface.send_message(
                        user_id, "❌ Une erreur est survenue lors du traitement."
                    )
                    return {"status": "error", "error": str(e)}
            elif choice == "confirm" and not has_state:
                await self.tg_interface.send_message(user_id, "👷 Je n'ai pas d'action en cours à confirmer. Que veux-tu faire ?")
                return {"status": "ok"}
            else:
                await graph.aupdate_state(config, {"last_action_status": "cancelled"}, as_node="formatter")
                await self.tg_interface.send_message(user_id, "👷 Ok, j'ai annulé l'opération. Quoi d'autre ?")
                return {"status": "ok"}

            # Fallback si le stream n'a rien donné
            if not cb_state_values:
                try:
                    cb_state_values = (await graph.aget_state(config)).values
                except Exception as e:
                    logger.error(f"Erreur aget_state après callback: {e}")
                    cb_state_values = {}

            # Utiliser le même parseur que pour les messages standards (ActionRegistry)
            if cb_state_values.get("messages"):
                all_msgs = cb_state_values["messages"]
                parsed = ActionRegistry.parse_response(all_msgs)
                reply_markup = None

                if parsed.action == ActionType.DISPLAY_MENU:
                    options = parsed.payload.get("options")
                    if options:
                        reply_markup = ActionRegistry.build_keyboard(options, callback_prefix="chantier")
                elif parsed.action == ActionType.CONFIRM_ACTION:
                    reply_markup = self.tg_interface.build_inline_keyboard([
                        {"text": "✅ Confirmer", "callback_data": "hitl:confirm"},
                        {"text": "❌ Annuler", "callback_data": "hitl:cancel"}
                    ])

                text = parsed.text or str(all_msgs[-1].content) if all_msgs and all_msgs[-1].content else "👍 Fait."
                await self.tg_interface.send_message(user_id, text, reply_markup=reply_markup)
            return {"status": "ok"}

        # Routage annulation buffer (action:cancel_buffer)
        if data == "action:cancel_buffer":
            try:
                await graph.aupdate_state(config, {"buffer_data": None})
            except Exception:
                pass
            await self.tg_interface.send_message(
                user_id, "C'est oublié ! Que puis-je faire d'autre ?"
            )
            return {"status": "ok"}

        # Routage des callbacks de formulaire (act:... ou form:...)
        if data.startswith("act:") or data.startswith("form:"):
            await self._handle_struct_callback(graph, config, data, user_id, callback_query)
            return {"status": "ok"}

        # Routage sélection chantier (callback_data: chantier:<ref>)
        if data.startswith("chantier:"):
            chantier_ref = data.split(":", 1)[1]
            
            # Résoudre l'UUID réel du chantier depuis Supabase
            chantier_uuid = chantier_ref
            try:
                import uuid as _uuid
                _uuid.UUID(chantier_ref)
            except (ValueError, AttributeError):
                # Ce n'est pas un UUID, chercher la ref dans Supabase
                try:
                    res = self.supabase.table("chantiers") \
                        .select("id") \
                        .or_(f"ref.eq.{chantier_ref},nom.ilike.%{chantier_ref}%") \
                        .limit(1) \
                        .execute()
                    if res.data:
                        chantier_uuid = res.data[0]["id"]
                        logger.debug(f"UUID résolu pour {chantier_ref}: {chantier_uuid}")
                except Exception as e:
                    logger.warning(f"Impossible de résoudre l'UUID pour {chantier_ref}: {e}")
            
            # Récupérer le buffer_data existant (infos déjà collectées)
            current_state = await graph.aget_state(config)
            buf = (current_state.values or {}).get("buffer_data")
            
            # Construire le message de reprise avec ou sans buffer
            if buf:
                # Restaurer le contexte : on remet le buffer dans les messages
                reprise_msg = (
                    f"Le chantier {chantier_ref} est maintenant sélectionné. "
                    f"Reprends l'action en cours avec ces infos : {buf}. "
                    f"Termine l'opération."
                )
                await graph.aupdate_state(config, {
                    "chantier_id": chantier_uuid,
                    "buffer_data": None,  # Vider le buffer après utilisation
                    "messages": [
                        HumanMessage(content=f"Je sélectionne le chantier {chantier_ref} (UUID: {chantier_uuid})"),
                        AIMessage(content=reprise_msg)
                    ]
                })
            else:
                await graph.aupdate_state(config, {
                    "chantier_id": chantier_uuid,
                    "messages": [
                        HumanMessage(content=f"Je sélectionne le chantier {chantier_ref} (UUID: {chantier_uuid})"),
                        AIMessage(content=f"C'est noté chef ! On travaille maintenant sur le chantier : {chantier_ref} 🏗️")
                    ]
                })
            
            # Feedback utilisateur Telegram
            await self.tg_interface.send_message(
                user_id,
                f"✅ **Chantier {chantier_ref} sélectionné.**\n\nQue veux-tu faire ? (Dépense, rapport, pointage...)"
            )
            return {"status": "ok"}

        # Fallback : callback non reconnu, on le traite comme un message texte
        logger.warning(f"⚠️ Callback non géré: {data}, traitement comme message texte")
        from_user = callback_query.get('from', {})
        fake_message = {
            "from": {"id": user_id, "first_name": from_user.get('first_name', 'Utilisateur')},
            "text": data
        }
        await self._process_graph_message(graph, config, fake_message, correlation_id)
        return {"status": "ok"}

    async def _handle_struct_callback(self, graph, config, callback_data: str, user_id: int, callback_query: dict):
        """Gère un callback structuré (menu, formulaire, action)."""
        import uuid as _uuid
        parts = callback_data.split(":")
        prefix = parts[0]
        action = parts[1] if len(parts) > 1 else ""

        state = await graph.aget_state(config)

        # Si un formulaire est en cours
        pending_form_dict = state.values.get("pending_form")
        if pending_form_dict:
            form = PendingForm(**pending_form_dict)
            try:
                form.advance(form.current_step_name(), action)
                if form.is_complete():
                    # Formulaire terminé : on injecte les données dans le graphe
                    form_msg = f"✅ Formulaire {form.form_id} complété : {form.data}"
                    await graph.aupdate_state(config, {
                        "pending_form": None,
                        "messages": [HumanMessage(content=form_msg)]
                    })
                    # Relancer le graphe pour traiter les données
                    async for event in graph.astream(None, config, stream_mode="values"):
                        pass
                    final_state = await graph.aget_state(config)
                    if final_state.values.get("messages"):
                        await self.tg_interface.send_message(user_id, final_state.values["messages"][-1].content)
                else:
                    # Prochaine étape
                    prompt = form.get_current_prompt()
                    step = form.current_step_info()
                    reply_markup = None
                    if step and step.options:
                        reply_markup = ActionRegistry.build_keyboard(step.options, callback_prefix="form")
                    await graph.aupdate_state(config, {"pending_form": form.model_dump()})
                    await self.tg_interface.send_message(user_id, prompt, reply_markup=reply_markup)
            except ValueError as e:
                await self.tg_interface.send_message(user_id, str(e))
            return

        # Action de menu (pas de formulaire en cours)
        # On traite comme un message texte normal pour relancer le graphe proprement
        import uuid as _uuid
        from_user = callback_query.get('from', {})
        fake_message = {
            "from": {"id": user_id, "first_name": from_user.get('first_name', 'Utilisateur')},
            "text": action
        }
        await self._process_graph_message(graph, config, fake_message, str(_uuid.uuid4()))

    async def _get_user_role(self, telegram_user_id: int) -> str:
        """Récupère le rôle de l'utilisateur."""
        try:
            res = self.supabase.table("telegram_users").select("role").eq("telegram_id", str(telegram_user_id)).single().execute()
            return res.data.get("role", "conducteur") if res.data else "conducteur"
        except Exception:
            return "conducteur"

    async def _get_user_org(self, telegram_user_id: int) -> str:
        try:
            res = self.supabase.table("telegram_users").select("org_id").eq("telegram_id", str(telegram_user_id)).single().execute()
            if res.data and res.data.get("org_id"):
                return res.data["org_id"]
        except Exception:
            pass
        from app.core.config import settings
        return settings.org_id if settings.org_id else ""

    def _extract_user_id(self, update: Dict[str, Any]) -> Optional[int]:
        """Extrait l'ID utilisateur Telegram d'une update."""
        if 'message' in update:
            return update['message'].get('from', {}).get('id')
        elif 'callback_query' in update:
            return update['callback_query'].get('from', {}).get('id')
        return None

    async def _answer_callback(self, callback_query_id: str):
        """Répond à Telegram pour accuser réception du callback (arrête le spinner sur le bouton)."""
        try:
            import httpx
            url = f"{self.tg_interface.base_url}/answerCallbackQuery"
            async with httpx.AsyncClient() as client:
                await client.post(url, json={"callback_query_id": callback_query_id})
        except Exception as e:
            logger.debug(f"answerCallbackQuery ignoré: {e}")

    def _determine_interaction_type(self, update: Dict[str, Any]) -> str:
        """Détermine le type d'interaction."""
        if 'message' in update:
            message = update['message']
            if message.get('text', '').startswith('/'):
                return 'command_received'
            elif 'document' in message or 'photo' in message or 'voice' in message:
                return 'file_received'
            else:
                return 'message_received'
        elif 'callback_query' in update:
            return 'button_clicked'
        return 'message_received'
