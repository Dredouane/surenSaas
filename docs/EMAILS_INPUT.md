# Module Emails - Documentation & Plan d'implémentation

## Vue d'ensemble

Module d'ingestion, stockage et vectorisation des emails Gmail pour PME du BTP via **aliasing multi-tenant**. **Ce module est purement technique** : il ne prend aucune décision métier, il se contente de capturer et structurer les données.

> **Separation of concerns** : Le module Secrétariat IA (décisions métier, workflows) est documenté séparément dans `docs/SECRETARIAT.md`. Ce module Emails ne fait que fournir les données brutes structurées.

---

## Architecture Multi-Tenant par Aliasing Gmail

### Principe

Un seul compte Gmail `REDACTED_EMAIL` reçoit tous les emails via forwarding avec aliasing :

**Format**: `REDACTED_EMAIL`

Le séparateur est configurable (défaut: `#`) pour éviter confusion avec les tirets du slug :
- `REDACTED_EMAIL` → Org "REDACTED_ORG_SLUG", Company "construction"
- `REDACTED_EMAIL` → Org "suren-societe-prod", Company "nettoyage"

### Flux de données

```
Client envoie à: client@entreprise.fr
                    ↓
Forward configuré vers: REDACTED_EMAIL
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND (TEST ou PROD)                        │
├─────────────────────────────────────────────────────────────────────┤
│  1. TRIGGER HTTP                                                    │
│     └─▶ POST /api/v1/{org}/emails/sync                              │
│                                                                     │
│  2. POLLING GMAIL (compte unique: REDACTED_EMAIL)             │
│     ├─▶ Connexion OAuth2 (mêmes credentials TEST/PROD)              │
│     ├─▶ Extraction header "Delivered-To"                            │
│     └─▶ Parsing alias: +test-construction                           │
│                                                                     │
│  3. ROUTING STRICT (pas de fallback)                                │
│     ├─▶ Vérification org_slug == ENV_ORG_SLUG                       │
│     ├─▶ Lookup company_id par company_slug                          │
│     ├─▶ ❌ Si org mismatch → IGNORER                                │
│     ├─▶ ❌ Si company inexistant → IGNORER                          │
│     └─▶ ✅ Si routing OK → Continuer traitement                     │
│                                                                     │
│  4. TRAITEMENT (RAG Mail + Vectorisation)                           │
│     ├─▶ Nettoyage contenu (suppression signatures, légals)          │
│     ├─▶ Stockage table `emails` avec org_id + company_id            │
│     ├─▶ Stockage pièces jointes                                     │
│     └─▶ Génération embeddings (pgvector)                            │
│                                                                     │
│  5. STATUT FINAL                                                    │
│     └─▶ Marquage `processing_status = 'vectorized'`                 │
│         (Prêt pour module Secrétariat)                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Règles de routing STRICTES

| Scénario | Action |
|----------|--------|
| **Alias valide** (`+test-construction`) + org match + company existe | ✅ Traitement complet |
| **Pas d'alias** (`REDACTED_EMAIL`) | ❌ IGNORER (pas de fallback) |
| **Org mismatch** (`+prod-xxx` sur env TEST) | ❌ IGNORER (log warning) |
| **Company inexistant** | ❌ IGNORER (log warning) |
| **Format invalide** (`+invalid`) | ❌ IGNORER (log error) |

> **Important** : Aucun email n'est stocké si le routing échoue. Seuls les emails avec aliasing valide et résolvable sont traités.

---

## Structure de base de données

### Tables créées (fichier `db/schema/020_email_tables.sql`)

#### 1. `email_accounts` - Configuration Gmail
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)         -- Org qui configure le compte
- email_address TEXT NOT NULL                      -- REDACTED_EMAIL
- email_address_display TEXT                       -- Nom d'affichage
- oauth_refresh_token TEXT NOT NULL                -- Token OAuth2 (chiffré)
- last_sync_uid BIGINT DEFAULT 0                   -- Dernier UID synchronisé
- last_sync_at TIMESTAMP
- is_active BOOLEAN DEFAULT true
- created_at / updated_at
```

