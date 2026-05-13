# Ubiquitous Language — Module Chantier

Generated: 2026-04-27 via `ubiquitous-language.md` skill
Contexte : SurenSaaS — Gestion de chantiers de construction

---

## Termes du Domaine

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **Chantier** | Site de construction avec cycle de vie complet (en_cours, termine, en_attente, cloture) | Tous les modules | Utiliser `chantier` (pas `site`, `project`, `worksite`) |
| **Opération HITL** | Action terrain signalée par un conducteur via Telegram (homme-in-the-loop) | Chantier > Operations | Toujours qualifier avec `HITL` dans le code pour éviter confusion avec opérations CRUD génériques |
| **Pointage** | Relevé de présence journalier pour les ressources (hommes + machines) | Chantier > Pointages | Ne pas confondre avec `attendance` ou `presence` |
| **Ressource** | Homme (`homme`) ou machine (`machine`) affecté(e) à un chantier | Chantier > Pointages | Typé par `chantier_ressource_type` |
| **Situation** | Jalon financier facturé ou à facturer sur un chantier | Chantier > Situations | Ne pas confondre avec `invoice` ou `facture` — c'est un état d'avancement |
| **Réception** | Réunion client avec statut (planifiee, en_cours, terminee, annulee) et type (livraison, validation, probleme, suivi) | Chantier > Réceptions | Pas `meeting` ou `rdv` |
| **Tâche** | Action assignée depuis la direction vers l'équipe, avec priorité et source | Chantier > Tâches | Typée par `chantier_tache_type` (information, action, validation, rapport) et `chantier_tache_source` (direction, systeme, client) |
| **Notification chantier** | Message bidirectionnel entre le chantier et l'équipe via Telegram | Chantier > Notifications | Typée par `chantier_notification_type` (tache, reception, pointage, validation, alerte, info, urgence) |
| **Statut (colonne DB)** | Colonne nommée `statut` dans TOUTES les tables chantier (pas `status`) | DB > Chantier | Règle absolue : `statut`, jamais `status` |
| **Conducteur** | Utilisateur terrain qui interagit via le bot Telegram | Chantier > Telegram | Rôle métier : celui qui pointe, signale des opérations, valide des réceptions |
| **Gérant** | Utilisateur bureau qui supervise via le frontend web | Chantier > Frontend | Rôle métier : celui qui crée des chantiers, assigne des tâches, consulte les indicateurs |
| **Trigger métier** | Fonction SQL `recalculer_metriques_chantier()` qui recalcule les KPI financiers | DB > Chantier | Déclenchée automatiquement sur INSERT/UPDATE/DELETE de situations et dépenses uniquement |
| **Audit trail** | Historique de toutes les actions (création, modification, validation, rejet, suppression) via `chantier_audit_trail` | DB > Chantier | Généré automatiquement par trigger SQL |
| **HITL (Human-In-The-Loop)** | Principe où une action terrain est initiée par un humain via Telegram puis validée | Architecture > Bot | Workflow : signalement → extraction → validation → persistance |

---

## Mapping Termes ↔ Fichiers

| Terme | Backend | Frontend | Bot | DB |
|-------|---------|----------|-----|----|
| Chantier | `app/api/chantiers.py` | `dashboard/chantiers/` | `bot_construction*.py` | `chantiers` |
| Opération HITL | `chantiers.py` (endpoints `/operations`) | `OperationsList.tsx` | `bot_construction_operations.py` | `chantier_operations_htl` |
| Pointage | `chantiers.py` (endpoints `/pointages`) | `PointagesList.tsx` | `bot_construction_pointages.py` | `chantier_pointages`, `chantier_pointage_ressources`, `chantier_ressources` |
| Situation | `chantiers.py` (endpoints `/situations`) | `SituationsTable.tsx`, `ValidationProduction.tsx` | `bot_construction_avancements.py` | `chantier_situations`, `chantier_situation_lignes` |
| Réception | `chantiers.py` (endpoints `/receptions`) | `ReceptionsList.tsx` | `bot_construction_receptions.py` | `chantier_receptions` |
| Tâche | `chantiers.py` (endpoints `/taches`) | `TachesList.tsx` | `bot_construction_taches.py` | `chantier_taches` |
| Notification | `chantiers.py` (endpoints `/notifications`) | `NotificationsPanel.tsx` | Notification non automatisée | `chantier_notifications` |
| Ressource | `chantiers.py` (endpoints `/ressources`) | — | Pointages > liste ressources | `chantier_ressources` |
| Audit | — | `AuditTrail.tsx` | — | `chantier_audit_trail` |
| Indicateurs | — | `Indicateurs.tsx` | Workflow "📊 Indicateurs" | Vue calculée via `recalculer_metriques_chantier()` |

