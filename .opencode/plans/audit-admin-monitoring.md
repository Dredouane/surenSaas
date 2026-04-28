# Plan — Écran Audit Admin (Monitoring)

## Objectif
Ajouter un onglet "Audit" dans la page d'administration, exposant le contenu des tables `logs_activity`, `logs_agents`, et les corrélations entre elles.

## Ubiquitous Language
| Terme | Définition |
|-------|-----------|
| Activité | Mutation CRUD dans `logs_activity` |
| Agent IA | Appel LLM tracé dans `logs_agents` |
| Corrélation | chaînage `correlation_id` entre requête HTTP, appels LLM et mutations DB |
| HITL | Human-In-The-Loop (validation humaine d'une sortie IA) |
| Guardrail | Barrière regex ou LLM Judge filtrant les entrées/sorties |
| Delta | Différence entre état précédent et nouvel état |
| Stats audit | Agrégats : total activités, appels IA, erreurs, coût |

## Backend — Phase A (RED → GREEN → REFACTOR)

### A1 — Pydantic schemas (`app/schemas/audit.py`)
- `ActivityLogResponse`, `AgentLogResponse`
- `AuditPaginatedResponse[T]` (items, total, page, page_size)
- `AuditStatsResponse`
- `HitlFeedbackRequest`

### A2 — FastAPI router (`app/api/audit.py`)
Endpoints sous `/api/v1/admin/audit` protégés par `verify_admin`:

| Méthode | Path | Description |
|---------|------|-------------|
| GET | `/activity` | Liste paginée + filtres (org_id, action, table_name, entity_id, user_id, date_from, date_to, source_system) |
| GET | `/activity/{id}` | Détail d'une activité |
| GET | `/agents` | Liste paginée + filtres (org_id, agent_type, model, status, entity_table, entity_id, date_from, date_to, origin_context) |
| GET | `/agents/{id}` | Détail d'un agent |
| GET | `/correlations` | Liste des correlation_id distincts, avec nb activités, nb agents, première/dernière date |
| GET | `/correlations/{correlation_id}` | Détail complet : activités + agents pour ce correlation_id |
| GET | `/stats` | Agrégats : total activité, total agents, taux erreur, coût estimé |

Architecture : appels Supabase Python `.table().select().range().order()` directement dans le routeur (pas de service layer). Pagination page/offset.

### A3 — Enregistrement dans `app/main.py`
`app.include_router(audit_router, prefix="/api/v1")`

### A4 — Tests (`tests/test_api_audit.py`)
- GET activity list (success, empty, filtered, paginated)
- GET agents list (with filters)
- GET correlations (with agents list)
- GET stats
- 403 non-admin
- Mocks : `unittest.mock` sur `get_supabase().table(...).select(...).execute()`

## Frontend — Phase B

### B1 — Page (`app/dashboard/settings/admin/audit/page.tsx`)
Page client-side avec 3 tabs (shadcn/ui Tabs) : Activité, Agents IA, Corrélations

### B2 — 4 cartes stats en haut
Total activités, total appels IA, taux d'erreur, coût estimé

### B3 — Tableau "Activité"
Colonnes : Date, Action (badge coloré), Table, Entité, Utilisateur, IP, Durée
Filtres : date, action, table_name
Modal détail : JSON de `delta`, `previous_state`, `new_state`

### B4 — Tableau "Agents IA"
Colonnes : Date, Type, Modèle, Statut (badge), Prompt (trunc 80), Tokens, Coût, Guardrails
Filtres : date, agent_type, status
Modal détail : JSON `raw_input`, `raw_output`, `guardrail_issues`

### B5 — Tableau "Corrélations"
Colonnes : correlation_id, Nb activités, Nb agents, Première activité, Dernière activité
Au clic : modal listant toutes les activités + tous les agents de cette corrélation

### B6 — Navigation
- Carte "Audit & Monitoring" dans `app/dashboard/settings/page.tsx` (onglet Admin)

## Ordre d'exécution
1. **TDD RED** — Écrire `tests/test_api_audit.py` avec des tests qui échouent
2. **TDD GREEN** — Créer `app/schemas/audit.py` + `app/api/audit.py` + modifier `app/main.py`
3. **TDD REFACTOR** — Vérifier deep modules, nettoyer
4. **Frontend** — Créer `app/dashboard/settings/admin/audit/page.tsx`
5. **Frontend navigation** — Modifier `app/dashboard/settings/page.tsx`
