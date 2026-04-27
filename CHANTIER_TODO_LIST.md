# TODO — Module Chantier

Generated: 2026-04-27
Skills appliqués : `grill-me.md`, `ubiquitous-language.md`, `tdd-cycle.md`, `deep-modules.md`

---

## 🔴 PHASE 1 — Pointages

### CHA-001: Bug colonne `status` → `statut` dans le bot
**Fichier**: `surenSaasBack/app/api/bot_construction_pointages.py:136`
**Desc**: Le bot met à jour `status` qui n'existe pas dans la DB. La colonne s'appelle `statut`. L'UPDATE échoue silencieusement.
**Action**: Remplacer `{"status": "en_attente_validation"}` par `{"statut": "en_attente_validation"}`.
**Test**: Écrire un test qui appelle l'UPDATE et vérifie que `statut` est modifié.

### CHA-002: `chantier_context.py` avale toutes les exceptions
**Fichier**: `surenSaasBack/app/services/chantier_context.py:23-24,48-49`
**Desc**: `except Exception: return None` masque les erreurs réseau/Supabase. Impossible de debugger.
**Action**: Logger l'exception avant de return None, ou laisser remonter selon le contexte.
**Test**: Écrire un test avec un mock Supabase qui échoue et vérifier que l'erreur est loggée.

### CHA-003: Callbacks orphelins `pointage:present` / `pointage:absent`
**Fichier**: `surenSaasBack/app/api/construction_menu.py:298-299`
**Desc**: Deux callbacks enregistrés dans `CALLBACK_ROUTES` mais aucun handler correspondant. La logique réelle utilise un mécanisme de toggle (`pt:t:`).
**Action**: Supprimer les entrées inutilisées du dictionnaire `CALLBACK_ROUTES`.
**Test**: Vérifier que les callbacks supprimés ne sont référencés nulle part ailleurs.

### CHA-004: `handleRefresh` → `fetchChantierComplet()` inexistant
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/page.tsx:111`
**Desc**: `handleRefresh` appelle `fetchChantierComplet(o)` qui n'est jamais définie. Crash navigateur garanti.
**Action**: Implémenter `fetchChantierComplet` ou remplacer par un appel API réel, ou supprimer l'appel si non nécessaire.
**Test**: Test fonctionnel : cliquer sur un élément qui déclenche `handleRefresh` → pas d'erreur console.

### CHA-005: `PointagesList` ignore la prop `pointages`
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/components/PointagesList.tsx:36`
**Desc**: L'interface `PointagesListProps` déclare `pointages: Pointage[]` mais le composant ne le destructure pas et gère son propre state local. La prop est ignorée.
**Action**: Soit utiliser la prop si fournie, soit la supprimer de l'interface pour éviter toute confusion.
**Test**: Vérifier que le rendu est correct avec et sans la prop `pointages`.

---

## 🟡 PHASE 2 — Opérations HITL

