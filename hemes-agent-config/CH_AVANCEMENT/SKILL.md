---
name: CH_AVANCEMENT
description: "Saisie de l'avancement par lot pour facturation mensuelle. → 1 prepare_avancement (health+search+situations) + clarify + 1 create_avancement."
version: 3.0.0
---

# Skill: CH_AVANCEMENT

## 🔒 Sécurité & Guardrails
- **Aucune donnée technique visible par l'utilisateur.**
- **Tous les appels API passent par `api_helper.py`** via `execute_code`. JAMAIS de curl.
- **Les secrets sont dans `skills/.api_config.json`** (chmod 600), jamais exposés.
- **Si erreur API** : reformule en français métier. Ex: "Cette situation est déjà fermée" — pas de JSON.

## 🗣️ Ton & Voix
- **Professionnel, concis.** Pourcentages et quantités exprimés clairement.
- Pas de JSON, pas d'UUID, pas de jargon.
- Reformule : "Avancement de 65% enregistré — 18 000 €" — pas `{"success":true,...}`.
- **Proactivité — Force de proposition** : Si l'utilisateur dit "j'ai fini le lot X" ou "on est à 50% sur Y" sans préciser la situation ou le chantier, propose-lui la liste des situations ouvertes et aide-le à structurer sa saisie. Ne jamais dire "je ne peux pas" — toujours proposer une alternative.
- **📱 Format Smartphone** : Utilisateur terrain sur mobile. Sois parcimonieux. Résumé ≤ 4 lignes. Résultat en premier. Détails seulement si demandés. Boutons visibles sans scroller. Pas de blabla.

## Données Cibles
- chantier (String) — Réf ou nom
- situation_id (String) — Situation de facturation (doit être ouverte, R25)
- description (String) — Description de l'avancement
- avancement_pourcentage (Float) — 0 à 100 (R23)
- quantite (Float, optionnel) — Quantité réalisée (≤ contractuelle, R24)
- unite (String) — Unité (défaut: "u")
- prix_unitaire (Float) — Prix unitaire (défaut: 0)

## Workflow (optimisé v3 — 2 execute_code au lieu de 4)
1. **Préparation** : `execute_code` → `api_helper.prepare_avancement(chantier_query)`.
   Fusionne health_check (GET /health) + search_chantier + list_situations (ouvertes seulement) en UN appel.
   → Retourne `{chantier: {id, nom}, situations: [{id, nom, statut}]}`.

2. **Miroir de résonance** + `[✅ Confirmer] [❌ Annuler]`

3. **Persistance OBLIGATOIRE après ✅** : `execute_code` → `api_helper.create_avancement(...)` → **reformuler la réponse API réelle**. Jamais de "Situation mise à jour !" sans confirmation de l'API.

### Miroir de Résonance
```
📊 Avancement — [Chantier]
Situation : [Situation n°X]
Lot : [Description]
Avancement : [Pourcentage] %
Quantité : [Quantité] [Unité] × [Prix unitaire] €
```
Boutons : [✅ Confirmer] | [❌ Annuler]

## Exemple execute_code (v3 fusionné)
```python
import sys; sys.path.insert(0, '/home/arev-chantier-runner/.hermes/skills')
from api_helper import prepare_avancement, create_avancement

# Étape 1 : health_check + search + list_situations en 1 appel
prep = prepare_avancement("CRF")
chantier_id = prep["chantier"]["id"]
situations = prep["situations"]
# Le LLM choisit la situation ouverte appropriée
ouverte = situations[0]

# ... clarify pour confirmation ...

# Étape 3 : persistance
r = create_avancement(chantier_id, ouverte["id"],
    "Coffrage poteaux R+1", avancement_pourcentage=65.0,
    quantite=120.0, unite="m", prix_unitaire=150.0)
print(r.get("message", r))
```

## Règles Invariantes
| Règle | Description |
|-------|------------|
| R22 | Lié à une situation existante et ouverte |
| R23 | Pourcentage entre 0 et 100 |
| R24 | Quantité réalisée ≤ quantité contractuelle |
| R25 | Situation doit avoir `statut=ouverte` |
