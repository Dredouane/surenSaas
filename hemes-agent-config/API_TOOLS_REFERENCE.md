# API Tools Reference — Endpoints REST pour SurenSaaS

> Document de référence pour l'agent Hermes (Arev_Chantiers_Assist).
> Tous les endpoints sont préfixés par `/api/v1/tools` et nécessitent le header `X-API-Key`.

URL de base : `https://test-surensaas-back-REDACTED-ew.a.run.app/api/v1/tools`

---

## Authentification

Chaque requête DOIT inclure le header :
```
X-API-Key: <ta_clé_api>
```
La clé est définie dans la variable d'environnement `TOOLS_API_KEY` du backend.

Si la clé est invalide ou absente, le backend retourne :
```json
{ "detail": "Clé API invalide" }
```
Statut HTTP : `403 Forbidden`

---

## 1. Dépenses — Création

### POST `/depenses`
Créer une dépense.

**Payload :**
| Champ | Type | Requis | Défaut | Description |
|---|---|---|---|---|
| `org_id` | string | ✅ | — | UUID de l'organisation |
| `chantier_id` | string | ✅ | — | UUID du chantier (résolu) |
| `description` | string | ✅ | — | Description de la dépense |
| `montant` | float | ❌ | 0.0 | Montant TTC |
| `fournisseur` | string | ❌ | "Telegram" | Nom du fournisseur |
| `categorie` | string | ❌ | "autre" | Voir types fermés ci-dessous |
| `date_depense` | string | ❌ | aujourd'hui | Format YYYY-MM-DD |
| `invoice_id` | string | ❌ | null | UUID de la facture liée (après upload OCR) |

**Catégories valides (fermées) :** `fournisseur`, `sous_traitant`, `achat_direct`, `location`, `carburant`, `divers`

**Exemple :**
```json
{
  "org_id": "uuid-org",
  "chantier_id": "uuid-chantier",
  "description": "Achat béton pour fondation",
  "montant": 150.0,
  "fournisseur": "SARL Bâti",
  "categorie": "fournisseur",
  "date_depense": "2026-05-21"
}
```

**Réponse succès :**
```json
{
  "success": true,
  "data": { "id": "uuid-depense" },
  "error": null,
  "suggestion": null,
  "message": "Dépense SARL Bâti - 150.0€ enregistrée (en attente validation)."
}
```

**Réponse erreur (date future) :**
```json
{
  "success": false,
  "data": null,
  "error": "Date 2026-05-30 dans le futur. Impossible d'enregistrer une dépense future.",
  "suggestion": "Utilise la date réelle de la dépense (passée ou aujourd'hui).",
  "message": null
}
```

---

## 2. Dépenses — Lecture

### GET `/chantiers/{chantier_id}/depenses?org_id={org_id}`
Lister les dépenses d'un chantier.

**Paramètres :**
| Champ | Type | Requis | Description |
|---|---|---|---|
| `chantier_id` | string (path) | ✅ | UUID du chantier |
| `org_id` | string (query) | ✅ | UUID de l'organisation |

**Exemple :**
```
GET /api/v1/tools/chantiers/<uuid>/depenses?org_id=<uuid>
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": "<uuid>",
      "chantier_id": "<uuid>",
      "org_id": "<uuid>",
      "fournisseur": "SARL Bâti",
      "montant": 150.0,
      "categorie": "fournisseur",
      "description": "Achat béton",
      "date": "2026-05-21",
      "status": "en_attente_validation"
    }
  ]
}
```

---

## 3. Opérations Terrain — Création

### POST `/operations`
Créer une opération terrain (HTL).

**Payload :**
| Champ | Type | Requis | Défaut | Description |
|---|---|---|---|---|
| `org_id` | string | ✅ | — | UUID de l'organisation |
| `chantier_id` | string | ✅ | — | UUID du chantier (résolu) |
| `description` | string | ✅ | — | Description (min 10 caractères) |
| `type` | string | ❌ | "autre" | Voir types fermés ci-dessous |
| `montant` | float | ❌ | null | Montant estimé |
| `quantite` | float | ❌ | null | Quantité |
| `unite` | string | ❌ | null | Unité de mesure |

**Types valides (fermés) :** `demolition`, `nettoyage`, `commande`, `livraison`, `reception`, `incident`, `autre`

**Exemple :**
```json
{
  "org_id": "uuid-org",
  "chantier_id": "uuid-chantier",
  "description": "Coffrage des poteaux R+1",
  "type": "autre"
}
```

**Réponse succès :**
```json
{
  "success": true,
  "data": {
    "id": "uuid-operation",
    "type": "autre",
    "description": "Coffrage des poteaux R+1",
    "date": "2026-05-23",
    "source": "manuel"
  },
  "error": null,
  "message": "Opération créée"
}
```

