# Domain Language — SurenSaaS Bot Telegram

> Langage ubiquitaire : ces définitions sont LA référence pour Hermes et Pi.
> Tout code, prompt, test ou documentation utilisant ces termes DOIT respecter ces définitions.

---

## Concepts Fondamentaux

| Terme | Définition | Exemple |
|-------|-----------|---------|
| **Session d'input** | Cycle de messages utilisateur sur un même chantier. Débute au premier message, s'accumule en mémoire LangGraph, se termine par HITL#1 (envoi) ou annulation. Un seul chantier par session. | User envoie dépense → reçoit résumé → ajoute photo → reçoit nouveau résumé → ✅ Envoi groupé |
| **HITL#1** | Validation par le conducteur de terrain. Le LLM résume ce qu'il a extrait, le user confirme. Déclenche l'écriture DB en `en_attente_validation`. | "J'ai compris : dépense 150€ SARL Bâti. ✅ Envoyer ?" |
| **HITL#2** | Validation par le gérant/backoffice. Vérifie la donnée et la passe en `valide` ou `rejete` (avec motif). Implémenté plus tard. | Gérant voit "Pointage du 04/05 en attente" → ✅ ou ❌ motif |
| **Chantier courant** | Le chantier sélectionné pour la session en cours. Un seul à la fois. Détecté par fuzzy matching sur les chantiers "en cours" du user. | Si user dit "sur le chantier B", l'agent fuzzy-match "B" → UUID chantier |
| **Workflow** | Ensemble de règles métier (invariants) qu'un agent LangGraph exécute pour collecter, valider et persister un type de donnée métier. | Workflow Dépense, Workflow Pointage |
| **buffer_data** | Zone de mémoire temporaire du state LangGraph. Stocke le résumé de la session en cours (workflow, step, summary). Persiste entre les tours via le retour de `call_model_node`. | `{"workflow": "operation", "step": "init", "summary": "Signalement..."}` |
| **TTL (Time To Live)** | Mécanisme d'expiration du `buffer_data`. Si inactivité > 300s, le buffer est vidé pour éviter les résidus de session. | `if (now - last_msg_time) > 300: buf = None` |
| **last_message_time** | Timestamp Unix du dernier message utilisateur. Mis à jour à chaque message entrant dans `webhook_handler.py` et retourné par `call_model_node`. | `"last_message_time": time.time()` |

---

## Rôles

| Terme | Définition |
|-------|-----------|
| **Conducteur de travaux** | Utilisateur principal du bot. Envoie les données terrain. Déclenche HITL#1. A accès à ses chantiers "en cours". |
| **Gérant / Chef d'entreprise** | Valide les données en backoffice (HITL#2). Voit les statuts `en_attente_validation`. |
| **Ressource** | Personne (type=homme) ou engin (type=machine) affecté à un chantier. |

## Statuts (Modèle de Données)

| Statut | Scope | Signification |
|--------|-------|---------------|
| `brouillon` | Optionnel | Données en cours, session ouverte en mémoire LangGraph non persistée |
| `en_attente_validation` | Toute table métier | HITL#1 passé, en attente du gérant (HITL#2) |
| `valide` | Toute table métier | Gérant a approuvé |
| `rejete` | Toute table métier | Gérant a refusé, avec `motif_rejet` obligatoire |

## Architecture

| Terme | Définition |
|-------|-----------|
| **VOIE A** | Pipeline legacy : menu boutons + état DB (`telegram_users.last_state`) + handlers séquentiels. Destinée à être remplacée. |
| **VOIE B** | Pipeline LangGraph : agent Gemini 2.5 Flash, accumulation session, interruptions HITL, écriture DB en fin de session. Architecture cible. |
| **LangGraph** | Framework de graphe d'état utilisé pour orchestrer l'agent conversationnel. StateGraph avec interruptions `interrupt_before=["tools"]`. |
| **GenericDocumentExtractor** | Outil OCR existant (VOIE A) qui doit migrer en tool LangGraph pour traitement agentique de photos/PDFs. |

## Navigation de Session (Prompt V3.3)

