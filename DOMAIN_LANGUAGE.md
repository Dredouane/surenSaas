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

## Mapping Termes TMA ↔ Fichiers

| Terme | Backend | Frontend | Bot | DB |
|-------|---------|----------|-----|----|
| TMA | `app/api/tma.py` (2 endpoints : auth, context) | `(tma)/mini-app/` (route group complet) | `construction_menu.py` (WebApp buttons) | — |
| InitData | `app/services/tma_auth_service.py` (HMAC validation) | `providers.tsx` (extraction + envoi) | `bot_construction_commands.py` (start_param encoding) | — |
| Guardrails IA | `app/services/ai/validators.py` (Zod schemas) | — | `extractor.py` (intégré avant affichage) | `logs_agents.guardrail_issues` |
| Audit Agent | `app/services/logs_agent_service.py` | — | — | `logs_agents` (enrichi : origin_context, target_entity, device_info) |
| CorrelationID | `main.py` (middleware log_requests renforcé) | `providers.tsx` (génération + header) | — | `logs_agents.correlation_id` |