---

## 4. Opérations Terrain — Lecture

### GET `/chantiers/{chantier_id}/operations?org_id={org_id}&statut={statut}`
Lister les opérations d'un chantier. `statut` est optionnel.

**Exemple :**
```
GET /api/v1/tools/chantiers/<uuid>/operations?org_id=<uuid>
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": "<uuid>",
      "chantier_id": "<uuid>",
      "description": "Coffrage poteaux",
      "type": "autre",
      "date": "2026-05-23",
      "source": "manuel"
    }
  ]
}
```

---

## 5. Pointages — Upsert

### POST `/pointages/upsert`
Créer ou mettre à jour un pointage pour une date donnée.

**Payload :**
| Champ | Type | Requis | Description |
|---|---|---|---|
| `org_id` | string | ✅ | UUID de l'organisation |
| `chantier_id` | string | ✅ | UUID du chantier (résolu) |
| `date_pointage` | string | ✅ | Format YYYY-MM-DD |
| `ressources` | array | ✅ | Liste des présences |

**Structure d'une ressource :**
```json
{
  "ressource_id": "uuid-ressource",
  "present": true,
  "nom": "Jean Dupont"
}
```

**Exemple complet :**
```json
{
  "org_id": "uuid-org",
  "chantier_id": "uuid-chantier",
  "date_pointage": "2026-05-21",
  "ressources": [
    { "ressource_id": "uuid-res1", "present": true, "nom": "Jean Dupont" },
    { "ressource_id": "uuid-res2", "present": false, "nom": "Marie Martin" },
    { "ressource_id": "uuid-machine1", "present": true, "nom": "Pelleteuse 3t" }
  ]
}
```

**Réponse succès :**
```json
{
  "success": true,
  "data": { "pointage_id": "uuid", "ressources": [...] },
  "error": null,
  "message": "Pointage du 2026-05-21 mis à jour : 2 présent(s), 1 absent(s)."
}
```

**Réponse erreur (pointage verrouillé) :**
```json
{
  "success": false,
  "data": null,
  "error": "Pointage déjà en_attente_validation. Impossible de modifier.",
  "suggestion": "Contacte le gérant pour modifier un pointage validé.",
  "message": null
}
```

---

## 6. Pointages — Lecture

### GET `/chantiers/{chantier_id}/pointages?org_id={org_id}`
Lister les pointages d'un chantier.

```
GET /api/v1/tools/chantiers/<uuid>/pointages?org_id=<uuid>
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": "<uuid>",
      "date": "2026-05-21",
      "status": "brouillon",
      "chantier_id": "<uuid>"
    }
  ]
}
```

---

## 7. Ressources — Lecture

### GET `/chantiers/{chantier_id}/ressources?org_id={org_id}&type_ressource={type}`
Lister les ressources d'un chantier (personnel ou machines). `type_ressource` est optionnel (valeurs : `homme`, `machine`). Si aucune ressource n'est trouvée pour le chantier, l'API fait un fallback org-wide.

```
GET /api/v1/tools/chantiers/<uuid>/ressources?org_id=<uuid>&type_ressource=homme
GET /api/v1/tools/chantiers/<uuid>/ressources?org_id=<uuid>&type_ressource=machine
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    { "id": "<uuid>", "nom": "Jean Dupont", "type": "homme", "chantier_id": "<uuid>", "org_id": "<uuid>" },
    { "id": "<uuid>", "nom": "Marie Martin", "type": "homme", ... }
  ]
}
```

**Matching sémantique :** Une fois la liste récupérée, utilise ta capacité LLM pour faire le matching entre les noms donnés par l'utilisateur et les ressources listées (fautes d'orthographe, surnoms, variations).

---

## 8. Tâches — Création et Gestion

### POST `/taches`
Créer ou compléter une tâche.

**Payload :**
| Champ | Type | Requis | Défaut | Description |
|---|---|---|---|---|
| `org_id` | string | ✅ | — | UUID de l'organisation |
| `chantier_id` | string | ✅ | — | UUID du chantier (résolu) |
| `action` | string | ✅ | — | `create` ou `complete` |
| `titre` | string | ❌* | — | Titre (min 2 car., requis si create) |
| `description` | string | ❌ | "" | Description détaillée |
| `assignee_nom` | string | ❌ | null | Nom de la ressource assignée |
| `priorite` | string | ❌ | "moyenne" | `basse`, `moyenne`, `haute` |
| `date_echeance` | string | ❌ | null | Format YYYY-MM-DD, pas dans le passé (R20) |
| `tache_id` | string | ❌* | null | UUID de la tâche (requis si complete) |