---

## Termes du Domaine — Extension Situations

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **SituationOuverte** | Situation en cours, accumulant des lignes d'avancement terrain avant facturation finale | Chantier > Situations | `statut='ouverte'` — pas encore facturée |
| **SituationLigne** | Ligne de détail d'une situation : description, quantité, prix unitaire, % avancement, photo | Chantier > Situations | Table `chantier_situation_lignes`, FK → `chantier_situations` |
| **Item de production** | Saisie unitaire du conducteur via Telegram : ligne de situation + % + photo/note | Chantier > Bot > Telegram | Workflow HITL : signalement → validation → consolidation |
| **Avancement** | Pourcentage réalisé (0-100%) sur une ligne de situation | Chantier > Situations > Lignes | Champ `avancement_pourcentage` dans `chantier_situation_lignes` |
| **Consolidation** | Passage d'une SituationOuverte (`statut='ouverte'`) à facturée (`statut='validee'`) | Chantier > Situations | Déclenché par le gérant depuis le frontend |
| **Photo de preuve** | Photo attachée à un item de production ou une opération HITL, stockée dans le cloud | Chantier > Preuves | Optionnelle, URL stockée dans `photo_url` (TEXT) |
| **Validation de Production** | Écran gérant où les lignes accumulées sont approuvées ou ajustées avant consolidation | Frontend > Chantier > Situations | Vue dédiée dans l'onglet Situations |

## Workflows Telegram — Machine d'État

| État | Déclencheur | Handler | Table concernée |
|------|-------------|---------|-----------------|
| `idle` | Menu principal / /start | `handle_start_command` | `telegram_users.last_state` |
| `op_awaiting_description` | Click "Signaler opération" | `handle_operation_media` | `chantier_operations_htl` |
| `op_awaiting_validation` | Saisie description opération | `handle_save_operation` | `chantier_operations_htl` |
| `depense_awaiting_description` | Click "Signaler dépense" | `handle_depense_media` | `chantier_depenses` |
| `depense_awaiting_validation` | Saisie description dépense | `handle_save_depense` | `chantier_depenses` |
| `avancement_awaiting_situation` | Click "📈 Avancement chantier" | *(Créer)* | `chantier_situations` |
| `avancement_awaiting_ligne` | Choix situation ouverte | *(Créer)* | `chantier_situation_lignes` |
| `avancement_awaiting_validation` | Saisie ligne d'avancement | *(Créer)* | `chantier_situation_lignes` |

**Règle :** Chaque workflow suit le pattern : `idle → await_X_description → await_X_validation → idle`

## Règles Strictes

1. **Toujours `statut`** en base, jamais `status`
2. **Toujours `chantier_id`** comme FK, jamais `site_id` ou `project_id`
3. **Toujours `org_id`** pour l'isolation multi-tenant
4. **Toujours qualifier "opération"** par `HITL` dans le code (`chantier_operations_htl`, `handle_operation_media`, etc.)
5. **Toujours utiliser les enums** DB (`chantier_statut`, `chantier_operation_type`, etc.) — pas de strings libres
6. **`.execute()` sur Supabase retourne une liste** dans `.data` — toujours accéder via `data[0]['col']` pas `data['col']`
7. **Les statuts de situation** sont : `ouverte`, `validee`, `transmise`, `payee` (enum `chantier_situation_statut`)
8. **Une photo de preuve** est stockée comme URL TEXT, jamais comme blob en base
9. **Le `%avancement`** est un DECIMAL(5,2) entre 0 et 100, stocké dans `chantier_situation_lignes.avancement_pourcentage`

---

