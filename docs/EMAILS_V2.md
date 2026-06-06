# Emails V2 — Hermès Pipeline

Documentation centrale du nouveau flux d'ingestion et d'analyse des emails.

## Architecture

```
┌─────────┐     ┌────────────────┐     ┌────────────┐     ┌──────────────┐
│  Gmail  │     │ Backend (Fast) │     │  Supabase  │     │Hermès (Worker│
└────┬────┘     └───────┬────────┘     └─────┬──────┘     └──────┬───────┘
     │                  │                    │                   │
     │──( Cron 5m )────>│                    │                   │
     │  Polling IMAP    │                    │                   │
     │                  │──( Stockage )──────>│                   │
     │                  │  emails            │                   │
     │                  │  email_attachments │                   │
     │                  │                    │                   │
     │                  │──( Vectorisation )>│                   │
     │                  │  email_embeddings  │                   │
     │                  │  + chantier_id     │                   │
     │                  │  + status =        │                   │
     │                  │  'READY_FOR_AI'    │                   │
     │                  │                    │                   │
     │                  │                    │<──( Poll )────────│ [Cron 5m]
     │                  │                    │   status =        │
     │                  │                    │   'READY_FOR_AI'  │
     │                  │                    │                   │
     │                  │<──( Read )─────────│───────────────────│
     │                  │  GET /ready-for-   │                   │
     │                  │  analysis          │                   │
     │                  │                    │                   │
     │                  │──( Analyse )───────────────────────────│ [LLM Gemini]
     │                  │  POST /{id}/       │                   │
     │                  │  analysis          │                   │
     │                  │                    │                   │
     │                  │──( Stockage )──────>│                   │
     │                  │  email_ai_analysis │                   │
     │                  │  status =          │                   │
     │                  │  'PENDING_VAL'     │                   │
     │                  │                    │                   │
┌─────────┐            │                    │                   │
│  User   │            │                    │                   │
└────┬────┘            │                    │                   │
     │──( Valide )────>│                    │                   │
     │  Telegram/Front │──( Execute )───────>│                   │
     │                  │  POST /{id}/execute│                   │
     │                  │  proposed_actions  │                   │
     │                  │  → depenses/taches │                   │
     │                  │  status = PROCESSED│                   │
```

## Cycle de vie des statuts

```
        ┌─────────┐
        │   NEW   │  Email reçu brut (avant traitement backend)
        └────┬────┘
             │
    Traitement backend (vectorisation + routage chantier)
             │
             ▼
     ┌──────────────┐
     │ READY_FOR_AI │  Prêt pour Hermès (vecteurs + chantier_id OK)
     └──────┬───────┘
            │
    Hermès analyse (LLM)
            │
            ▼
    ┌───────────────────┐
    │ PENDING_VALIDATION│  Hermès a soumis ses propositions
    └────────┬──────────┘
             │
    Humain valide (clic Telegram/Front)
             │
             ├──────────┐
             ▼          ▼
     ┌──────────┐ ┌──────────┐
     │ PROCESSED│ │ REJECTED │
     │ Actions  │ │ Refus    │
     │ exécutées│ │ humain   │
     └──────────┘ └──────────┘
```

## Tables

### `email_threads` — Statut étendu

```sql
ALTER TABLE email_threads ADD COLUMN IF NOT EXISTS status email_processing_status DEFAULT 'NEW';
```

### `email_ai_analysis` — Propositions Hermès

```sql
CREATE TABLE email_ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_thread_id UUID REFERENCES email_threads(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    detected_urgency VARCHAR(20),         -- 'LOW', 'MEDIUM', 'HIGH'
    proposed_actions JSONB DEFAULT '[]'::jsonb,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    validated_at TIMESTAMP WITH TIME ZONE,
    validated_by UUID REFERENCES auth.users(id),
    raw_llm_response TEXT
);
```

Format de `proposed_actions` :
```json
[
  {"type": "CREATE_EXPENSE", "payload": {"montant": 450, "fournisseur": "Point P"}},
  {"type": "CREATE_TASK", "payload": {"titre": "Commander placo", "priorite": "haute"}},
  {"type": "SEND_NOTIFICATION", "payload": {"message": "Blocage chantier", "urgence": "critical"}}
]
```

## Endpoints API

### `GET /api/v1/emails/ready-for-analysis`

Récupère les threads prêts pour Hermès (status = `READY_FOR_AI`).

**Query :** `org_id`, `company_id` (optionnel), `limit` (max 50)

**Response :**
```json
{
  "data": [{
    "thread_id": "uuid",
    "chantier_id": "uuid",
    "chantier_nom": "Chantier P14",
    "subject": "Devis INV-EXA-0001",
    "emails": [
      {"id": "uuid", "from": "client@acorus.fr", "subject": "...", "body": "..."}
    ]
  }]
}
```

### `POST /api/v1/emails/{thread_id}/analysis`

Hermès soumet son analyse.

**Body :**
```json
{
  "summary": "Demande de prix placo",
  "detected_urgency": "MEDIUM",
  "proposed_actions": [...],
  "raw_llm_response": "..."
}
```

**Effet de bord :** Insère dans `email_ai_analysis`, passe le thread en `PENDING_VALIDATION`, notifie l'utilisateur.

### `POST /api/v1/analysis/{analysis_id}/execute`