#### 2. `emails` - Données des emails (avec routing)
```sql
- id UUID PRIMARY KEY
- org_id UUID NOT NULL REFERENCES organizations(id)    -- Org déduite de l'alias
- company_id UUID REFERENCES companies(id)             -- Company déduite de l'alias
- email_account_id UUID REFERENCES email_accounts(id)

-- Routing (nouveau)
- delivered_to_alias TEXT                              -- REDACTED_EMAIL
- routing_status TEXT                                  -- 'routed', 'ignored_no_alias', 
                                                       -- 'ignored_org_mismatch', 'ignored_company_not_found'

-- Identifiants Gmail
- gmail_thread_id TEXT NOT NULL
- gmail_message_id TEXT UNIQUE NOT NULL
- gmail_history_id BIGINT

-- En-têtes
- subject TEXT
- subject_cleaned TEXT
- sender_email TEXT NOT NULL
- sender_name TEXT
- sender_domain TEXT GENERATED
- recipient_emails TEXT[]
- cc_emails TEXT[]

-- Dates
- sent_at TIMESTAMP
- received_at TIMESTAMP

-- Contenu (RAG Mail)
- content_text TEXT                                    -- Corps nettoyé (RAG Mail)
- content_text_raw TEXT                                -- Corps original
- content_html TEXT
- content_cleaned_at TIMESTAMP

-- Traitement
- processing_status EMAIL_STATUS                       -- pending/processing/vectorized/error
- processing_error TEXT
- processing_attempts INTEGER DEFAULT 0

-- Métadonnées
- gmail_labels TEXT[]
- gmail_snippet TEXT
- headers JSONB                                        -- Headers complets (incluant Delivered-To)
- has_attachments BOOLEAN DEFAULT false
- attachments_count INTEGER DEFAULT 0

-- Traçabilité
- synced_by UUID REFERENCES auth.users(id)
- created_at / updated_at
```

#### 3. `email_attachments` - Pièces jointes
```sql
- id UUID PRIMARY KEY
- org_id UUID NOT NULL REFERENCES organizations(id)
- company_id UUID REFERENCES companies(id)           -- Hérité de l'email parent
- email_id UUID NOT NULL REFERENCES emails(id)
- filename TEXT
- mime_type TEXT
- file_size_bytes INTEGER
- storage_path TEXT
- ocr_text TEXT
- ocr_confidence DECIMAL(3,2)
- created_at / updated_at
```

#### 4. `email_embeddings` - Vecteurs pour RAG
```sql
- id UUID PRIMARY KEY
- org_id UUID NOT NULL REFERENCES organizations(id)
- company_id UUID REFERENCES companies(id)           -- Hérité de l'email parent
- email_id UUID NOT NULL REFERENCES emails(id)
- source_type EMBEDDING_SOURCE                       -- 'email_body', 'attachment'
- source_id UUID
- content_chunk TEXT
- embedding VECTOR(768)                      -- 768 dims (text-embedding-004)
- chunk_index INTEGER
- created_at
```

### Types PostgreSQL

```sql
CREATE TYPE email_status AS ENUM (
    'pending',
    'processing', 
    'vectorized',
    'error'
);

CREATE TYPE embedding_source AS ENUM (
    'email_body',
    'attachment'
);

-- Note: Les embeddings sont générés avec Vertex AI text-embedding-004 (768 dimensions)
-- Le chunking utilise 500 tokens avec 50 tokens d'overlap
```

---

## Configuration Environnement

### Variables d'environnement (.env.test / .env.prod)

```bash
# Gmail OAuth2 (mêmes valeurs pour TEST et PROD - même compte Gmail)
SUREN_GMAIL_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com
SUREN_GMAIL_OAUTH_CLIENT_SECRET=xxx
SUREN_GMAIL_OAUTH_REFRESH_TOKEN=xxx

# Compte Gmail principal (explicite)
SUREN_GMAIL_ACCOUNT=REDACTED_EMAIL

# Séparateur d'alias (configurable, défaut: #)
EMAIL_ALIAS_SEPARATOR=#

# Org Slug pour validation routing (différent par env)
TEST_ORG_SLUG=REDACTED_ORG_SLUG
# ou
PROD_ORG_SLUG=suren-societe-prod

# Vertex AI (Google Cloud)
VERTEX_AI_PROJECT_ID=xxx
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_EMBEDDING_MODEL=text-embedding-004

# Stratégie d'embedding
EMBEDDING_SIZE=768                    # Dimensions (768 pour text-embedding-004)
EMBEDDING_CHUNK_SIZE=500              # Taille chunks en tokens
EMBEDDING_CHUNK_OVERLAP=50            # Overlap entre chunks en tokens
```

### Configuration du forwarding client

Les clients configurent un forwarding depuis leur adresse métier vers :
```
REDACTED_EMAIL
```

Exemple pour un client de l'entreprise "construction" sur l'environnement de test (séparateur `#`) :
```
REDACTED_EMAIL
```

---

## API Endpoints

### Synchronisation
```
POST /api/v1/{org}/emails/sync
├── Body: { 
│     "account_id": "uuid",
│     "sync_mode": "incremental",  // ou "historical"
│     "date_range": {              // si historical
│       "start_date": "2024-01-01",
│       "end_date": "2024-01-31"
│     }
│   }
└── Response: { 
│     "synced": 5,              // Emails avec routing OK
│     "ignored": 3,             // Emails ignorés (alias invalide)
│     "vectorized": 5,
│     "errors": 0,
│     "last_uid": 12345
│   }

GET /api/v1/{org}/emails/sync-status
└── Response: {
    "account_id": "uuid",
    "status": "idle",
    "last_sync": "2024-01-15T10:30:00Z",
    "last_sync_uid": 12345,
    "stats": {
      "total_synced": 150,
      "total_ignored": 23,
      "pending": 3,
      "vectorized": 147,
      "error": 0
    }
  }
```