## Termes du Domaine — Extension Telegram Mini App (TMA)

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **TMA** | Telegram Mini App : WebApp SPA Next.js intégrée dans le WebView Telegram, isolée sous `/mini-app` | TMA > Route Group | Route Group `(tma)/mini-app/` avec layout dédié, aucun asset du SaaS Desktop |
| **InitData** | Payload d'authentification signé HMAC-SHA256 du bot Telegram, envoyé par la TMA au backend | TMA > Auth Bridge | Seule source de vérité pour l'auth TMA ; `start_param` utilisé uniquement pour le routage métier |
| **OriginContext** | Source du déclenchement IA : `TELEGRAM_BOT`, `TMA_PROGRESS_SLIDER`, `TMA_EXPENSE_SCANNER` | Architecture > Audit Trail | Stocké dans `logs_agents.origin_context` ; permet de tracer si une extraction vient du vocal bot ou du slider TMA |
| **TargetEntity** | Référence métier ciblée par l'appel IA : `{type, id, project_id}` | Architecture > Audit Trail | Stocké dans `logs_agents.target_entity` (JSONB) ; permet de filter l'historique IA par chantier, tâche ou situation |
| **DeviceInfo** | Empreinte matérielle/OS du terminal : `{platform, app_version, connection_type}` | Architecture > Audit Trail | Stocké dans `logs_agents.device_info` (JSONB) ; utile pour débugger les bugs liés au hardware terrain |
| **CorrelationID** | UUID généré à l'entrée dans `/mini-app`, propagé sur chaque appel API en header `X-Correlation-ID` | TMA > Infrastructure | Permet de tracer une action utilisateur de bout en bout (click → API → IA → DB → notification) |
| **Guardrails IA** | Validation Zod de la sortie IA avant affichage HITL : `avancement_pourcentage` 0-100, `montant` ≥ 0, etc. | TMA > Workflow Extraction | Si le validateur échoue → log dans `guardrail_issues`, fallback vers données brutes, pas de blocage |
| **InitData Validation** | Vérification HMAC-SHA256 du `initData` Telegram avec le `BOT_TOKEN` ; génération d'un JWT short-lived (15 min) | TMA > Auth Bridge | Endpoint `POST /api/v1/tma/auth` ; JWT porté en `Authorization: Bearer` par chaque appel API TMA |
| **WebView Fallback** | Si `window.Telegram.WebApp` est absent, affichage d'un message "Ouvrir dans Telegram" + QR code | TMA > Frontend | Pas de redirection vers le SaaS Desktop (isolation stricte des contextes) |
| **Bottom Tab Bar** | Barre de navigation inférieure fixe (Sticky Bottom) avec 4 onglets : 📊 Chantier, 📈 Progression, 💰 Dépenses, 👷 Équipe | TMA > Navigation | Design one-handed thumb operation ; padding-bottom `pb-16` sur le contenu |

---

## Termes du Domaine — Extension Pipeline Audio (Whisper + Gemini)

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **Pipeline Audio** | Chaîne de traitement en deux étapes : transcription Whisper puis structuration Gemini | Architecture > Services | Toujours logger chaque étape séparément dans `logs_agents` |
| **Whisper** | Modèle `whisper-large-v3` via OpenRouter pour la transcription audio en texte brut | Appelé depuis `whisper_service.py` | Input : blob audio (webm/ogg/wav). Output : chaîne texte. API compatible OpenAI |
| **OpenRouter** | Proxy API unifié pour modèles LLM. Utilisé pour Whisper (audio → texte) | Config > `SUREN_OPEN_ROUTER_API_KEY` | URL : `https://openrouter.ai/api/v1/audio/transcriptions`. Clé secrète déploy |
| **Structuration Gemini** | Deuxième étape du pipeline : transforme le texte transcrit en JSON structuré pour Supabase | Appelé depuis `transcribe_service.py` | System Prompt : parseur JSON strict. Schéma : `{task_id, percentage, status, observation}` |
| **StructuredAudio** | Résultat complet du pipeline : `{transcript, structured, whisper_log_id, gemini_log_id}` | TMA > Endpoint API | Permet au frontend d'afficher à la fois le texte brut et le JSON interprété |
| **Étape (Step)** | Une des deux phases du pipeline : `whisper` ou `gemini_structuration` | Architecture > Audit | Permet de monitorer précisément quelle étape échoue. `logs_agents.agent_type` = `whisper_transcription` ou `gemini_structuration` |

## Mapping Pipeline Audio ↔ Fichiers

| Terme | Backend | Frontend |
|-------|---------|----------|
| Whisper | `app/services/whisper_service.py` | — |
| Pipeline Audio | `app/services/transcribe_service.py` (fonction `transcribe_pipeline`) | — |
| Endpoint | `app/api/tma.py` (POST `/transcribe-and-structure`) | `VoiceRecorder.tsx` (appel optionnel après transcription) |
| Config | `app/core/config.py` (SUREN_OPEN_ROUTER_API_KEY) | — |
| Tests Whisper | `tests/test_whisper_service.py` | — |
| Tests Pipeline | `tests/test_transcribe_pipeline.py` | — |
| Tests API | `tests/test_tma_transcribe_and_structure_api.py` | — |

