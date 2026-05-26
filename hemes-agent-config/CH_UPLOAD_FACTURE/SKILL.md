# Skill: CH_UPLOAD_FACTURE
Description : Réceptionner une facture fournisseur (photo ou PDF), extraction OCR automatique via le backend, création facture brouillon puis dépense liée.

Déclencheur : Envoi d'une photo ou d'un PDF par l'utilisateur (pas sur un message texte).
Ne pas confondre avec CH_DEPENSES (saisie manuelle) — ici l'utilisateur envoie un fichier.

## Données Cibles (extraites par OCR backend)
- fournisseur (String) — Nom du fournisseur extrait
- montant_ttc (Float) — Montant TTC
- montant_ht (Float, optionnel) — Montant HT
- tva (Float, optionnel) — Montant TVA
- date_facture (String) — Date de la facture (YYYY-MM-DD)
- numero_facture (String) — Numéro de facture
- lignes (Array) — Lignes de détail (description, quantité, PU, total HT)
- chantier (String) — Réf ou nom du chantier

## Directives
- Dès réception d'une photo ou d'un PDF, active ce workflow CH_UPLOAD_FACTURE
- Télécharge le fichier depuis Telegram, puis appelle l'API backend pour OCR
- Affiche les données extraites à l'utilisateur dans le Miroir de Résonance
- Si l'OCR n'a pas pu extraire les données → indique à l'utilisateur et demande une nouvelle photo lisible
- Après confirmation, crée la dépense liée à la facture via POST /depenses avec invoice_id

### Miroir de Résonance
```
📄 Facture reçue et analysée :
- Fournisseur : [Fournisseur]
- Montant TTC : [Montant] €
- Date : [Date]
- N° facture : [Numéro]
- [N] lignes de détail
- Affectation : [Chantier]
```
Boutons : [✅ Confirmer et créer dépense] | [📸 Reprendre la photo] | [❌ Annuler]

## Persistance Backend

### Étape 1 — Envoyer le fichier pour OCR
POST /api/v1/tools/upload-facture
Content-Type: multipart/form-data
Header : `X-API-Key: <ta_clé>`

Champs du formulaire :
| Champ | Type | Requis | Description |
|---|---|---|---|
| `file` | binary (multipart) | ✅ | Fichier PDF, JPEG ou PNG |
| `org_id` | string (form) | ✅ | UUID de l'organisation |
| `chantier_id` | string (form) | ✅ | UUID du chantier (résolu) |

**Workflow :** Résous d'abord le chantier via POST /chantiers/search pour obtenir l'UUID.

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
  "error": "L'OCR n'a pas pu extraire les données...",
  "besoin_clarification": true
}
```
Si `besoin_clarification` est true, demande à l'utilisateur de renvoyer une photo plus lisible.

### Étape 2 — Créer la dépense liée (après ✅ Confirmer)
POST /api/v1/tools/depenses
Header : `X-API-Key: <ta_clé>`

Payload :
```json
{
  "org_id": "<uuid_org>",
  "chantier_id": "<uuid_chantier>",
  "description": "Facture FAC-2026-001 - SARL Bâti",
  "montant": 1250.00,
  "fournisseur": "SARL Bâti",
  "categorie": "fournisseur",
  "date_depense": "2026-05-26",
  "invoice_id": "<uuid_facture>"
}
```

Le champ `invoice_id` lie la dépense à la facture dans la DB. La dépense apparaîtra dans l'écran chantier.

## Règles Invariantes
| Règle | Description |
|-------|------------|
| R26 | L'OCR doit extraire : fournisseur, montant_ttc, date_facture, numero_facture |
| R27 | Si un champ obligatoire manque → demander à l'utilisateur |
| R28 | Le montant TTC extrait par OCR prime sur toute saisie manuelle |
| R29 | La facture est automatiquement liée au chantier courant |
| R30 | Après confirmation, une dépense est créée dans chantier_depenses liée à cette facture |
