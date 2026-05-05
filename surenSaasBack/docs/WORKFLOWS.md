# Workflows Métier — Bot Telegram Agentic SurenSaaS

> Document de référence pour Hermes (Louki) et Pi.
> Chaque workflow décrit : concept métier, règles invariantes, cycle HITL, tables DB.

---

## Architecture Générale — VOIE B (LangGraph)

```
User envoie message (texte/voice/photo/PDF)
        │
        ▼
  [classifier] ─── voice → audio_expert (Whisper)
         │         image → vision_expert (Gemini Vision)
         │         PDF  → document_extractor (Gemini OCR)
         │
         ▼
  [agent Gemini 2.5 Flash]
    ├─ 1. DÉTECTE le chantier (fuzzy match sur "en cours" du user)
    ├─ 2. DÉTECTE le sous-domaine (dépense, pointage, tâche…)
    ├─ 3. EXTRAIT les raw data → structure cible
    ├─ 4. VALIDE les règles métier (invariants ci-dessous)
    ├─ 5. SI OK → propose résumé + boutons [✅ Envoyer] [➕ Ajouter] [❌ Annuler]
    └─ 6. SI KO → demande précisions (champ manquant, format invalide…)

         ▼
  Session d'input (accumulation en mémoire LangGraph)
    └─ Chaque nouvel input → re-valide tout le cumul → nouveau résumé → mêmes boutons
         │
         ▼
  User clique [✅ Envoyer] (HITL#1)
         │
         ▼
  Écriture DB → statut = en_attente_validation
         │
         ▼
  HITL#2 (gérant, plus tard via app web) → statut = validé ou rejete
```

---

## Modèle de Données — Statuts Normalisés

Toutes les tables métier (chantier_depenses, chantier_pointages, chantier_taches, chantier_situation_lignes, chantier_operations_htl, invoices) supportent ces statuts :