## Termes du Domaine — Extension Agents LangGraph

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **Graphe Orchestrateur** | Instance LangGraph pilotant le cycle : Classification -> Décision -> Tool -> Réflexion -> Output | Architecture > Agents | Centralise toute la logique de décision du bot et de la TMA |
| **Thread ID** | ID unique (Telegram User ID) partagé Bot/TMA, clé de persistance dans le schéma `agents` | Architecture > Agents | Assure la continuité du contexte entre le Bot et la TMA |
| **Busy State** | État de verrouillage d'un thread pendant qu'un agent traite une demande | Architecture > Agents | Empêche les collisions de state |
| **Audio Expert** | Nœud spécialisé dans la transcription Whisper (OpenRouter) et la normalisation métier (Vertex AI Gemini) | Architecture > Agents | Transforme le binaire `.ogg` en texte structuré |
| **Vision Expert** | Nœud spécialisé dans l'OCR de documents financiers et la classification de photos de chantier | Architecture > Agents | Distingue ticket/facture (workflow dépense) de photo métier (workflow progrès) |
| **Pre-Reflector** | Nœud de contrôle avant l'appel d'un outil pour vérifier la cohérence des arguments | Architecture > Agents | Valide que le `chantier_id` existe et que les montants sont réalistes |
| **Final Reflector** | Nœud de contrôle après l'appel d'un outil pour analyser le résultat réel de la base de données | Architecture > Agents | Gère les erreurs métier et les transforme en explications polies |
| **Output Formatter** | Nœud final préparant le message Telegram avec le ton "Collègue de chantier" et les boutons d'action | Architecture > Agents |
| **Memory Trim** | Stratégie de fenêtre glissante conservant les 10 derniers messages | Architecture > Agents | Évite la saturation du contexte |
| **State Summary** | Résumé persistant de la conversation stocké dans le State du graphe | Architecture > Agents | Mémoire long terme |

## Mapping Workflows Métier ↔ Tools

| Workflow | Tool | Service | Table DB |
|----------|------|---------|----------|
| **Dépenses** | `create_depense` | `tools.py:101` | `chantier_depenses` |
| **Opérations HITL** | `create_operation` | `tools.py:129` | `chantier_operations_htl` |
| **Pointages** | `manage_attendance` | `tools.py:159` | `chantier_pointages`, `chantier_pointage_ressources` |
| **Avancements** | `report_progress` | `tools.py:192` | `chantier_situation_lignes` |
| **Tâches** | `manage_tasks` | `tools.py:222` | `chantier_taches` |
| **Liste chantiers** | `get_user_chantiers` | `tools.py:75` | `chantiers` |
| **Détail chantier** | `get_chantier_details` | `tools.py:89` | `chantiers` |

## Termes du Domaine — Extension Interface Intelligente

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **ActionType** | Énumération des actions d'interface : `DISPLAY_TEXT`, `DISPLAY_MENU`, `INIT_FORM`, `CONFIRM_ACTION` | Architecture > Interface > ActionRegistry | Toujours utiliser l'enum, pas de string libre |
| **format_response** | Tool LLM qui structure la réponse en texte + action + payload JSON | Architecture > Interface > Output Parser | Schéma validé par Pydantic `FormatResponseSchema` |
| **ParsedResponse** | Structure de sortie : texte + action + payload prêts pour Telegram | Architecture > Interface > ActionRegistry | Produit par `ActionRegistry.parse_response()` |
| **PendingForm** | État d'un formulaire multi-étapes en cours, stocké dans `AgentState.pending_form` | Architecture > Interface > FormEngine | Survit au redémarrage via LangGraph Checkpointer |
| **FormStep** | Une étape d'un formulaire : nom, label, type (text/number/select/date), options | Architecture > Interface > FormEngine | Le type `select` nécessite une liste d'options |
| **FormEngine** | Moteur qui avance étape par étape dans un formulaire et collecte les données | Architecture > Interface > FormEngine | Utilise `advance(step_name, value)` pour progresser |
| **MenuContext** | Contexte pour la génération de menu : chantier_id, user_role, pending_form | Architecture > Interface > MenuManager | Le rôle `gerant` voit plus d'actions que `conducteur` |
| **MenuManager** | Générateur de menus contextuels dynamiques adaptés au rôle et au chantier | Architecture > Interface > MenuManager | Produit des claviers inline Telegram |
| **Callback Router** | Routage des callbacks Telegram vers les handlers du graphe LangGraph | Architecture > Interface > Stateful Router | Format : `act:<action_name>:<step>` (limité à 64 octets) |
| **Output Formatter** | Nœud LangGraph qui parse la réponse LLM et met à jour `pending_form` et `last_action_status` | Architecture > Interface > Graph | S'exécute après `agent` et avant l'envoi à Telegram |

## Nouveaux Fichiers — Interface Intelligente

