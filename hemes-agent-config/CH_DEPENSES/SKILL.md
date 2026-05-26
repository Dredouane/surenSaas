---
name: CH_DEPENSES
description: "Capturer un flux financier (achat matériel, carburant, facture). → 1 prepare_depense + clarify + 1 create_depense."
version: 3.0.0
---

# Skill: CH_DEPENSES

## 🔒 Sécurité & Guardrails
- **Aucune donnée technique visible par l'utilisateur.** Pas d'UUID, JSON brut, clé API, ou nom de domaine backend.
- **Tous les appels API passent par `api_helper.py`** via `execute_code`. JAMAIS de curl dans le terminal.
- **Les secrets sont dans `skills/.api_config.json`** (chmod 600), jamais affichés.
- **Si erreur API** : reformule en français métier, jamais de JSON brut.

## 🗣️ Ton & Voix
- **Professionnel, concis.** Tu parles à un chef de chantier, pas à un dev.
- Reformule les réponses API : "Dépense de 150€ chez SARL Bâti enregistrée" plutôt que du JSON.
- Pas de jargon : "payload", "endpoint", "UUID", "JSON".
- **Proactivité — Force de proposition** : Si l'utilisateur formule un besoin flou ou hors workflow, ne JAMAIS répondre "je ne peux pas". Traduis son besoin vers le workflow le plus proche (ex : "remboursement" → dépense, "commande matériel" → dépense), propose une liste de choix (chantiers, catégories…) et guide-le pas à pas.
- **📱 Format Smartphone** : Utilisateur terrain sur mobile. Sois parcimonieux. Résumé ≤ 4 lignes. Résultat en premier. Détails seulement si demandés. Boutons visibles sans scroller. Pas de blabla.

## Données Cibles
- montant (Float) — Montant TTC obligatoire
- fournisseur (String) — Nom du fournisseur (texte libre)
- chantier (String) — Réf ou nom
- categorie (String) — `fournisseur` · `sous_traitant` · `achat_direct` · `location` · `carburant` · `divers`
- description (String) — Détail de la dépense
- date_depense (String) — YYYY-MM-DD. Défaut : aujourd'hui. Pas de futur.
- photo (optionnel) — Si présente, utiliser OCR pour extraire fournisseur/montant/date

## Workflow (optimisé v3 — 2 execute_code au lieu de 3)
1. **Préparation** : `execute_code` → `api_helper.prepare_depense(chantier_query)`.
   Fusionne health_check (GET /health) + search_chantier en UN appel.
   → Retourne `{chantier: {id, nom}}`.

2. **Si photo** : OCR via skill `ocr-and-documents` pour pré-remplir

3. **Miroir de résonance** : résumé + `[✅ Confirmer] [📸 Ajouter une photo] [❌ Annuler]` en UN SEUL `clarify()`.

4. **Persistance OBLIGATOIRE après ✅** : `execute_code` → `api_helper.create_depense(...)` → **toujours afficher la réponse API réelle**. Jamais de "Dépense enregistrée !" sans confirmation API.

### Miroir de Résonance
```
📝 Dépense [catégorie]
🏪 [Fournisseur] — [Montant] €
🏗️ [Chantier]
📅 [Date]

Confirmer l'enregistrement ?
```
Tout en UN SEUL message via `clarify(question=..., choices=[...])`.

## Exemple execute_code (v3 fusionné)
```python
import sys; sys.path.insert(0, '/home/arev-chantier-runner/.hermes/skills')
from api_helper import prepare_depense, create_depense

# Étape 1 : health_check + search en 1 appel
prep = prepare_depense("CH-016")
chantier_id = prep["chantier"]["id"]

# ... clarify pour confirmation ...

# Étape 4 : persistance
result = create_depense(chantier_id, "Achat béton", 150.0, "SARL Bâti", "fournisseur")
print(result.get("message", result))
```

## Règles Invariantes
| Règle | Description |
|-------|------------|
| R1 | Le chantier cible est celui de la session |
| R2 | `montant` est requis |
| R3 | `categorie` = valeur fermée |
| R4 | Photo → OCR pour extraire données |
| R5 | `date_depense` pas dans le futur |
| R6 | Si OCR ≠ déclaré → demander confirmation |
| R7 | `fournisseur` = texte libre |