### Gestion des comptes
```
GET    /api/v1/{org}/emails/accounts
POST   /api/v1/{org}/emails/accounts        # Connecter compte Gmail
GET    /api/v1/{org}/emails/accounts/{id}
DELETE /api/v1/{org}/emails/accounts/{id}   # Déconnecter
```

### Consultation emails (filtrable par company)
```
GET /api/v1/{org}/emails
├── Query: 
│   - company_id: filtrer par entreprise
│   - thread_id: filtrer par conversation
│   - status: pending/processing/vectorized/error
│   - sender: email expéditeur
│   - date_from/date_to: plage de dates
│   - search: recherche textuelle
│   - limit/offset: pagination
└── Response: Liste paginée avec métadonnées

GET /api/v1/{org}/emails/{id}
└── Response: Détail complet + attachments + embeddings status
```

---

## TÂCHES À FAIRE (Phase 1: Emails)

### T1: Configuration OAuth2 Gmail
**Objectif** : Configurer l'accès API Gmail pour `REDACTED_EMAIL`
- [ ] Créer projet Google Cloud Console
- [ ] Configurer écran de consentement OAuth (type "Externe")
- [ ] Créer credentials OAuth2 (Client ID + Secret)
- [ ] Activer Gmail API
- [ ] Scopes : `https://www.googleapis.com/auth/gmail.readonly`
- [ ] Générer refresh token via OAuth Playground ou script local
- [ ] Ajouter dans `.env.test` et `.env.prod` :
  - `SUREN_GMAIL_OAUTH_CLIENT_ID`
  - `SUREN_GMAIL_OAUTH_CLIENT_SECRET`
  - `SUREN_GMAIL_OAUTH_REFRESH_TOKEN`
  - `SUREN_GMAIL_ACCOUNT=REDACTED_EMAIL`
  - `EMAIL_ALIAS_SEPARATOR=#` (ou autre caractère accepté par Gmail)

### T2: Structure base de données
**Objectif** : Créer les tables avec support routing par alias
- [ ] Créer fichier `db/schema/020_email_tables.sql`
- [ ] Extension `vector` (pgvector)
- [ ] Types ENUM (`email_status`, `embedding_source`)
- [ ] Table `email_accounts` (config OAuth)
- [ ] Table `emails` avec :
  - `company_id` (référence company)
  - `delivered_to_alias` (pour traçabilité)
  - `routing_status` (statut du routing)
- [ ] Table `email_attachments` avec `company_id`
- [ ] Table `email_embeddings` avec `company_id`
- [ ] Indexes (performance recherche, routing)
- [ ] Triggers `updated_at`

### T3: Service Gmail API
**Objectif** : Communiquer avec Gmail
- [ ] Créer `app/services/gmail/gmail_client.py`
- [ ] Authentification OAuth2 (access token depuis refresh token)
- [ ] Méthode `list_messages(since_uid)` - récupération incrémentale
- [ ] Méthode `list_messages_by_date_range(start_date, end_date)` - polling historique
- [ ] Méthode `get_message(message_id)` avec extraction headers complets
- [ ] Extraction header `Delivered-To` pour routing
- [ ] Gestion pagination (batch requests)
- [ ] Gestion erreurs API (rate limits, token expired)

### T3b: Service de Routing par Alias (NOUVEAU)
**Objectif** : Router les emails vers la bonne org/company avec séparateur configurable
- [ ] Créer `app/services/emails/alias_router.py`
- [ ] Lire `EMAIL_ALIAS_SEPARATOR` depuis ENV (défaut: `#`)
- [ ] Parser `Delivered-To` header : `REDACTED_EMAIL`
- [ ] Regex dynamique selon séparateur : `\+([^{sep}@]+){sep}([^@]+)@gmail\.com`
- [ ] Valider `org_slug` contre `ENV_ORG_SLUG` (TEST_ORG_SLUG ou PROD_ORG_SLUG)
- [ ] Lookup `company_id` par `company_slug` + `org_id`
- [ ] Retourner struct : `{org_id, company_id, routing_status}` ou `None` si ignoré
- [ ] Gestion cas limites :
  - Pas d'alias → `routing_status='ignored_no_alias'` → return None
  - Org mismatch → `routing_status='ignored_org_mismatch'` → return None
  - Company inexistant → `routing_status='ignored_company_not_found'` → return None
  - Format invalide → `routing_status='ignored_invalid_format'` → return None