### CHA-006: `OperationsList.tsx` est un stub minimal
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/components/OperationsList.tsx:92-100`
**Desc**: Le composant affiche uniquement `{description} - {statut}` sans aucun filtre, détail, action. Inexploitable pour un gérant.
**Action**: Compléter avec : filtres par type/source/statut, vue détail par opération, couleurs par statut.
**Test**: Rendu avec jeu de données → chaque colonne affichée correctement.

### CHA-007: Validation manager après création d'opération (workflow bot incomplet)
**Fichier**: `surenSaasBack/app/api/bot_construction_operations.py`
**Desc**: Une fois l'opération créée via le workflow état-machine (`op_awaiting_description` → `op_awaiting_validation` → sauvegarde), aucune notification n'est envoyée au gérant pour validation.
**Action**: Ajouter une étape de notification au gérant (via Telegram ou notification chantier) après `handle_save_operation()`.
**Test**: Simuler une création d'opération → vérifier qu'une notification est créée dans `chantier_notifications`.

### CHA-008: Imports lazy circulaires dans les fichiers bot
**Fichiers**: `bot_construction_operations.py`, `bot_construction_depenses.py`, `bot_construction_taches.py`, `bot_construction_receptions.py`
**Desc**: Chaque fichier importe `_handle_chantier_list` de façon lazy (dans le corps d'une fonction) pour contourner une dépendance circulaire.
**Action**: Refactorer pour éliminer la dépendance circulaire (extraire la fonction dans un module partagé ou restructurer les imports).
**Test**: L'import direct (non lazy) fonctionne sans erreur.

---

## 🟡 PHASE 3 — Tâches

### CHA-009: Revue Kanban + transitions de statut
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/components/TachesList.tsx`
**Desc**: Le Kanban (4 colonnes : en_attente, en_cours, terminee, annulee) + table view. Vérifier que les transitions de statut sont correctement propagées à l'API.
**Action**: Vérifier que chaque drag/click de transition envoie bien le bon `statut` via PUT, et que le bot `handle_complete_task()` fait la même chose.
**Test**: Créer une tâche → changer statut → vérifier en base.

### CHA-010: Création tâche depuis le bot sans chantier actif
**Fichier**: `surenSaasBack/app/api/bot_construction_taches.py`
**Desc**: Si l'utilisateur n'a pas de `last_chantier_id` (aucun chantier sélectionné), le comportement est indéfini.
**Action**: Ajouter une vérification en début de handler et demander à l'utilisateur de sélectionner un chantier.
**Test**: Déclencher le handler sans chantier sélectionné → message "Veuillez d'abord sélectionner un chantier".

---

## 🟡 PHASE 4 — Réceptions

### CHA-011: Callback `rec:add_point` — vérification implémentation
**Fichier**: `surenSaasBack/app/api/bot_construction_receptions.py`
**Desc**: Le callback `rec:add_point` existe mais son implémentation doit être vérifiée : est-ce un simple ajout de note ou un workflow complet ?
**Action**: Tester le callback et documenter/compléter le comportement.
**Test**: Envoyer le callback → vérifier la réponse et la persistance.

---

## 🟡 PHASE 5 — Dépenses

### CHA-012: Fonction `handle_list_depenses` dupliquée
**Fichier**: `surenSaasBack/app/api/bot_construction_depenses.py:32 et :46`
**Desc**: La même fonction est définie deux fois. La seconde écrase la première.
**Action**: Supprimer la première définition (lignes 32-44).
**Test**: Vérifier qu'il n'y a pas de `def handle_list_depenses` en double après correction.

### CHA-013: Instance `workflow` en double
**Fichier**: `surenSaasBack/app/api/bot_construction_depenses.py:15-19 et :26`
**Desc**: `BaseTelegramWorkflow(...)` est instancié deux fois avec les mêmes paramètres.
**Action**: Supprimer la première instanciation (lignes 15-19).
**Test**: Vérifier qu'une seule instance est créée.

### CHA-014: `DepensesTable.tsx` utilise `prompt()` pour la création
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/components/DepensesTable.tsx:140-147`
**Desc**: La création de dépense utilise `window.prompt()` — expérience utilisateur dégradée.
**Action**: Remplacer par un formulaire dialog standard (shadcn/ui Dialog + Form) avec catégorie, montant, description, date.
**Test**: Ouvrir le dialog de création → soumettre → vérifier que les données sont envoyées à l'API.

---

## 🟡 PHASE 6 — Notifications

### CHA-015: Notifications avec IDs dupliqués dans les données mock
**Fichier**: `surenSaasFront/lib/chantier-data-extended.ts`
**Desc**: Les notifications `notif-002`, `notif-003`, `notif-004`, `notif-005` apparaissent chacune deux fois → clés React dupliquées.
**Action**: Supprimer les entrées en double. Remplacer les IDs par des UUIDs uniques.
**Test**: Afficher le panneau de notifications → pas de warning React `duplicate key`.

### CHA-016: Nom du bot en dur
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/components/NotificationsPanel.tsx`
**Desc**: `bot: @SurenSaasBot` est écrit en dur dans le template.
**Action**: Rendre configurable via une prop `botUsername` ou depuis la config de l'org.
**Test**: Rendre avec un `botUsername` différent → le texte affiché change.