| Fichier | Rôle |
|---------|------|
| `app/services/agents/actions.py` | ActionRegistry, FormatResponseSchema, ActionType enum, tool `format_response` |
| `app/services/agents/form_engine.py` | PendingForm, FormStep, FormEngine (gestion multi-étapes) |
| `app/services/agents/menu_manager.py` | MenuContext, MenuManager (menus dynamiques par rôle/chantier) |
| `tests/test_action_parser.py` | Tests Output Parser (3 tests) |
| `tests/test_form_engine.py` | Tests Form Engine (7 tests) |
| `tests/test_callback_router.py` | Tests Callback Router (2 tests) |
| `tests/test_menu_manager.py` | Tests Menu Manager (4 tests) |
| `tests/test_system_prompt.py` | Tests system prompt format_response (2 tests) |

## Termes du Domaine — Extension UI Telegram

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **InlineKeyboard** | Boutons attachés à un message Telegram, envoyés via `reply_markup` | Interface > Telegram | Généré par `ActionRegistry.build_keyboard()` ou `MenuManager.get_inline_keyboard()` |
| **ForceReply** | Mécanisme Telegram qui force l'utilisateur à répondre à un message précis | Interface > FormEngine | Utilisé pour les champs texte/number dans un formulaire multi-étapes |
| **ReplyKeyboard** | Menu persistant remplaçant le clavier utilisateur en bas de l'écran Telegram | Interface > MenuManager | Pas encore implémenté (P3) |
| **answerCallbackQuery** | Notification flash en haut de l'écran Telegram accusant réception d'un clic | Interface > WebhookHandler | Évite le "spinner" infini sur les boutons inline |
| **ForceReply Trigger** | Moment où le webhook_handler détecte un besoin de saisie et verrouille la réponse | Interface > WebhookHandler | Déclenché par `INIT_FORM` avec champ de type `text` ou `number` |
| **Callback Ack** | Signal envoyé à Telegram pour dire "J'ai bien reçu ton clic" | Interface > WebhookHandler | Appelé dans `_process_graph_callback()` via `answer_callback_query` |

## Règles Strictes — Interface LLM

1. **Le LLM DOIT utiliser le tool `format_response`** pour toute action d'interface (menu, formulaire, confirmation). Pas de listes Markdown à la place.
2. **`format_response` est bindé** au LLM dans `call_model_node` via `bind_tools([..., format_response])`.
3. **`format_response` est dans le ToolNode** du graphe pour exécution.
4. **Fallback automatique** : si le LLM ne produit pas de `format_response`, le système affiche un `DISPLAY_TEXT` par défaut.
5. **`parsed.text`** ne doit jamais être `None` : utiliser `_extract_text(msg.content)` qui gère les contenus multimodaux (liste de dicts).

## Mapping Termes TMA ↔ Fichiers

| Terme | Backend | Frontend | Bot | DB |
|-------|---------|----------|-----|----|
| TMA | `app/api/tma.py` (2 endpoints : auth, context) | `(tma)/mini-app/` (route group complet) | `construction_menu.py` (WebApp buttons) | — |
| InitData | `app/services/tma_auth_service.py` (HMAC validation) | `providers.tsx` (extraction + envoi) | `bot_construction_commands.py` (start_param encoding) | — |
| Guardrails IA | `app/services/ai/validators.py` (Zod schemas) | — | `extractor.py` (intégré avant affichage) | `logs_agents.guardrail_issues` |
| Audit Agent | `app/services/logs_agent_service.py` | — | — | `logs_agents` (enrichi : origin_context, target_entity, device_info) |
| CorrelationID | `main.py` (middleware log_requests renforcé) | `providers.tsx` (génération + header) | — | `logs_agents.correlation_id` |
| **Graphe Orchestrateur** | Instance LangGraph pilotant le cycle : Classification -> Décision -> Tool -> Réflexion -> Output | Architecture > Agents | Centralise toute la logique de décision du bot et de la TMA |
| **Thread ID** | ID unique (Telegram User ID) partagé Bot/TMA, clé de persistance dans le schéma `agents` | Architecture > Agents | Assure la continuité du contexte entre le Bot et la TMA |
| **Busy State** | État de verrouillage d'un thread pendant qu'un agent traite une demande | Architecture > Agents | Empêche les collisions de state ; renvoie un message "un instant... ⏳" à l'utilisateur |
| **Audio Expert** | Nœud spécialisé dans la transcription Whisper (OpenRouter) et la normalisation métier (Gemini Flash) | Architecture > Agents | Transforme le binaire `.ogg` en texte corrigé avec détection d'urgence |
| **Vision Expert** | Nœud spécialisé dans l'OCR de documents financiers et la classification de photos de chantier | Architecture > Agents | Distingue un ticket/facture (workflow compta) d'une photo métier (workflow progrès) |
| **ExtractedExpense** | Structure de données normalisée pour les dépenses extraites par l'Expert Vision | Architecture > Agents | Schéma : `{fournisseur, montant_ttc, tva, date, is_document, description}` |
| **Normalisation métier** | Processus utilisant Gemini Flash pour corriger les homophones et termes techniques selon le contexte des chantiers | Architecture > Agents | "Thenar" -> "Thénard". Injecte la liste des chantiers réels dans le prompt |
| **Nœud de Réflexion** | Garde-fou post-outil validant le résultat (anti-hallucination, gestion de liste vide) | Architecture > Agents | Si un Tool renvoie `[]`, l'agent propose les options réelles au lieu d'inventer |
| **HITL (Human-In-The-Loop)** | Point d'interruption du graphe attendant une confirmation utilisateur via InlineButton | Architecture > Agents | Permet de valider des actions critiques (paiement, suppression) avant exécution |
| **Pre-Reflector** | Nœud de contrôle avant l'appel d'un outil pour vérifier la cohérence des arguments et éviter les hallucinations | Architecture > Agents | Valide que le `chantier_id` existe et que les montants sont réalistes |
| **Final Reflector** | Nœud de contrôle après l'appel d'un outil pour analyser le résultat réel de la base de données | Architecture > Agents | Gère les erreurs métier (ex: chantier clôturé) et les transforme en explications polies |
| **Output Formatter** | Nœud final préparant le message Telegram avec le ton "Collègue de chantier" et les boutons d'action | Architecture > Agents | Utilise des emojis métier et structure les boutons de confirmation HITL |
| **Memory Trim** | Stratégie de fenêtre glissante conservant les 10 derniers messages pour optimiser le contexte LLM | Architecture > Agents | Évite la saturation du contexte tout en préservant le fil de la conversation |
|| **State Summary** | Résumé persistant de la conversation stocké dans le State du graphe pour la mémoire long terme | Architecture > Agents | Permet à l'agent de se souvenir du contexte global (ex: chantier actif) au-delà de 10 messages |

