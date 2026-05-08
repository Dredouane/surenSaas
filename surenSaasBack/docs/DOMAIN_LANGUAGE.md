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
| **tg-mock** | Serveur local qui émule l'API Telegram (Docker `aiogram/telegram-bot-api`). Écoute sur le port 8081. Stocke les messages du bot et les retourne via `getUpdates`. | `docker-compose.e2e.yml` |
| **TgMockClient** | Client HTTP qui interagit avec tg-mock : envoie des messages sur le webhook backend, récupère les réponses du bot via `getUpdates`. | `conftest.py` |
| **bot_seed** | Fixture pytest qui upsert un bot de test dans `telegram_bots` (Supabase) pour que le backend accepte les appels webhook. `webhook_token` fixe : `"test-e2e-token"`. | `conftest.py` |
| **Verdict attendu** | `expected_verdict: pass\|fail` dans le YAML. Conception RED-GREEN : `fail` d'abord, puis `pass` quand la feature est implantée. | `scenarios/*.yaml` |
| **Historique de conversation** | Tous les messages (utilisateur + bot) accumulés par le SessionRunner au fil des steps d'un scénario. Passé au Judge pour évaluation contextuelle. | `engine.py` |
| **webhook_token** | Segment de l'URL du webhook backend identifiant le bot. Ex: `test-e2e-token` dans `POST /api/v1/{org_id}/telegram/webhook/test-e2e-token`. | `telegram_core.py` |
| **RED-GREEN** | Convention de progression des scénarios : `expected_verdict: fail` → implémentation backend → `pass`. | `scenarios/*.yaml` |
| **run-e2e.sh** | Script d'orchestration : source `.bashrc` → docker compose up (tg-mock) → `run-local-back_test.sh --tg-mock` → attend /health → pytest → cleanup Docker. | `scripts/run-e2e.sh` |

## Conventions de Code

| Règle | Explication |
|-------|-------------|
| `statut` jamais `status` | Cohérence DB PostgreSQL (enum `statut_*`) |
| `chantier_id` jamais `site_id` | Terminologie métier |
| `org_id` toujours présent | Isolation multi-entreprise obligatoire |
| Mémoire LangGraph > état DB | La session vit en mémoire, pas en `telegram_users.last_state` |