### CHA-017: Notification automatique au gérant après création d'opération
**Fichier**: `surenSaasBack/app/api/bot_construction_operations.py` (post-save hook)
**Desc**: Une étape du workflow bot opération manquante : prévenir le gérant qu'une nouvelle opération est en attente de validation.
**Action**: Après `handle_save_operation()`, créer une entrée dans `chantier_notifications` avec `type='validation'`, destinée au gérant.
**Test**: Créer une opération → vérifier qu'une notification de type `validation` est créée.

---

## 🟡 PHASE 7 — Indicateurs / Audit / Infos

### CHA-018: Seuils des indicateurs en dur
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/components/Indicateurs.tsx`
**Desc**: Marge cible (25%) et ratio dépenses (75%) sont hardcodés.
**Action**: Rendre configurables depuis le chantier ou la config de l'org.
**Test**: Modifier le seuil → l'affichage se met à jour.

### CHA-019: Pas d'audit trail affiché pour les sub-resources
**Fichier**: `surenSaasFront/app/dashboard/chantiers/[id]/page.tsx` (onglet Audit)
**Desc**: L'audit trail est auto-généré par trigger SQL mais rien ne garantit qu'il est correctement fetch et affiché.
**Action**: Vérifier que l'endpoint GET `/audit` existe et que le composant l'utilise.
**Test**: Faire une modification sur un chantier → vérifier l'entrée audit dans le composant.

---

## 🔴 BUGS TRANSVERSAUX (à traiter avant ou en parallèle)

### CHA-T-001: `chantier_data.ts` — mock data sans API
**Fichier**: `surenSaasFront/lib/chantier-data.ts`, `chantier-data-extended.ts`
**Desc**: Toutes les fonctions CRUD (`createTache`, `createPointagesJour`, etc.) manipulent uniquement de la mémoire locale avec `console.log`. Aucune persistance réelle.
**Action**: Remplacer chaque fonction mock par son appel API correspondant (`fetch()` vers `/api/v1/chantiers/...`).
**Test**: Chaque opération CRUD → vérifier que l'appel API est émis avec les bons paramètres.

### CHA-T-002: `test_chantiers_crud_fix.py` non fonctionnel
**Fichier**: `surenSaasBack/tests/test_chantiers_crud_fix.py`
**Desc**: Le fichier ne contient aucun test réel (uniquement import + print).
**Action**: Soit implémenter les tests, soit supprimer le fichier.

### CHA-T-003: `recalculer_metriques_chantier()` jamais appelable depuis Python
**Desc**: La fonction existe en SQL et est déclenchée par triggers sur `chantier_situations` et `chantier_depenses`. Aucun endpoint API ni appel Python ne permet de la déclencher manuellement.
**Action**: Créer un endpoint `POST /chantiers/{id}/recalculer` qui appelle la fonction via `supabase.rpc()`.
**Test**: Appeler l'endpoint → vérifier que les métriques sont mises à jour.

---

## Légende

| Priorité | Délai | Signification |
|---|---|---|
| 🔴 PHASE 1 | En premier | Bugs bloquants, plantages, incohérences DB |
| 🟡 PHASE 2-7 | Séquentiel | Par sous-domaine, du plus critique au moins critique |
| 🔴 TRANSVERSE | En parallèle | Problèmes qui touchent toute la feature |

Format :
```
### ID: Titre court
**Fichier**: chemin
**Desc**: 1-2 phrases
**Action**: 1 phrase
**Test**: 1 phrase décrivant le test de validation
```