- [ ] Tests unitaires des différents cas

### T4: Service de nettoyage de contenu (RAG Mail + Extraction Forward)
**Objectif** : Extraire le mail original du forward et nettoyer pour RAG
- [ ] Créer `app/services/emails/content_cleaner.py`
- [ ] Détecter et parser les patterns forward (Gmail, Outlook, Apple Mail)
- [ ] Extraire headers originaux (From, To, Date, Subject) du mail forwardé
- [ ] Extraire le corps original (sans le header du forward)
- [ ] Suppression signatures ("--", "Cordialement", noms, titres)
- [ ] Suppression mentions légales ("Confidentialité...", "Disclaimer...")
- [ ] Suppression headers internes restants ("Forwarded by...", "De :", "À :")
- [ ] Suppression blocs publicitaires / pieds de page
- [ ] Extraction texte brut depuis HTML si nécessaire
- [ ] Conservation contexte métier (dates, montants, chantiers)
- [ ] Tests unitaires avec exemples réels BTP

### T5: Service de synchronisation
**Objectif** : Orchestrer le polling avec routing
- [ ] Créer `app/services/emails/sync_service.py`
- [ ] Méthode `sync_account(account_id, sync_mode, date_range)`
- [ ] Pour chaque email Gmail :
  1. Extraction `Delivered-To` header
  2. Appel `alias_router.parse_and_route()`
  3. Si routing OK → continuer traitement
  4. Si routing KO → incrémenter compteur "ignored", passer au suivant
- [ ] Gestion `last_uid` pour synchro incrémentale
- [ ] Stockage emails routés en DB (batch insert)
- [ ] Gestion des threads
- [ ] Mise à jour `last_sync_at` / `last_sync_uid`
- [ ] Logging détaillé (synced, ignored par raison, erreurs)
- [ ] Retourner stats complètes

### T6: Service de vectorisation (Vertex AI + Matryoshka)
**Objectif** : Générer les embeddings avec Vertex AI et stratégie Matryoshka
- [ ] Créer `app/services/emails/embedding_service.py`
- [ ] Intégrer `vertexai.language_models.TextEmbeddingModel` avec `text-embedding-004`
- [ ] **Chunking** : Fonction de découpage 500 tokens avec overlap 50 tokens
- [ ] **Matryoshka Slicing** : Générer vecteur complet, sauvegarder `[:EMBEDDING_SIZE]` (défaut 768)
- [ ] OCR pièces jointes via Extracteur existant
- [ ] Génération embeddings async (non-bloquante pour le flux principal)
- [ ] Stockage vecteurs pgvector table `email_embeddings`
- [ ] Mise à jour `processing_status = 'vectorized'`
- [ ] Gestion erreurs avec retry

### T7: Endpoints API
**Objectif** : Exposer le fonctionnement
- [ ] Routes OpenAPI (`openapi/api.yaml`)
- [ ] Contrôleur `POST /{org}/emails/sync` avec support sync_mode
- [ ] Contrôleur `GET /{org}/emails/sync-status` avec stats ignored
- [ ] Contrôleur CRUD comptes email
- [ ] Contrôleur consultation emails (filtrage par company)
- [ ] Génération code depuis OpenAPI
- [ ] Validation JWT + org

---

## Stratégie d'Embedding (Vectorisation)

### Architecture Asynchrone

> **Réponse à la question d'asynchronisme** : Oui, tu as raison. L'extraction raw data dans Supabase est déjà découplée de l'embedding. Le polling synchrone stocke d'abord les emails avec `processing_status = 'pending'`, puis l'embedding se fait dans un second temps. Cela permet :
> - De ne pas bloquer le polling si l'API Vertex AI est lente
> - De retry l'embedding indépendamment si ça échoue
> - De traiter l'embedding en batch ou à la demande

### Flux de vectorisation

```
1. Email stocké en DB (raw data)
   └─▶ processing_status = 'pending'

2. Déclenchement vectorisation (option A: async immédiat, option B: endpoint séparé)
   └─▶ Chunking 500 tokens + overlap 50

3. Appel Vertex AI (async/non-bloquant)
   └─▶ text-embedding-004

4. Matryoshka Slicing
   └─▶ vector[:EMBEDDING_SIZE] (défaut 768)

5. Stockage pgvector
   └─▶ processing_status = 'vectorized'
```

### Configuration Technique

**Variables d'environnement** :
```bash
# Vertex AI (Google Cloud)
VERTEX_AI_PROJECT_ID=xxx
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_EMBEDDING_MODEL=text-embedding-004

# Stratégie Matryoshka
EMBEDDING_SIZE=768                    # Dimensions à conserver (défaut: 768, max: 768 pour text-embedding-004)
EMBEDDING_CHUNK_SIZE=500              # Taille des chunks en tokens
EMBEDDING_CHUNK_OVERLAP=50            # Recouvrement entre chunks en tokens
```

