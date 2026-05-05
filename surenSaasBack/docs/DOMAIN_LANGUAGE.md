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

## Conventions de Code

| Règle | Explication |
|-------|-------------|
| `statut` jamais `status` | Cohérence DB PostgreSQL (enum `statut_*`) |
| `chantier_id` jamais `site_id` | Terminologie métier |
| `org_id` toujours présent | Isolation multi-entreprise obligatoire |
| Mémoire LangGraph > état DB | La session vit en mémoire, pas en `telegram_users.last_state` |