Validation humaine.

**Effet de bord :** Exécute `proposed_actions` (appelle les fonctions internes `_create_depense_internal`, `_manage_taches_internal`, `NotificationService`), passe le thread en `PROCESSED`.

**Body :**
```json
{
  "action": "accept"  // ou "reject"
}
```

## Interface de Validation (Frontend / Telegram)

### Données à afficher

Chaque analyse en attente (`PENDING_VALIDATION`) expose ces informations :

| Champ | Type | Description |
|-------|------|-------------|
| `thread.subject` | string | Sujet du fil de discussion |
| `thread.participants` | string[] | Expéditeurs du thread |
| `thread.email_count` | int | Nombre d'emails dans le thread |
| `thread.last_email_at` | datetime | Date du dernier email |
| `analysis.summary` | string | Résumé IA de l'analyse |
| `analysis.detected_urgency` | string | `LOW`, `MEDIUM` ou `HIGH` |
| `analysis.analyzed_at` | datetime | Date de l'analyse |
| `analysis.proposed_actions` | array | Liste des actions proposées |

### Endpoint pour récupérer les validations en attente

```http
GET /api/v1/{org}/email-threads?status=PENDING_VALIDATION
```

Retourne la liste des threads avec leur analyse via la jointure avec `email_ai_analysis`.

### Structure des actions proposées

Types possibles actuellement observés dans la production :

| Type | Payload | Exemple réel |
|------|---------|-------------|
| `CREATE_TACHE` | `{"titre", "priorite", "description", "date_echeance"}` | Clôturer levée de réserve pignon 169 |
| `CREATE_OPERATION` | `{"description", "type", "date_echeance"}` | Réception façade cour lift |
| `IGNORE` | `{}` | Aucune action nécessaire |

Chaque action a un champ `confidence` (0.0 à 1.0) indiquant la certitude d'Hermès.

### Recommandations design pour page "Validations Hermès"

```
┌──────────────────────────────────────────────────────┐
│ 🔔 Validations en attente (2)                         │
│                                                      │
│ ┌─────────────────────────────────────────────────┐  │
│ │ 🔴 HAUTE   TR: CR RC 10/03 - P14 Porte d'Orl. │  │
│ │ 14 emails · Enzo CAROFF, REDACTED_CONTACT      │  │
│ │                                                 │  │
│ │ Compte-rendu de coordination listant des        │  │
│ │ retards et réceptions à venir.                  │  │
│ │                                                 │  │
│ │ Actions proposées (10) :                        │  │
│ │ ☑ Clôturer levée de réserve pignon 169      90% │  │
│ │ ☑ Clôturer levée de réserve façade 134 rue  90% │  │
│ │ ☑ Préparer façade 134/133 côté cour          85% │  │
│ │ ☐ Rappel : ne pas surcharger zones           80% │  │
│ │ ...                                              │  │
│ │                                                 │  │
│ │           [❌ Rejeter]    [✅ Valider (3/10)]     │  │
│ └─────────────────────────────────────────────────┘  │
│                                                      │
│ ┌─────────────────────────────────────────────────┐  │
│ │ 🟡 MOYENNE  TR: CR RC 03/03 - P14 Porte d'Or.   │  │
│ │ 13 emails · Enzo CAROFF, REDACTED_CONTACT       │  │
│ │                                                 │  │
│ │ Aucune action spécifique détectée.              │  │
│ │                                                 │  │
│ │           [❌ Rejeter]    [✅ Archiver]          │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

**Comportement attendu :**
- **"Valider"** → `POST /analysis/{id}/execute` avec `action: "accept"` → exécute les actions sélectionnées → thread passe en `PROCESSED`
- **"Rejeter"** → `POST /analysis/{id}/execute` avec `action: "reject"` + `rejection_reason` → thread passe en `REJECTED`
- Les actions créées (tâches, opérations) doivent être visibles dans les pages existantes du chantier concerné

### État actuel de la production (juin 2026)

- **36 threads** en `READY_FOR_AI` — analysés par Hermès au prochain cycle
- **2 threads** en `PENDING_VALIDATION` — en attente de validation humaine
- **0 threads** validés ou rejetés — aucune interface de validation n'est encore déployée

## Règles métier

1. **Backend = plomberie uniquement** : stockage, vectorisation, endpoints. Pas de décision LLM.
2. **Hermès = cerveau** : analyse LLM, décisions, propositions. Ne touche pas directement à la DB (passe par les endpoints).
3. **HITL (Human in the Loop)** : Hermès propose, l'humain valide. Rien n'est écrit en DB tant que l'humain n'a pas cliqué "Valider".
4. **Déduplication** : SHA-256 composite (`sender|subject|date|body_hash`), fenêtre de 7 jours.
5. **Thread matching** : priorité `gmail_thread_id`, puis similarité cosinus (>0.85), puis LLM.

## Déploiement

### Migration SQL

```bash
# Appliquer la migration du cycle de vie
psql -f db/schema/022_email_v2_cycle_vie.sql
```

### Secrets

Les credentials IMAP sont chargés depuis `~/.bashrc` :
```bash
export SUREN_GMAIL_RECEPTION_IMAP_ADRESS="REDACTED_EMAIL"
export SUREN_GMAIL_RECEPTION_IMAP_MDP="mot_de_passe_application"
```