### Chunking avec Overlap

**Pourquoi l'overlap ?** 
- Évite de perdre le contexte entre deux chunks
- Garantit qu'une information à cheval sur deux blocs est préservée

```python
# Exemple
chunk_1 = "...rendez-vous le 15 août pour débuter les travaux. Merci de..."
chunk_2 = "...de confirmer votre présence. Cordialement..."
# L'info "15 août" n'est pas coupée grâce à l'overlap
```

### Matryoshka Slicing

**Principe** : Générer l'embedding complet mais ne stocker que les N premières dimensions.

**Avantages** :
- Réduction espace stockage Supabase (~50% si 768/1536)
- Performance recherche vectorielle améliorée
- Qualité préservée (les premières dimensions contiennent l'essentiel sémantique)

```python
# Implémentation
full_vector = model.get_embeddings([text])[0].values  # 768 dims pour text-embedding-004
sliced_vector = full_vector[:EMBEDDING_SIZE]          # 768 dims (défaut)
```

### Options de déclenchement

**Option A : Async immédiat (dans sync_service)**
```python
# Après stockage email en DB
asyncio.create_task(embedding_service.vectorize_email_async(email_id))
# Le polling continue, l'embedding se fait en parallèle
```

**Option B : Endpoint séparé (contrôle explicite)**
```python
POST /{org}/emails/{id}/vectorize  # Déclenche manuellement
# ou
POST /{org}/emails/vectorize-pending  # Vectorise tous les pending
```

**Recommandation** : Option A pour l'automatisation, Option B pour le contrôle/debug.

---

### T8: Intégration FileStorageService
**Objectif** : Stocker pièces jointes
- [ ] Téléchargement PJ depuis Gmail
- [ ] Stockage via `FileStorageService.store_file()`
- [ ] Nettoyage fichiers temporaires

### T9: Tests TDD Complets
**Objectif** : Valider tous les scénarios avec vrais embeddings
- [ ] Créer `tests/test_email_ingestion.py` (scénarios 1, 2, 4)
- [ ] Créer `tests/test_email_routing.py` (scénario 3 - cas limites)
- [ ] Créer `tests/test_email_cleaning.py` (scénario 5 - RAG Mail + extraction forward)
- [ ] Fixtures JSON dans `tests/data/emails/`
- [ ] Tests scénario 1 : Email forwardé simple avec PJ (recherche sémantique sur OCR)
- [ ] Tests scénario 2 : Chaîne d'emails thread (recherche sémantique dans réponse)
- [ ] Tests scénario 3 : Emails ignorés (no_alias, org_mismatch, company_not_found, invalid_format)
- [ ] Tests scénario 4 : Polling historique par période
- [ ] Tests scénario 5 : Extraction forward + RAG Mail
- [ ] Tests recherche sémantique avec vrais embeddings (pas de mock)
- [ ] Tests mocks Gmail API
- [ ] Test charge (100+ emails)

### T10: Documentation & Monitoring
**Objectif** : Faciliter maintenance
- [ ] Métriques : synced, ignored (par raison), vectorized, errors
- [ ] Logging structuré JSON
- [ ] Documentation procédure renouvellement OAuth
- [ ] Documentation troubleshooting routing

---

## Dépendances avec autres modules

### Modules existants utilisés
- `FileStorageService` : Stockage PJ
- `GenericDocumentExtractor` : OCR
- `CapabilityChecker` : Permissions

### Interface avec module Secrétariat (futur)
```python
# Le module Secrétariat utilisera ces données :
emails_to_analyze = await db.query("""
    SELECT e.*, c.slug as company_slug
    FROM emails e
    JOIN companies c ON c.id = e.company_id
    WHERE e.processing_status = 'vectorized'
    AND e.id NOT IN (SELECT email_id FROM secretariat_analysis)
""")
```

---

## Conventions & Patterns

### Nommage
- Tables : `emails`, `email_accounts`, `email_attachments`, `email_embeddings`
- Services : `gmail_client.py`, `alias_router.py`, `sync_service.py`, etc.
- Routing status : `routed`, `ignored_no_alias`, `ignored_org_mismatch`, `ignored_company_not_found`

### Gestion des erreurs
- Erreur Gmail API → `processing_status = 'error'` + log
- Routing échoué → Email ignoré (pas stocké) + log + stats
- Erreur vectorisation → `processing_status = 'error'`

---

## Notes de conception

### Pourquoi ignorer les emails sans alias valide ?

1. **Sécurité** : Pas de données parasites dans la DB
2. **Clarté** : Seuls les emails routés vers une company sont traités
3. **Simplicité** : Pas de gestion de "fallback" complexe

### Pourquoi même credentials OAuth pour TEST/PROD ?

Un seul compte Gmail `REDACTED_EMAIL` est utilisé. L'isolation TEST/PROD se fait via :
- Les variables d'env `TEST_ORG_SLUG` vs `PROD_ORG_SLUG`
- Le routing ignore les emails destinés à l'autre environnement

---

## Extraction du Mail Original (Suppression Forward)

### Principe

Le module traite les emails comme s'il écoutait directement l'adresse du client. L'adresse Gmail `REDACTED_EMAIL` disparaît complètement des données stockées.

**Processus** :
1. Email reçu sur `REDACTED_EMAIL` (forward du client)
2. Détection du pattern forward (`Fwd:`, `---------- Forwarded message ---------`)
3. Extraction des headers originaux (From, To, Date, Subject du mail forwardé)
4. **Stockage uniquement du mail original** :
   - `sender_email` = expéditeur original (ex: `contact@acorus.fr`)
   - `recipient_emails` = destinataire original (ex: `client@batiment-pro.fr`)
   - `subject` = sujet original (sans "Fwd:")
   - `sent_at` = date d'envoi originale
   - `content_text` = corps original nettoyé

**Avantages** :
- Le client peut forwarder plusieurs fois, l'email original est toujours retrouvé
- L'adresse Gmail n'apparaît nulle part (transparence totale)
- Le module "Secrétariat" voit les conversations comme si elle écoutait le client directement

### Patterns de détection

```python
# Patterns à détecter (ordre de priorité)
FORWARD_PATTERNS = [
    r"---------- Forwarded message ---------",  # Gmail standard
    r"^From: .*\nDate: .*\nSubject: .*\nTo: ",  # Headers formatés
    r"Begin forwarded message:",                 # Apple Mail
    r"_____ Original Message _____",             # Outlook
    r"^\s*From:\s*[^<]+<[^>]+>\s*$",           # From: line isolée
]
```

---

## Configuration du Séparateur d'Alias

### Variable d'environnement

Le séparateur entre `org_slug` et `company_slug` est configurable pour éviter les confusions avec les tirets du slug.

```bash
# .env.test / .env.prod
EMAIL_ALIAS_SEPARATOR=#     # Par défaut: # (dièse)
# Alternatives acceptées par Gmail: $ % & * = ? ^ { | } ~
```

### Format avec séparateur

```
REDACTED_EMAIL
                      ↑
                 séparateur (configurable)
```

### Parsing

```python
# Regex dynamique selon EMAIL_ALIAS_SEPARATOR
separator = os.getenv("EMAIL_ALIAS_SEPARATOR", "#")
# Échapper les caractères spéciaux regex si nécessaire
escaped_sep = re.escape(separator)
pattern = rf"\+([^{escaped_sep}@]+){escaped_sep}([^@]+)@gmail\.com"
```

**Exemples avec différents séparateurs** :

| Séparateur | Format d'alias | Exemple |
|------------|----------------|---------|
| `#` (défaut) | `+org#company` | `REDACTED_EMAIL` |
| `$` | `+org$company` | `REDACTED_EMAIL_LOCAL+REDACTED_ORG_SLUG$construction@gmail.com` |
| `%` | `+org%company` | `REDACTED_EMAIL` |

---

## Tests TDD - Scénarios Complets

### Structure des tests

```
tests/
├── test_email_ingestion.py          # Scénarios 1, 2, 4
├── test_email_routing.py            # Scénario 3 (cas limites)
├── test_email_cleaning.py           # Scénario 5 (RAG Mail + extraction forward)
├── conftest.py                      # Fixtures communes
└── data/
    └── emails/
        ├── email_1_forwarded_simple.json
        ├── email_2_forwarded_reply.json
        ├── email_3_no_alias.json
        ├── email_4_wrong_org.json
        ├── email_5_invalid_format.json
        └── INV-EXA-0001_EXAMPLE-SOCIETE.pdf
```

### Constantes de test

```python
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"
TEST_ORG_ID = "uuid-from-env"
TEST_COMPANY_SLUG = "construction"
TEST_COMPANY_ID = "uuid-construction-from-db"
EMAIL_ALIAS_SEPARATOR = "#"  # Depuis ENV
GMAIL_ACCOUNT = "REDACTED_EMAIL"
ALIAS_FULL = f"REDACTED_EMAIL"
```

### Scénario 1 : Email Forwardé Simple avec Facture (1er Polling)

**Contexte** : Facture ACORUS forwardée par le client

**Données test** (`email_1_forwarded_simple.json`) :
```json
{
  "gmail_uid": 1001,
  "gmail_message_id": "<forward-msg-001@batiment-pro.fr>",
  "gmail_thread_id": "thread-abc123",
  "delivered_to": "REDACTED_EMAIL",
  "raw_headers": {
    "From": "client@batiment-pro.fr",
    "To": "REDACTED_EMAIL",
    "Subject": "Fwd: Facture INV-EXA-0001 - Travaux salle de bain",
    "Date": "Mon, 28 Jul 2025 14:30:00 +0200"
  },
  "forwarded_content": {
    "original_headers": {
      "From": "Service Commercial ACORUS <contact@acorus.fr>",
      "To": "client@batiment-pro.fr",
      "Subject": "Facture INV-EXA-0001 - Travaux salle de bain",
      "Date": "Mon, 28 Jul 2025 10:00:00 +0200"
    },
    "original_body": "Madame, Monsieur,\n\nVeuillez trouver ci-joint notre facture N° INV-EXA-0001 pour les travaux de rénovation de la salle de bain PMR à la Résidence Les Lilas.\n\nMontant HT : 3 280,78 €\nBon de commande : BC2507036455\n\nCordialement,\n--\nService Commercial ACORUS\nTél : REDACTED_PHONE.78\nwww.acorus.fr",
    "attachments": ["INV-EXA-0001_EXAMPLE-SOCIETE.pdf"]
  }
}
```

**Vérifications** :

| Champ | Valeur attendue |
|-------|-----------------|
| `emails.sender_email` | `contact@acorus.fr` |
| `emails.sender_name` | `Service Commercial ACORUS` |
| `emails.recipient_emails` | `["client@batiment-pro.fr"]` |
| `emails.subject` | `Facture INV-EXA-0001 - Travaux salle de bain` (sans "Fwd:") |
| `emails.sent_at` | `2025-07-28T10:00:00+02:00` (date originale) |
| `emails.delivered_to_alias` | `REDACTED_EMAIL` |
| `emails.company_id` | UUID construction |
| `emails.content_text` | Sans signature ACORUS, sans mentions légales |
| `attachments[0].filename` | `INV-EXA-0001_EXAMPLE-SOCIETE.pdf` |
| `attachments[0].ocr_text` | Contient "ACORUS", "INV-EXA-0001", "3280.78" |

**Test recherche sémantique** :
```python
# Recherche dans la pièce jointe (OCR)
query = "Montant HT 3280.78 ACORUS facture"
results = search_similar_emails(query_embedding, TEST_ORG_ID, TEST_COMPANY_ID)
assert len(results) > 0
assert any("3280" in r.content_chunk or "ACORUS" in r.content_chunk for r in results)
```

### Scénario 2 : Chaîne d'Emails (Thread) - 2ème Polling

**Email 1** : Déjà en base (scénario 1), UID 1001

**Email 2** : Réponse du client forwardée (`email_2_forwarded_reply.json`)
```json
{
  "gmail_uid": 1002,
  "gmail_message_id": "<forward-msg-002@batiment-pro.fr>",
  "gmail_thread_id": "thread-abc123",
  "delivered_to": "REDACTED_EMAIL",
  "in_reply_to": "<original-msg-001@acorus.fr>",
  "references": ["<original-msg-001@acorus.fr>"],
  "forwarded_content": {
    "original_headers": {
      "From": "Gérard Martin <client@batiment-pro.fr>",
      "To": "contact@acorus.fr",
      "Subject": "Re: Facture INV-EXA-0001 - Travaux salle de bain",
      "Date": "Wed, 30 Jul 2025 09:15:00 +0200"
    },
    "original_body": "Bonjour,\n\nMerci pour la facture. Pouvez-vous commencer les travaux la semaine du 11 août ? Le logement sera libre.\n\nMerci de confirmer.\nCordialement,\nGérard Martin\nResponsable Technique"
  }
}
```

**Vérifications** :

| Champ | Valeur attendue |
|-------|-----------------|
| `emails.sender_email` | `client@batiment-pro.fr` |
| `emails.in_reply_to` | `<original-msg-001@acorus.fr>` |
| `emails.gmail_thread_id` | Identique à email 1 |
| `emails.company_id` | UUID construction |
| Thread complet | 2 emails via `get_email_thread()` |

**Test recherche sémantique dans la chaîne** :
```python
# Recherche info dans le mail de réponse
query = "commencer travaux semaine 11 août"
results = search_similar_emails(query_embedding, TEST_ORG_ID, TEST_COMPANY_ID)
assert len(results) > 0
assert any("11 août" in r.content_chunk for r in results)
```

### Scénario 3 : Emails Ignorés (Cas Limites)

**3a. Sans Alias** (`email_3_no_alias.json`)
- `To`: `REDACTED_EMAIL` (pas d'alias)
- Résultat: **Ignoré** - `ignored_no_alias`

**3b. Org Mismatch** (`email_4_wrong_org.json`)
- `To`: `REDACTED_EMAIL` (sur env TEST)
- Résultat: **Ignoré** - `ignored_org_mismatch`

**3c. Company Inexistante**
- `To`: `REDACTED_EMAIL`
- Résultat: **Ignoré** - `ignored_company_not_found`

**3d. Format Invalide**
- `To`: `REDACTED_EMAIL` (pas de séparateur company)
- Résultat: **Ignoré** - `ignored_invalid_format`

**Vérifications globales** :
- Aucun email stocké en DB
- Réponse API: `synced: 0, ignored: 4`
- Stats détaillées par raison

### Scénario 4 : Polling Historique par Période

**Paramètres** :
```json
{
  "account_id": "uuid",
  "sync_mode": "historical",
  "date_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

**Mock** : 5 emails (3 valides, 2 ignorés)

**Vérifications** :
- Emails stockés: 3
- Emails ignorés: 2
- `last_sync_uid`: mis à jour
- Tous les stockés ont `company_id` non NULL

### Scénario 5 : RAG Mail + Extraction Forward

**Input** (contenu brut forwardé) :
```
---------- Forwarded message ---------
From: Service Commercial ACORUS <contact@acorus.fr>
Date: Mon, 28 Jul 2025 10:00:00 +0200
Subject: Facture INV-EXA-0001
To: client@batiment-pro.fr

Madame, Monsieur,

Veuillez trouver ci-joint notre facture N° INV-EXA-0001.
Montant HT : 3 280,78 €

Cordialement,
--
Service Commercial ACORUS
Tél : REDACTED_PHONE.78
www.acorus.fr

Ce message et toutes les pièces jointes sont confidentiels...
```

**Output attendu** (après traitement) :
```
Madame, Monsieur,

Veuillez trouver ci-joint notre facture N° INV-EXA-0001.
Montant HT : 3 280,78 €

Cordialement,
```

**Tests** :
- Header forward supprimé
- Signature supprimée (-- jusqu'à la fin)
- Mention légale supprimée
- Contenu métier conservé

**Test recherche sémantique** :
```python
query = "facture INV-EXA-0001 montant 3280"
results = search_similar_emails(query_embedding, TEST_ORG_ID, TEST_COMPANY_ID)
assert len(results) > 0
```

---

## Variables d'Environnement

### Secrets dans `~/.bashrc` (Local + Déploiement)

Les secrets Gmail OAuth2 doivent être définis dans votre `~/.bashrc` local et sont automatiquement passés aux déploiements Cloud Run via les scripts `deploy_back_test.sh` et `deploy_back_prod.sh`.

```bash
# Ajouter dans ~/.bashrc

# ============================================
# MODULE EMAILS - Gmail OAuth2 (TEST/PROD partagés)
# ============================================
export SUREN_GMAIL_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export SUREN_GMAIL_OAUTH_CLIENT_SECRET="your-client-secret"
export SUREN_GMAIL_OAUTH_REFRESH_TOKEN="your-refresh-token"
export SUREN_GMAIL_ACCOUNT="REDACTED_EMAIL"
```

**Comment obtenir ces valeurs ?**
1. Va sur [Google Cloud Console](https://console.cloud.google.com/)
2. Crée un projet (ou utilise un existant)
3. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
4. Type : **Web application** ou **Desktop app**
5. Configure l'écran de consentement OAuth (externe)
6. Active **Gmail API** dans la bibliothèque
7. Récupère `client_id` et `client_secret`
8. Pour le **refresh token**, utilise [OAuth Playground](https://developers.google.com/oauthplayground) :
   - Étape 1 : Select & authorize APIs → Gmail API v1 → `https://www.googleapis.com/auth/gmail.readonly`
   - Étape 2 : Exchange authorization code for tokens
   - Récupère le `refresh_token`

### Variables dans `.env.test` / `.env.prod`

Ces variables sont chargées depuis les fichiers d'environnement (pas de secrets ici):

```bash
# Séparateur d'alias (configurable, défaut: #)
EMAIL_ALIAS_SEPARATOR=#

# Org Slug (différent par environnement)
TEST_ORG_SLUG=REDACTED_ORG_SLUG
# ou PROD_ORG_SLUG=suren-societe-prod

# Vertex AI (peut être dans .bashrc ou .env)
VERTEX_AI_PROJECT_ID=xxx
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_EMBEDDING_MODEL=text-embedding-004

# Configuration Embedding
EMBEDDING_SIZE=768
EMBEDDING_CHUNK_SIZE=500
EMBEDDING_CHUNK_OVERLAP=50
```

### Vérification des secrets

```bash
# Vérifier que tout est configuré
./scripts/check-gcp-secrets.sh

# Déployer (les secrets seront automatiquement créés/mis à jour)
./scripts/deploy_back_test.sh
```

---

## Références

- `docs/SECRETARIAT.md` - Module décisions métier (futur)
- `docs/CAPABILITIES.md` - Système de permissions
- `docs/gemini-extraction-agent.md` - OCR existant