---

## Termes du Domaine — Module AO v2 (Moteur de Pricing & Benchmarking)

> Ajouté le 2026-05-11 — Session de refonte AO_SPECIFICATION_V2

| Terme | Définition | Contexte/Module | Contrainte |
|-------|-----------|-----------------|------------|
| **Dossier AO** | Dossier de consultation publié par l'Acheteur, contenant les documents de référence (BPU vierge, CCTP, RC). C'est l'entité **parente**. | AO > Dossiers | Table `ao_dossiers`. Jamais `appel_offre` ou `ao_candidature` pour désigner le dossier source |
| **Candidature** | Réponse financière déposée par un offreur (notre client, un concurrent, un partenaire) en réponse à un Dossier AO. C'est l'entité **enfant**. | AO > Candidatures | Table `ao_candidatures`. Une candidature appartient toujours à un `dossier_id` |
| **Type de Candidature** | Nature de l'offreur : `OUR_OFFER` (notre client), `COMPETITOR` (concurrent identifié via ATTRI), `PARTNER` (partenaire uploadé manuellement) | AO > Candidatures | Enum `ao_candidature_type`. Toujours utiliser ces valeurs, jamais de strings libres |
| **Ligne de Prix** | Unité atomique de valeur du système. Prix unitaire extrait d'un BPU/DQE, enrichi de son contexte technique (CCTP) et de son statut compétitif (ATTRI). | AO > Pricing | Table `ao_price_lines`. C'est l'entité centrale du moteur de pricing |
| **Code Métier** | Identifiant normalisé d'une prestation dans la taxonomie hybride. Ex: `DIAG_AMIANTE_AVT_TRAVAUX`, `DIAG_PLOMB_CREP`. | AO > Taxonomie | Colonne `code_metier`. Format : `{DOMAINE}_{PRESTATION}[_{SOUS_TYPE}]`. Assigné par l'Agent Synthétiseur |
| **Taxonomie Hybride** | Classification à deux niveaux des prestations diagnostics/travaux IDF, pilotée par l'IA. Niveau 1 : domaine (`DIAG_AMIANTE`). Niveau 2 : sous-type (`AVANT_TRAVAUX`). | AO > Normalisation | Le mapping est effectué par l'Agent Synthétiseur via prompt Gemini Pro |
| **Agent Synthétiseur** | Agent IA central déclenché manuellement après traitement des documents obligatoires. Orchestre : extraction des lignes de prix → normalisation taxonomie → matching BPU↔CCTP → calcul Gap ATTRI. | AO > Agents | Fichier `ao_synthetiseur.py`. Remplace le `ao_lens_engine.py` de la v1 |
| **Contexte Technique** | Lien persistant entre une Ligne de Prix (BPU) et la section CCTP qui l'encadre techniquement. Stocké avec un score de confiance et un extrait justificatif. | AO > Matching | Table `ao_price_technical_context`. Colonnes : `price_line_id`, `cctp_section_id`, `confidence_score`, `justification_snippet` |
| **Justification Snippet** | Extrait court du CCTP expliquant le lien technique avec une ligne de prix. Généré par Gemini Pro lors du matching. | AO > Matching | Colonne `justification_snippet` dans `ao_price_technical_context`. Permet de répondre "Pourquoi ce prix ?" sans relancer l'IA |
| **ATTRI** | Avis d'Attribution — document officiel indiquant le nom du gagnant et le montant global HT de l'offre retenue. Ne contient PAS le détail ligne par ligne. | AO > Documents | Type `ATTRI` dans l'enum `ao_document_type`. Utilisé pour calculer le Gap de compétitivité |
| **Gap de Compétitivité** | Écart en pourcentage entre le montant total d'une candidature et le montant de l'offre retenue (ATTRI). Un Gap positif = offre au-dessus du prix gagnant. | AO > Benchmarking | Colonne `gap_vs_attri_pct` sur `ao_candidatures`. Formule : `((montant_total - attri_montant) / attri_montant) * 100` |
| **Knowledge Base (KB)** | Base de données de prix de référence alimentée par les lignes de prix validées (`in_knowledge_base = TRUE`). Sert de fondation à l'Explorateur de Prix. | AO > KB | Flag `in_knowledge_base` sur `ao_price_lines`. Vue `ao_kb_prix_reference` pour la consultation |
| **KB Locale** | Vecteurs CCTP/RC d'un seul Dossier AO, utilisés uniquement pour le matching BPU↔CCTP de l'Agent Synthétiseur. | AO > RAG | Filtrage sur `dossier_id` dans `ao_embeddings` |
| **KB Cross-AO** | Ensemble des lignes de prix validées de tous les dossiers de l'org. Sert au benchmarking et à l'Explorateur de Prix. | AO > RAG | Données de `ao_kb_prix_reference` (vue SQL). Isolation stricte par `org_id` |
| **Explorateur de Prix** | Interface de consultation de la KB Cross-AO. Permet de rechercher une prestation et de voir : prix moyen gagnant, dernier prix client, min/max, références sources. | AO > Frontend | Page `/dashboard/ao/explorer`. Composant `PriceExplorer.tsx` |
| **Dernier Prix Client** | Dernier prix unitaire utilisé par notre client (`OUR_OFFER`) pour un code métier donné. Affiché dans l'Explorateur de Prix. | AO > KB | Sous-requête dans `ao_kb_prix_reference` filtrée sur `type_candidature = 'OUR_OFFER'` ORDER BY `created_at DESC` |
| **HITL AO** | Validation humaine des lignes de prix dont le score de confiance est inférieur au seuil (85%). Permet de corriger le code métier ou le prix avant injection en KB. | AO > Validation | Enum `ao_validation_statut` : `EN_ATTENTE`, `VALIDE`, `REJETE`, `CORRIGE`, `AUTO_VALIDE`. Interface : `HITLValidationTable.tsx` |
| **Seuil de Confiance** | Score minimum (0.85) en dessous duquel une ligne de prix passe en validation humaine (`EN_ATTENTE`). Au-dessus : `AUTO_VALIDE`. | AO > HITL | Constante `AO_CONFIDENCE_THRESHOLD = 0.85`. S'applique à `normalisation_confiance` et `confidence_score` (matching) |
| **Worker Extraction** | Service dédié à l'extraction brute d'un type de fichier. Trois workers : PDF (Gemini OCR), Excel (openpyxl double-passe), DOCX (python-docx par section). | AO > Pipeline | Fichiers : `ao_excel_extractor.py`, `ao_docx_extractor.py`. PDF via `generic_extractor.py` existant |
| **Double-Passe Excel** | Stratégie d'extraction Excel consistant à lire le fichier deux fois avec `openpyxl` : une fois pour les formules (`data_only=False`) et une fois pour les valeurs calculées (`data_only=True`). | AO > Worker Excel | Colonne `formule_brute` + `valeur_calculee` sur `ao_price_lines`. Les formules révèlent les marges et règles de calcul |
| **Complétude Dossier** | État d'un Dossier AO indiquant que tous les documents obligatoires (BPU + DQE + CCTP) sont présents et traités. Condition nécessaire pour déclencher l'Agent Synthétiseur. | AO > Pipeline | Colonne `docs_obligatoires_ok` sur `ao_dossiers`. Calculée par `check_dossier_completude()` |
| **Statut Dossier** | État du pipeline d'un Dossier AO : `INCOMPLET` → `PRET` → `EN_ANALYSE` → `ANALYSE_OK` ou `ERROR`. | AO > Pipeline | Enum `ao_dossier_statut`. Colonne `statut` sur `ao_dossiers` |
| **Traçabilité Source** | Capacité à retrouver l'origine exacte d'une donnée extraite : clé R2, numéro de page PDF, numéro de ligne et nom d'onglet Excel. Permet le lien cliquable vers le document source. | AO > Traçabilité | Colonnes `r2_file_id`, `page_number`, `row_number`, `sheet_name` sur `ao_price_lines` et `ao_embeddings` |
| **Chunk Sémantique** | Unité de texte vectorisée respectant la structure logique du document. CCTP : 800–1000 tokens par section. BPU/DQE : 1 ligne = 1 chunk (jamais découpée). | AO > RAG | Stratégie dans `ao_rag_service.py`. L'atomicité des lignes BPU est une règle absolue |
| **Zone Géo** | Code de département IDF (75, 77, 78, 91, 92, 93, 94, 95). Granularité de référence pour le benchmarking géographique. | AO > Contexte | Colonne `zone_geo` sur `ao_dossiers`, `ao_price_lines`, `ao_embeddings`. Jamais "IDF" en bloc |
| **Type Acheteur** | Catégorie de l'entité publiant l'AO : `BAILLEUR_SOCIAL`, `COLLECTIVITE`, `PRIVE`, etc. Dimensionne le benchmarking. | AO > Contexte | Colonne `type_acheteur` sur `ao_dossiers` et `ao_price_lines`. Hérité du dossier vers les lignes de prix |

