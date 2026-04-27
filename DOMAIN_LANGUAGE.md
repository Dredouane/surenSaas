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
| Situation | `chantiers.py` (endpoints `/situations`) | `SituationsTable.tsx` | — | `chantier_situations` |
| Réception | `chantiers.py` (endpoints `/receptions`) | `ReceptionsList.tsx` | `bot_construction_receptions.py` | `chantier_receptions` |
| Tâche | `chantiers.py` (endpoints `/taches`) | `TachesList.tsx` | `bot_construction_taches.py` | `chantier_taches` |
| Notification | `chantiers.py` (endpoints `/notifications`) | `NotificationsPanel.tsx` | Notification non automatisée | `chantier_notifications` |
| Ressource | `chantiers.py` (endpoints `/ressources`) | — | Pointages > liste ressources | `chantier_ressources` |
| Audit | — | `AuditTrail.tsx` | — | `chantier_audit_trail` |
| Indicateurs | — | `Indicateurs.tsx` | Workflow "📊 Indicateurs" | Vue calculée via `recalculer_metriques_chantier()` |

---

## Workflows Telegram — Machine d'État

| État | Déclencheur | Handler | Table concernée |
|------|-------------|---------|-----------------|
| `idle` | Menu principal / /start | `handle_start_command` | `telegram_users.last_state` |
| `op_awaiting_description` | Click "Signaler opération" | `handle_operation_media` | `chantier_operations_htl` |
| `op_awaiting_validation` | Saisie description opération | `handle_save_operation` | `chantier_operations_htl` |
| `depense_awaiting_description` | Click "Signaler dépense" | *(manquant — à implémenter)* | `chantier_depenses` |
| `depense_awaiting_validation` | Saisie description dépense | *(manquant — à implémenter)* | `chantier_depenses` |

**Règle :** Chaque workflow suit le pattern : `idle → await_X_description → await_X_validation → idle`

## Règles Strictes

1. **Toujours `statut`** en base, jamais `status`
2. **Toujours `chantier_id`** comme FK, jamais `site_id` ou `project_id`
3. **Toujours `org_id`** pour l'isolation multi-tenant
4. **Toujours qualifier "opération"** par `HITL` dans le code (`chantier_operations_htl`, `handle_operation_media`, etc.)
5. **Toujours utiliser les enums** DB (`chantier_statut`, `chantier_operation_type`, etc.) — pas de strings libres
6. **`.execute()` sur Supabase retourne une liste** dans `.data` — toujours accéder via `data[0]['col']` pas `data['col']`