| Statut | Description | Qui |
|--------|-------------|-----|
| `brouillon` | Données en cours, session ouverte (optionnel — peut rester en mémoire LangGraph) | LLM |
| `en_attente_validation` | Données complètes, HITL#1 passé, en attente du gérant | User terrain |
| `valide` | Gestionnaire a vérifié et approuvé | Gérant (HITL#2) |
| `rejete` | Gestionnaire a refusé, motif obligatoire (`motif_rejet` text) | Gérant (HITL#2) |

---

## Workflow #1 : Dépense (Achat / Paiement)

### Concept métier
Enregistrement d'une dépense liée à un chantier : achat fournisseur, sous-traitance, petit matériel. Peut inclure une photo du ticket/ facture pour OCR.

### Déclencheur
Message texte du user contenant une intention dépense OU photo/PDF d'une facture.

### Règles invariantes (agent DOIT les respecter)

| # | Règle | Pourquoi |
|---|-------|----------|
| R1 | Le chantier cible est forcément le chantier courant de la session | Cohérence, pas de multi-chantier |
| R2 | `montant_ht` ou `montant_ttc` est requis (au moins un des deux) | Sinon impossible à comptabiliser |
| R3 | Le `type` doit être une catégorie existante : `fournisseur`, `sous_traitant`, `achat_direct`, `location`, `carburant`, `divers` | Catégories fermées |
| R4 | Si photo/PDF fourni(e) → l'OCR doit extraire au moins : fournisseur, montant_ttc, date | Facture valide minimale |
| R5 | Une dépense ne peut pas être datée dans le futur | Cohérence comptable |
| R6 | Si le `montant_ttc` extrait par OCR est différent du `montant_ttc` déclaré par le user → demander confirmation | Détection d'erreur OCR |
| R7 | `fournisseur` peut être libre (texte) — pas de référencenel fermé | Flexibilité terrain |

### Tables DB
- `chantier_depenses` (id, chantier_id, org_id, fournisseur, montant_ht, montant_ttc, type, statut, motif_rejet, date_depense, created_at, updated_at)
- Pièces jointes : stockage GCS / Supabase Storage, référence dans `chantier_depenses.piece_url`

### Cycle HITL
```
User "J'ai payé 150€ à SARL Bâti pour le béton"
→ LLM extrait : chantier_courant, type=fournisseur, montant_ttc=150, fournisseur=SARL Bâti
→ Résumé : "Dépense fournisseur : SARL Bâti - 150€ TTC (béton) sur CH-016."
→ Boutons : [✅ Envoyer] [➕ Ajouter] [❌ Annuler]

Si user envoie photo du ticket → OCR extrait montant → résumé mis à jour avec les deux sources
→ User clique ✅ → écriture DB statut=en_attente_validation
```

---

## Workflow #2 : Pointage (Présence Ressources)

### Concept métier
Relevé de présence quotidien des ressources humaines et/ou machines sur le chantier.

### Déclencheur
Message texto du type "pointage du jour", "présence", ou sélection via menu.

### Règles invariantes

| # | Règle | Pourquoi |
|---|-------|----------|
| R8 | Un pointage est toujours lié à une **date** (la date du jour par défaut) | Quotidien obligatoire |
| R9 | Un pointage ne peut pas être dans le futur | Impossible de pointer demain |
| R10 | Seules les ressources appartenant à l'orga du chantier sont listables | Cohérence org |
| R11 | Le pointage peut être "humain" (type=homme) ou "machine" | Distinction comptable |
| R12 | Une fois `statut=en_attente_validation`, les présences sont verrouillées (plus de toggle) | Audit trail |
| R13 | Une même ressource ne peut avoir qu'une entrée par pointage (unicité pointage_id + ressource_id) | État binaire présence/absence |

### Tables DB
- `chantier_pointages` (id, chantier_id, org_id, date, statut, motif_rejet, commentaires)
- `chantier_pointage_ressources` (id, pointage_id, ressource_id, presence, periode)
- `chantier_ressources` (id, org_id, nom, type)

---

## Workflow #3 : Opération Terrain (HTL — Hors Travaux Lourds)

### Concept métier
Remontée d'une opération ou incident sur le chantier : démolition, nettoyage, commande, livraison, etc.

### Déclencheur
Message texte ou photo décrivant une opération en cours ou terminée.

### Règles invariantes

| # | Règle | Pourquoi |
|---|-------|----------|
| R14 | Le `type_operation` est une valeur fermée : `demolition`, `nettoyage`, `commande`, `livraison`, `reception`, `incident`, `autre` | Catégorisation métier |
| R15 | Si `type=incident`, une description détaillée et au moins une photo sont obligatoires | Sérieux requis |
| R16 | L'opération peut être liée à zéro ou une tâche existante | Lien optionnel |
| R17 | Le compte-rendu textuel est libre mais doit être ≥10 caractères | Éviter les vides |

### Tables DB
- `chantier_operations_htl` (id, chantier_id, org_id, type_operation, description, tache_id?, statut, motif_rejet, created_at)

---

## Workflow #4 : Tâche

### Concept métier
Création et suivi de tâches assignées à des ressources sur le chantier.

### Déclencheur
Message texte demandant de créer, lister ou clôturer une tâche.

### Règles invariantes

| # | Règle | Pourquoi |
|---|-------|----------|
| R18 | Une tâche a un `statut`: `a_faire`, `en_cours`, `terminee`, `annulee` | Cycle de vie |
| R19 | `assigne_a` doit être une ressource existante dans `chantier_ressources` (type=homme) | Traçabilité |
| R20 | La `date_echeance` ne peut pas être dans le passé si `statut=a_faire` | Planification |
| R21 | Une tâche `terminee` ne peut pas repasser à `en_cours` | Irréversible |

### Tables DB
- `chantier_taches` (id, chantier_id, org_id, titre, description, assigne_a, date_echeance, statut, created_at)

---

## Workflow #5 : Avancement (Situation de Facturation)

### Concept métier
Saisie de l'avancement par lot de prix unitaire pour établir une situation de facturation mensuelle.

### Déclencheur
Message texte indiquant un pourcentage d'avancement ou une quantité réalisée.

### Règles invariantes

| # | Règle | Pourquoi |
|---|-------|----------|
| R22 | L'avancement est lié à une `situation` (situation de facturation) existante et ouverte | Structure comptable |
| R23 | `pourcentage <= 100` et `pourcentage >= 0` | Physique |
| R24 | `quantite_realisee <= quantite_contractuelle` du lot | Pas de dépassement sans avenant |
| R25 | La `situation` de facturation doit avoir `statut=ouverte` pour accepter des lignes | Workflow facturation |

### Tables DB
- `chantier_situations` (id, chantier_id, org_id, mois, statut, montant_total)
- `chantier_situation_lignes` (id, situation_id, lot_id, quantite_realisee, pourcentage, montant, statut)

---

## Workflow #6 : Upload Facture Fournisseur (OCR)

### Concept métier
Un conducteur prend en photo ou envoie un PDF de facture fournisseur. Le LLM extrait les données via OCR, les structure, et crée une facture "brouillon" qu'il propose au user avant validation.

### Déclencheur
Envoi d'une photo ou d'un PDF (pas d'intention texte explicite).

### Règles invariantes

| # | Règle | Pourquoi |
|---|-------|----------|
| R26 | L'OCR doit extraire : `fournisseur`, `montant_ttc`, `date_facture`, `numero_facture` | Champs obligatoires |
| R27 | Si un champ obligatoire manque → demander au user de le fournir OU de reprendre la photo | Pas d'écriture partielle |
| R28 | Le `montant_ttc` extrait par OCR prime sur tout montant saisi manuellement | Source de vérité |
| R29 | La facture créée est automatiquement liée au chantier courant | Session active |
| R30 | Après validation HITL#1, une dépense est automatiquement créée dans `chantier_depenses` liée à cette facture | Cohérence comptable |

### Tables DB
- `invoices` (id, chantier_id, org_id, fournisseur, montant_ttc, numero_facture, date_facture, statut, motif_rejet, file_url)
- `invoice_items` (id, invoice_id, description, quantite, pu, montant_ht)
- `chantier_depenses` (facture_id en FK optionnel)

---

## Règles Globales (Applicables à Tous les Workflows)

| # | Règle | Pourquoi |
|---|-------|----------|
| G1 | 1 session = 1 chantier. Si l'agent détecte un autre chantier, il le signale et ignore. | Cohérence |
| G2 | L'org_id est toujours celui du user, jamais demandé. | Inféré du token |
| G3 | Les dates sont toujours en ISO 8601 (YYYY-MM-DD) en DB, mais le LLM accepte tout format. | Normalisation |
| G4 | Un motif de rejet (texte libre) est OBLIGATOIRE si `statut=rejete`. | Audit |
| G5 | Toute écriture DB est précédée d'un HITL#1 explicite. Aucun commit silencieux. | Principe fondamental |
| G6 | Si le LLM a un doute (confiance < 70%), il pose une question précise, il ne devine pas. | Robustesse |
| G7 | Les fichiers temporaires (photos, PDFs) sont nettoyés après traitement. | Hygiène disque |