### Règles Strictes — Module AO v2

1. **Toujours `ao_dossiers`** pour l'entité parent (le dossier de consultation de l'acheteur)
2. **Toujours `ao_candidatures`** pour les réponses déposées (notre client, concurrent, partenaire)
3. **Toujours `code_metier`** pour l'identifiant normalisé (jamais `category`, `type`, `label`)
4. **Toujours `in_knowledge_base`** comme flag d'injection KB — une ligne non validée ne doit JAMAIS apparaître dans l'Explorateur de Prix
5. **Toujours `r2_file_id` + `page_number`** pour toute donnée extraite — la traçabilité source est obligatoire
6. **1 ligne BPU = 1 chunk** — règle absolue, ne jamais découper une ligne de prix entre deux vecteurs
7. **`statut`** (pas `status`) sur toutes les tables AO
8. **`org_id`** sur toutes les tables AO — isolation multi-tenant systématique

---

## Termes du Domaine — Extension Harnais de Validation (E2E Blackbox)

| Terme | Définition | Contexte | Contrainte |
|-------|-----------|----------|------------|
| **Harnais de Validation** | Dispositif de test blackbox qui simule Telegram pour injecter des Updates et capturer les réponses du bot | Tests > E2E | Tourne sur localhost VPS ; ne touche pas au code interne du bot |
| **tg-mock** | Serveur Go (Docker) qui remplace `api.telegram.org` localement : mocke `sendMessage`, `sendPhoto`, `sendDocument` et expose un endpoint `/updates` pour injecter des Updates | Tests > Simulateur | Port 8081. Le bot backend pointe vers `http://localhost:8081/bot<TOKEN>/...` via `TELEGRAM_BASE_URL` |
| **Runner (pytest)** | Script Python pytest qui orchestre le test : lit un YAML → POST à tg-mock → capture la réponse → appelle le Juge | Tests > Runner | Utilise une fixture `tg_mock_client` ; timeout/polling configurable pour la latence LLM |
| **Scénario YAML** | Fichier `.yaml` décrivant un test : input Telegram (text/voice/photo/pdf) + critère de jugement LLM | Tests > Scénarios | Validé par Pydantic dans le runner. Contient sections `input`, `judge`, `expected_verdict` |
| **LLM Judge (Gemini Flash)** | Appel à Gemini Flash qui compare la réponse du bot au critère attendu et rend un verdict `{score: 1/0, reason: "..."}` | Tests > Judge | Prompt machine-readable structuré : SCENARIO + REPONSE → JSON verdict |
| **Reset d'état inter-scénario** | Nettoyage de la mémoire LangGraph et des enregistrements DB entre deux scénarios YAML pour éviter la pollution | Tests > Runner | Exécuté après chaque test via fixture pytest `autouse` avec scope `function` |
| **Polling Timeout** | Délai d'attente configurable (ex: 15s) entre l'injection de l'Update et la récupération de la réponse bot | Tests > Runner | Nécessaire car le backend utilise LangGraph + LLM (latence variable) |