**Exemple create :**
```json
{
  "org_id": "uuid-org",
  "chantier_id": "uuid-chantier",
  "action": "create",
  "titre": "Coffrage R+1",
  "description": "Préparer le coffrage des poteaux",
  "priorite": "haute",
  "date_echeance": "2026-06-01"
}
```

**Réponse succès create :**
```json
{
  "success": true,
  "data": { "id": "uuid", "titre": "Coffrage R+1", "statut": "en_attente" },
  "error": null,
  "message": "Tâche 'Coffrage R+1' créée"
}
```

**Exemple complete :**
```json
{
  "org_id": "uuid-org",
  "chantier_id": "uuid-chantier",
  "action": "complete",
  "tache_id": "uuid-tache"
}
```

**Réponse succès complete :**
```json
{
  "success": true,
  "data": { "id": "uuid" },
  "error": null,
  "message": "Tâche marquée comme terminée"
}
```

**Réponse erreur (déjà terminée) :**
```json
{
  "success": false,
  "data": null,
  "error": "Tâche déjà terminée, impossible de la repasser en cours (R21)"
}
```

### GET `/chantiers/{chantier_id}/taches?org_id={org_id}&statut={statut}`
Lister les tâches d'un chantier. `statut` est optionnel.

```
GET /api/v1/tools/chantiers/<uuid>/taches?org_id=<uuid>
GET /api/v1/tools/chantiers/<uuid>/taches?org_id=<uuid>&statut=en_attente
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": "<uuid>",
      "titre": "Coffrage R+1",
      "description": "Préparer le coffrage",
      "statut": "en_attente",
      "priorite": "haute",
      "assignee_nom": "Jean Dupont"
    }
  ]
}
```

---

## 9. Avancements — Création

### POST `/avancements`
Ajouter une ligne d'avancement sur une situation de facturation.

**Payload :**
| Champ | Type | Requis | Défaut | Description |
|---|---|---|---|---|
| `org_id` | string | ✅ | — | UUID de l'organisation |
| `chantier_id` | string | ✅ | — | UUID du chantier (résolu) |
| `situation_id` | string | ✅ | — | UUID de la situation (doit être ouverte, R25) |
| `description` | string | ✅ | — | Description de l'avancement |
| `avancement_pourcentage` | float | ❌ | 0.0 | Entre 0 et 100 (R23) |
| `quantite` | float | ❌ | null | Quantité réalisée (≤ contractuelle, R24) |
| `unite` | string | ❌ | "u" | Unité de mesure |
| `prix_unitaire` | float | ❌ | 0.0 | Prix unitaire |

**Exemple :**
```json
{
  "org_id": "uuid-org",
  "chantier_id": "uuid-chantier",
  "situation_id": "uuid-situation",
  "description": "Coffrage poteaux R+1",
  "avancement_pourcentage": 65.0,
  "quantite": 120.0,
  "unite": "m",
  "prix_unitaire": 150.0
}
```

**Réponse succès :**
```json
{
  "success": true,
  "data": { "id": "uuid", "avancement_pourcentage": 65.0, "montant_total": 18000.0 },
  "error": null,
  "message": "Avancement ajouté: 65.0%"
}
```

**Réponse erreur (situation fermée) :**
```json
{
  "success": false,
  "data": null,
  "error": "La situation doit être ouverte pour accepter des lignes d'avancement (R25)"
}
```

### GET `/chantiers/{chantier_id}/situations?org_id={org_id}`
Lister les situations de facturation (pour trouver une situation ouverte).

```
GET /api/v1/tools/chantiers/<uuid>/situations?org_id=<uuid>
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": "<uuid>",
      "numero": 1,
      "libelle": "Situation n°1",
      "montant": 50000.0,
      "statut": "ouverte",
      "periode_debut": "2026-05-01",
      "periode_fin": "2026-05-31"
    }
  ]
}
```

---

## 10. Upload Facture — OCR et Création

### POST `/upload-facture`
Envoyer une photo ou un PDF de facture pour extraction OCR automatique. Crée une facture brouillon en DB. Retourne les données structurées pour confirmation.

**Méthode :** `multipart/form-data`

| Champ | Type | Requis | Description |
|---|---|---|---|
| `file` | binary | ✅ | Fichier PDF, JPEG ou PNG |
| `org_id` | string | ✅ | UUID de l'organisation |
| `chantier_id` | string | ✅ | UUID du chantier (résolu) |

**Workflow :** Résous d'abord le chantier via `POST /chantiers/search`, puis envoie le fichier avec `curl -F`.

**Exemple curl :**
```
curl -X POST /api/v1/tools/upload-facture \
  -H "X-API-Key: <ta_clé>" \
  -F "file=@facture.pdf" \
  -F "org_id=<uuid>" \
  -F "chantier_id=<uuid>"
```

