# Plan de Migration — VOIE A → VOIE B (LangGraph)

> Objectif : Remplacer les handlers séquentiels (menus boutons + état DB) par l'agent LangGraph tout en réutilisant le code métier existant comme tools internes.

---

## Principe Général

Chaque workflow VOIE A contient :
- Un **orchestrateur** (callbacks + set_state/get_state) → **remplacé par LangGraph**
- Une **extraction IA** (WorkflowExtractor → GeminiClient) → **remplacé par le LLM agent lui-même**
- Des **opérations DB** (insert/update dans les tables métier) → **réutilisées comme tools LangGraph**

---

## Phase 1 : Workflow Dépense (PRIORITAIRE)

### Ce qu'il faut migrer

**Fichiers VOIE A :**
- `app/api/bot_construction_depenses.py` (handle_depense_create, handle_depense_type_selected, handle_depense_media, handle_save_depense)
- `app/services/telegram/chantier_context.py` (set_state/get_state — la machine à états)
- La logique d'extraction via `extract_depense()` dans le fichier dédié

**Cible VOIE B :**
- Tool LangGraph `create_depense` (existe déjà dans le graph actuel — à vérifier/réécrire)
- Le LLM détecte l'intention "dépense" et extrait lui-même les champs via Gemini
- Les règles métier R1 à R7 (WORKFLOWS.md) sont dans le prompt système / pre_reflector

### Étapes

| # | Tâche | Durée estimée | Dépend de |
|---|-------|---------------|-----------|
| 1 | Extraire la fonction `insert_depense()` du handler VOIE A comme tool LangGraph pur | 1h | — |
| 2 | Ajouter la validation des règles R1-R7 dans `pre_reflector` ou prompt système | 1h | #1 |
| 3 | Créer un test E2E "Nouvelle dépense" via le pipeline LangGraph (pas VOIE A) | 2h | #2 |
| 4 | Vérifier que le HITL#1 s'interrompt avant l'écriture DB | 30min | #3 |
| 5 | Désactiver le callback `depense:create` dans `bot_construction_commands.py` | 15min | #4 |

### Critères de succès
- [ ] Un user peut envoyer "150€ pour le béton chez SARL Bâti" → le LLM propose un résumé → ✅ Envoyer → écriture DB
- [ ] Les règles R2 (montant requis) et R5 (pas de date future) sont appliquées
- [ ] Si photo jointe, l'OCR extrait les champs et le LLM les fusionne avec le texte
- [ ] Le test E2E existant (`test_scenarios.py::scenario_depense`) passe toujours

---

## Phase 2 : Workflow Pointage (PRIORITAIRE)

### Ce qu'il faut migrer

**Fichiers VOIE A :**
- `app/api/bot_construction_pointages.py` (handle_list_human, handle_list_machine, handle_toggle_presence, handle_validate_pointage)
- `app/api/bot_construction_commands.py` (les callbacks pointage:list, pointage:validate)

**Cible VOIE B :**
- Tool LangGraph `manage_attendance` (existe déjà — à vérifier)
- Le LLM gère la navigation "pointage humain/machine", la pagination, le toggle présence
- La validation se fait par HITL#1 (pas de bouton "Valider" legacy)

### Étapes

| # | Tâche | Durée estimée | Dépend de |
|---|-------|---------------|-----------|
| 1 | Wrapper `_get_pointage_for_date()` et `_toggle_presence()` en tools LangGraph | 1h | — |
| 2 | Implémenter la logique de pagination (liste ressources 5 par page) dans le LLM | 1h30 | #1 |
| 3 | Ajouter les règles R8-R13 (pas de date future, unicité, pas de toggle après validation) | 30min | #2 |
| 4 | Test E2E "Pointage quotidien" via LangGraph | 2h | #3 |
| 5 | Désactiver les callbacks pointage dans `bot_construction_commands.py` | 15min | #4 |

### Critères de succès
- [ ] User peut dire "pointage du jour" → le LLM liste les ressources avec leur statut
- [ ] User peut toggler présence pour une ressource
- [ ] "✅ Envoyer" → écriture DB statut=en_attente_validation
- [ ] Impossible de modifier après validation

---

## Phase 3 : Workflow Opération Terrain

### Ce qu'il faut migrer
- `app/api/bot_construction_operations.py` (handle_create_operation, handle_operation_media, handle_save_operation)
- Tool LangGraph `create_operation` (existe déjà — à vérifier)

### Règles métier à implémenter dans le prompt : R14-R17

---

## Phase 4 : Workflow Tâche

### Ce qu'il faut migrer
- `app/api/bot_construction_taches.py` (handle_list_taches, handle_validate_tache)
- Tool LangGraph `manage_tasks` (existe déjà — à vérifier)

### Règles métier : R18-R21

---

## Phase 5 : Workflow Avancement

### Ce qu'il faut migrer
- `app/api/bot_construction_avancements.py` (saisie d'avancement, calcul des montants)
- Tool LangGraph `report_progress` (existe déjà — à vérifier)

### Règles métier : R22-R25

---

## Phase 6 : Upload Facture Fournisseur (le plus complexe)

### Ce qui change fondamentalement
- VOIE A : OCR → extraction → proposition → validation (séquentiel rigide)
- VOIE B : LLM reçoit la photo → détecte "facture" → extrait → détecte champs manquants → demande au user → fusionne → propose

### Règles métier : R26-R30

---

## Risques & Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| LangGraph trop lent pour l'OCR | Faible | Fort | Tests E2E de performance avant déploiement |
| LLM n'extrait pas correctement les données | Moyen | Fort | HITL#1 comme filet de sécurité |
| Rétrocompatibilité avec les données existantes | Faible | Moyen | Migration des statuts `brouillon` → `en_attente_validation` |
| Le code VOIE A n'est pas réutilisable comme tool | Moyen | Moyen | Refactor partiel ou recréation du tool |
| Le LLM confond deux workflows (ex: dépense vs opération) | Faible | Moyen | Prompt système + classifier en amont |

---

## Timeline Estimée

```
Semaine 1 : Phase 1 (Dépense) + Phase 2 (Pointage) — les 2 piliers
Semaine 2 : Phase 3 (Opération) + Phase 4 (Tâche)
Semaine 3 : Phase 5 (Avancement) + Phase 6 (OCR Facture)
Semaine 4 : Tests E2E complets, rollback des boutons VOIE A, déploiement
```