| Terme | Définition |
|-------|-----------|
| **MÉMOIRE DE SESSION** | Résumé du workflow en cours, qualifié de "CONSÉQUENCE DU PASSÉ". Perd son autorité face à un nouveau message sans rapport. |
| **ANALYSE DE CONTINUITÉ** | Le LLM évalue si le message utilisateur s'inscrit dans la suite logique de la session actuelle. |
| **GESTION DE RUPTURE** | Si le message introduit un nouveau workflow, le LLM DOIT ignorer la MÉMOIRE DE SESSION et initialiser une nouvelle session. |
| **Aucune session active** | Valeur par défaut du résumé quand `buffer_data` est vide. Indique au LLM qu'il n'y a pas de session en cours. |

## Callbacks & Actions

| Terme | Définition |
|-------|-----------|
| **HITL:confirm** | Callback de reprise LangGraph après validation utilisateur |
| **HITL:cancel** | Callback d'annulation LangGraph |
| **Session:reset** | Annulation explicite de la session courante, retour à l'état idle |

---

## Tests E2E — Harnais Autonome

> Terminologie du `e2e-harness/` : harnais de test E2E isolé du backend, avec son propre venv.

| Terme | Définition | Contexte/Module |
|---|---|---|
| **e2e-harness** | Harnais de test E2E autonome, dans `surenSaas/e2e-harness/`, avec son propre venv (`venv-e2e/`). Découple les tests E2E du backend. | `e2e-harness/` |
| **SessionRunner** | Moteur d'exécution de scénarios. Prend un `Scenario` YAML, l'exécute step par step en accumulant l'historique, et appelle le Judge à chaque step. | `engine.py` |
| **Judge** | LLM (Gemini 2.5 Flash via API HTTP) qui évalue si la réponse du bot correspond au comportement attendu pour un step donné. Retourne `Verdict`. | `judge.py` |
| **Verdict** | Résultat d'une évaluation du Judge : `{"score": 1\|0, "reason": "..."}`. Score 1 = pass, 0 = fail. | `models.py` |
| **Step** | Une étape unitaire dans un scénario : `{type, content, judge_prompt, expected_verdict}`. Types : `text` (message), `callback` (clic bouton), `document` (fichier). | `models.py` |
| **Scenario** | Séquence complète de steps décrivant une interaction utilisateur ↔ bot. Défini dans un fichier YAML dans `scenarios/`. | `models.py` / `scenarios/*.yaml` |
| **tg-mock** | Serveur local (Python, sans Docker) qui émule l'API Telegram sur le port 8081. Stocke les messages du bot et les retourne via `getUpdates`. | `mock_telegram.py` |
| **TgMockClient** | Client HTTP qui interagit avec tg-mock : envoie des messages sur le webhook backend, récupère les réponses du bot via `getUpdates`. | `conftest.py` |
| **bot_seed** | Fixture pytest qui upsert un bot de test dans `telegram_bots` (Supabase) pour que le backend accepte les appels webhook. | `conftest.py` |
| **Historique de conversation** | Tous les messages (utilisateur + bot) accumulés par le SessionRunner au fil des steps d'un scénario. Passé au Judge pour évaluation contextuelle. | `engine.py` |
| **RED-GREEN** | Convention de progression des scénarios : `expected_verdict: fail` → implémentation backend → `pass`. | `scenarios/*.yaml` |
| **Classifier code** | Code Python qui détecte déterministiquement l'intention métier avant l'appel LLM (ex: "signaler" → workflow Opération). | `graph.py:call_model_node` |
| **[SYSTEM-DATA-EXTRACTION]** | Protocole structuré pour les résultats OCR. Le LLM reçoit `RAW_JSON_DATA` avec les données extraites et doit les verbaliser. | `graph.py:vision_expert_node` |
| **[SYSTEM-DATA-PHOTO-ATTACHED]** | Protocole pour les photos en workflow Opération. Le LLM confirme la réception sans analyser l'image. | `graph.py:vision_expert_node` |

## Conventions de Code

| Règle | Explication |
|-------|-------------|
| `statut` jamais `status` | Cohérence DB PostgreSQL (enum `statut_*`) |
| `chantier_id` jamais `site_id` | Terminologie métier |
| `org_id` toujours présent | Isolation multi-entreprise obligatoire |
| Mémoire LangGraph > état DB | La session vit en mémoire, pas en `telegram_users.last_state` |