**Réponse succès :**
```json
{
  "success": true,
  "data": {
    "invoice_id": "uuid-facture",
    "supplier_name": "SARL Bâti",
    "amount_ttc": 1250.00,
    "amount_ht": 1041.67,
    "vat_amount": 208.33,
    "vat_rate": 20.0,
    "invoice_date": "2026-05-26",
    "invoice_number": "FAC-2026-001",
    "description": "Fourniture de béton prêt à l'emploi",
    "line_items": [
      { "description": "Béton C25/30", "quantity": 6.0, "unit_price": 90.0, "total_ht": 540.0 },
      { "description": "Acier HA16", "quantity": 500.0, "unit_price": 0.85, "total_ht": 425.0 }
    ],
    "chantier_id": "uuid-chantier"
  },
  "error": null,
  "message": "Facture SARL Bâti - 1250.00€ extraite et enregistrée (brouillon). Confirme pour créer la dépense."
}
```

**Réponse échec OCR :**
```json
{
  "success": false,
  "data": null,
  "error": "L'OCR n'a pas pu extraire les données de cette facture. Vérifie que l'image est lisible.",
  "besoin_clarification": true
}
```

### Après confirmation → Créer la dépense liée
Utilise `POST /depenses` avec `invoice_id` :
```json
{
  "org_id": "<uuid>",
  "chantier_id": "<uuid>",
  "description": "Facture FAC-2026-001 - SARL Bâti",
  "montant": 1250.00,
  "fournisseur": "SARL Bâti",
  "categorie": "fournisseur",
  "date_depense": "2026-05-26",
  "invoice_id": "<uuid_facture>"
}
```
La dépense apparaîtra dans l'écran chantier avec un lien vers la facture.

---

## 11. Chantiers — Recherche

### POST `/chantiers/search`
Rechercher un chantier par référence ou nom (ILIKE).

**Payload :**
| Champ | Type | Requis | Description |
|---|---|---|---|
| `org_id` | string | ✅ | UUID de l'organisation |
| `query` | string | ✅ | Réf (CH-016) ou nom partiel. Minimum 2 caractères. |

**Exemple :**
```json
{
  "org_id": "uuid-org",
  "query": "CH-016"
}
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-chantier",
      "ref": "CH-016",
      "nom": "Résidence Les Jardins",
      "statut": "en_cours"
    }
  ],
  "error": null,
  "message": "1 chantier(s) trouvé(s) pour 'CH-016'."
}
```

### POST `/chantiers/list`
Lister les chantiers d'une organisation.

**Payload :**
| Champ | Type | Requis | Défaut | Description |
|---|---|---|---|---|
| `org_id` | string | ✅ | — | UUID de l'organisation |
| `statut` | string | ❌ | null | Filtrer par statut (`en_cours`, `termine`, etc.) |

**Exemple :**
```json
{
  "org_id": "uuid-org",
  "statut": "en_cours"
}
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    { "id": "uuid-1", "ref": "CH-016", "nom": "Résidence Les Jardins", "statut": "en_cours" },
    { "id": "uuid-2", "ref": "CH-014", "nom": "Bureaux EcoParc", "statut": "en_cours" }
  ],
  "error": null
}
```

---

## Récapitulatif des Workflows et Endpoints

| Workflow | SKILL.md | Endpoints |
|---|---|---|
| Dépense | `CH_DEPENSES/SKILL.md` | `POST /depenses` (avec ou sans `invoice_id`), `GET /chantiers/{id}/depenses` |
| Opération Terrain | `CH_OP_TERRAIN/SKILL.md` | `POST /operations`, `GET /chantiers/{id}/operations` |
| Pointage | `CH_POINTAGE/SKILL.md` | `POST /pointages/upsert`, `GET /chantiers/{id}/pointages`, `GET /chantiers/{id}/ressources` |
| Tâche | `CH_TACHES/SKILL.md` | `POST /taches` (create/complete), `GET /chantiers/{id}/taches` |
| Avancement | `CH_AVANCEMENT/SKILL.md` | `POST /avancements`, `GET /chantiers/{id}/situations` |
| Upload Facture | `CH_UPLOAD_FACTURE/SKILL.md` | `POST /upload-facture` (multipart OCR), `POST /depenses` (avec invoice_id) |
| Chantiers | — | `POST /chantiers/search`, `POST /chantiers/list` |

## Workflow Type : Résolution de chantier avant création

Pour tous les endpoints qui utilisent `chantier_id`, suis ce workflow :
1. L'utilisateur donne une référence (ex: "CH-016", "CRF", "Bureaux")
2. Appelle `POST /chantiers/search` avec la référence
3. Extrais l'`id` (UUID) du premier résultat
4. Utilise cet UUID comme `chantier_id` dans l'appel de création

**Ne passe jamais une référence brute (CH-016) comme chantier_id** — l'API attend un UUID.
