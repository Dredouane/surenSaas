# Louki — Todo List / Backlog

> Tenue par Louki (Lead Dev). Priorités: P0 = blocker, P1 = cette semaine, P2 = quand possible.

---

## Installation & Setup

| ID | Tâche | Priorité | Statut | Notes |
|----|-------|----------|--------|-------|
| SETUP-001 | Installer pi-coding-agent (npm global) | P0 | ✅ Fait | `npm install -g @mariozechner/pi-coding-agent` |
| SETUP-002 | Créer skills Pi (grill-me, ubiquitous-language, tdd-cycle, deep-modules) | P0 | ✅ Fait | |
| SETUP-003 | Configurer AGENTS.md global Pi (compréhension projet + rôle) | P0 | ✅ Fait | |
| SETUP-004 | Créer skills Hermes (grill-me, ubiquitous-language, tdd-cycle, deep-modules) | P0 | ✅ Fait | |
| SETUP-005 | Créer Louki-todo-list.md | P0 | ✅ Fait | |
| SETUP-006 | Tester shorting Pi via delegate_task ACP | P0 | ✅ Fait | `delegate_task(acp_command="/usr/local/bin/pi-acp-wrapper")` — fonctionnel |
| SETUP-007 | Installer pi-acp (adapter ACP officiel) | P0 | ✅ Fait | `npm install -g pi-acp` — installé et testé |
| SETUP-008 | Rechercher extensions Pi utiles (Telegram mock, HTTP, end2end) | P1 | ✅ Fait | Voir notes ci-dessous ⬇️ |
| SETUP-009 | Configurer auth.json Pi (clé DeepSeek) | P0 | ✅ Fait | |
| SETUP-010 | Installer pi-yagami-search (web search pour Pi) | P2 | 🔲 Planifié | |
| SETUP-011 | Installer pi-docparser (parsing docs) | P2 | 🔲 Planifié | |
| SETUP-012 | Installer @wayaans/ramean (subagents + guardrails) | P2 | 🔲 Planifié | |
| SETUP-013 | Configurer .pi/settings.json projet dans surenSaas | P1 | 🔲 Planifié | |

---

## Features / Milestones Client

| ID | Tâche | Priorité | Statut | Notes |
|----|-------|----------|--------|-------|
| MIL-001 | [À définir — première feature urgente à attaquer] | P0 | 🔲 Planifié | Attente CTO |

---

## Bugs & Refactoring

Cf. `CHANTIER_TODO_LIST.md` pour la liste complète. Priorités ici :

| ID | Tâche | Priorité | Statut | Notes |
|----|-------|----------|--------|-------|
| BUG-001 | Bug colonne `status` → `statut` dans bot pointages (CHA-001) | P0 | 🔲 Planifié | |
| BUG-002 | `fetchChantierComplet()` inexistant (CHA-004) | P0 | 🔲 Planifié | |
| BUG-003 | Données mock sans API réelle (CHA-T-001) | P1 | 🔲 Planifié | |
| BUG-004 | Imports circulaires dans fichiers bot (CHA-008) | P1 | 🔲 Planifié | |

---

## Exploration Technique

| ID | Tâche | Priorité | Statut | Notes |
|----|-------|----------|--------|-------|
| EXP-001 | Tester des Pi packages : pi-acp, babysitter-pi | P2 | 🔲 Planifié | |
| EXP-002 | Chercher/simuler Telegram bot en local pour E2E | P2 | 🔲 Planifié | |
| EXP-003 | Configurer GitHub MCP ou action pour PR review auto | P2 | 🔲 Planifié | |
