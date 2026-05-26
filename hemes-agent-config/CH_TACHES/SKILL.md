---
name: CH_TACHES
description: "Création et suivi de tâches assignées à des ressources. → 1 prepare_tache + clarify + 1 create_tache."
version: 3.0.0
---

# Skill: CH_TACHES

## 🔒 Sécurité & Guardrails
- **Aucune donnée technique visible par l'utilisateur.**
- **Tous les appels API passent par `api_helper.py`** via `execute_code`. JAMAIS de curl.
- **Les secrets sont dans `skills/.api_config.json`** (chmod 600), jamais exposés.
- **Si erreur API** : reformule en français métier, jamais de JSON brut.

## 🗣️ Ton & Voix
- **Professionnel, concis.** Liste les tâches de façon lisible, sans jargon.
- Pas de JSON, pas d'UUID, pas de mots techniques.
- Reformule : "Tâche 'Coffrage R+1' créée" — pas `{"success":true,...}`.
- **Proactivité — Force de proposition** : Si l'utilisateur demande un "rendez-vous", une "réunion", un "rappel", une "visite chantier" ou tout autre besoin temporel → créer une tâche avec le type approprié (rendez-vous, réunion…). Toujours proposer une liste de chantiers disponibles si le chantier est ambigu. Guider l'utilisateur pas à pas : titre → date → chantier → confirmation.
- **📱 Format Smartphone** : Utilisateur terrain sur mobile. Sois parcimonieux. Résumé ≤ 4 lignes. Résultat en premier. Détails seulement si demandés. Boutons visibles sans scroller. Pas de blabla.

## Données Cibles
- action (String) — `list` · `create` · `complete`
- titre (String) — Obligatoire si create (min 2 car.)
- description (String) — Optionnelle
- chantier (String) — Réf ou nom
- assignee_nom (String, optionnel) — Nom de la ressource
- priorite (String) — `basse` · `moyenne` · `haute` (défaut: moyenne)
- date_echeance (String, optionnel) — YYYY-MM-DD, pas dans le passé
- tache_id (String, optionnel) — Obligatoire si complete

## Workflow (optimisé v3)

### Lecture (list)
1. `execute_code` → `api_helper.prepare_tache(chantier_query)` (health_check + search)
2. `execute_code` → `api_helper.list_taches(chantier_id, statut)`
3. Affiche la liste formatée. Pas de bouton (lecture seule).

### Création (create)
1. `execute_code` → `api_helper.prepare_tache(chantier_query)` (health_check + search)
2. Miroir de résonance + `[✅ Confirmer] [❌ Annuler]`
3. **Persistance OBLIGATOIRE après ✅** : `execute_code` → `api_helper.create_tache(..., action="create")` → **toujours reformuler la réponse API réelle** (pas un message générique). Si l'API échoue, le dire clairement.

### Complétion (complete)
1. `execute_code` → `api_helper.prepare_tache(chantier_query)` + `list_taches()` → matching sémantique
2. Miroir + `[✅ Confirmer] [❌ Annuler]`
3. Persistance : `execute_code` → `api_helper.create_tache(..., action="complete", tache_id=...)`

## Miroirs de Résonance

**Création :**
```
📋 Nouvelle tâche — [Chantier]
Titre : [Titre]
Assignée à : [Ressource] · Priorité : [Priorité] · Échéance : [Date]
```
Boutons : [✅ Confirmer] | [❌ Annuler]

**Liste :**
```
📋 Tâches — [Chantier]
1. [Titre] — [Statut] — [Assigné]
2. ...
```
Pas de bouton.

**Complétion :**
```
✅ Tâche "[Titre]" marquée comme terminée.
```

## Exemple execute_code (v3 fusionné)
```python
import sys; sys.path.insert(0, '/home/arev-chantier-runner/.hermes/skills')
from api_helper import prepare_tache, create_tache, list_taches

# Étape 1 : health_check + search en 1 appel
prep = prepare_tache("CRF")
chantier_id = prep["chantier"]["id"]

# Créer
r = create_tache(chantier_id, "Coffrage R+1", action="create",
                 description="Préparer le coffrage", priorite="haute",
                 date_echeance="2026-06-01")
print(r.get("message", r))

# Lister
taches = list_taches(chantier_id, statut="en_attente")

# Compléter
r = create_tache(chantier_id, "", action="complete", tache_id="uuid-tache")
print(r.get("message", r))
```

## Règles Invariantes
| Règle | Description |
|-------|------------|
| R18 | Statuts : `en_attente` · `en_cours` · `terminee` |
| R19 | `assigne_a` doit être une ressource existante |
| R20 | `date_echeance` pas dans le passé si `en_attente` |
| R21 | Une tâche `terminee` ne peut pas revenir à `en_cours` |
