# Module Emails - Documentation & Plan d'implémentation

## Vue d'ensemble

Module d'ingestion, stockage et vectorisation des emails Gmail pour PME du BTP. **Ce module est purement technique** : il ne prend aucune décision métier, il se contente de capturer et structurer les données.

> **Separation of concerns** : Le module Secrétariat IA (décisions métier, workflows) est documenté séparément dans `docs/SECRETARIAT.md`. Ce module Emails ne fait que fournir les données brutes structurées.

---

## Architecture

### Positionnement dans le système

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Gmail API     │────▶│   Module Emails  │────▶│  Module         │
│   (OAuth2)      │     │   (Ce document)  │     │  Secrétariat    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐          ┌──────────────┐
                        │  Supabase    │          │  Workflows   │
                        │  + Vector    │          │  métier      │
                        └──────────────┘          └──────────────┘
```

### Responsabilités du module Emails

| Couche | Responsabilité | Hors scope |
|--------|---------------|------------|
| **Ingestion** | Polling Gmail, récupération threads, nettoyage contenu | Décision sur l'importance |
| **Stockage** | Tables `emails`, `email_attachments`, `email_embeddings` | Actions métier |
| **Vectorisation** | Embeddings pgvector pour RAG | Analyse sémantique métier |

---

## Flux de données

```
1. TRIGGER HTTP (manuel/cron)
   └─▶ POST /api/v1/{org}/emails/sync

2. INGESTION
   ├─▶ Connexion Gmail API (OAuth2)
   ├─▶ Récupération emails (depuis last_uid)
   ├─▶ Threading natif Gmail (thread_id)
   └─▶ Nettoyage contenu (suppression signatures, légals)

3. STOCKAGE
   ├─▶ Insertion table `emails`
   ├─▶ Stockage pièces jointes (FileStorageService local)
   └─▶ Insertion table `email_attachments`

4. VECTORISATION
   ├─▶ Chunking texte mail
   ├─▶ OCR pièces jointes (PDF/images) via Extracteur existant
   ├─▶ Génération embeddings (Supabase pgvector)
   └─▶ Insertion table `email_embeddings`

5. STATUT
   └─▶ Marquage `processing_status = 'vectorized'`
       (Prêt pour module Secrétariat)
```

---

## Structure de base de données

### Tables créées (fichier `db/schema/020_email_tables.sql`)

#### 1. `email_accounts` - Configuration Gmail par organisation
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- email_address TEXT UNIQUE NOT NULL          -- Adresse Gmail
- oauth_refresh_token TEXT NOT NULL           -- Token OAuth2 (chiffré)
- last_sync_uid BIGINT DEFAULT 0              -- Dernier UID synchronisé
- last_sync_at TIMESTAMP                      -- Dernière synchro
- is_active BOOLEAN DEFAULT true
- created_at / updated_at
```

#### 2. `emails` - Données des emails
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- email_account_id UUID REFERENCES email_accounts(id)
- gmail_thread_id TEXT NOT NULL               -- ID thread natif Gmail
- gmail_message_id TEXT UNIQUE NOT NULL       -- ID message natif Gmail
- subject TEXT
- sender_email TEXT
- sender_name TEXT
- recipient_emails TEXT[]                     -- Destinataires
- sent_at TIMESTAMP                           -- Date envoi (Gmail)
- content_text TEXT                           -- Corps nettoyé
- content_html TEXT                           -- Corps HTML brut (optionnel)
- processing_status EMAIL_STATUS              -- Enum: pending/vectorized/error
- metadata JSONB                              -- Headers, labels Gmail
- created_at / updated_at
```

#### 3. `email_attachments` - Pièces jointes
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- email_id UUID REFERENCES emails(id)
- filename TEXT
- mime_type TEXT                              -- application/pdf, image/jpeg...
- file_size_bytes INTEGER
- storage_path TEXT                           -- Chemin FileStorageService
- ocr_text TEXT                               -- Texte extrait (si applicable)
- created_at
```

#### 4. `email_embeddings` - Vecteurs pour RAG
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- email_id UUID REFERENCES emails(id)
- source_type EMBEDDING_SOURCE                -- Enum: 'email_body', 'attachment'
- source_id UUID                              -- email_id ou attachment_id
- content_chunk TEXT                          -- Texte chunké
- embedding VECTOR(1536)                      -- pgvector (dimension selon modèle)
- chunk_index INTEGER                         -- Position dans le document
- created_at
```

### Types PostgreSQL

```sql
CREATE TYPE email_status AS ENUM (
    'pending',           -- Reçu, en attente traitement
    'processing',        -- En cours de vectorisation
    'vectorized',        -- Prêt pour Secrétariat
    'error'              -- Erreur traitement
);

CREATE TYPE embedding_source AS ENUM (
    'email_body',        -- Contenu du mail
    'attachment'         -- Pièce jointe
);
```

---

## API Endpoints (à ajouter dans OpenAPI)

### Synchronisation
```
POST /api/v1/{org}/emails/sync
├── Body: { "account_id": "uuid" }
└── Response: { "synced": 5, "errors": 0, "last_uid": 12345 }

GET /api/v1/{org}/emails/sync-status
└── Response: { "last_sync": "2024-01-15T10:30:00Z", "pending": 3 }
```

### Gestion des comptes
```
POST /api/v1/{org}/emails/accounts
├── Body: { "email": "contact@entreprise.com", "oauth_code": "..." }
└── Response: { "id": "uuid", "status": "connected" }

GET /api/v1/{org}/emails/accounts
DELETE /api/v1/{org}/emails/accounts/{id}
```

### Consultation emails
```
GET /api/v1/{org}/emails
├── Query: thread_id, status, date_from, date_to, search
└── Response: Liste paginée avec métadonnées

GET /api/v1/{org}/emails/{id}
└── Response: Détail complet + attachments + embeddings status
```

---

## TÂCHES À FAIRE (Phase 1: Emails)

### T1: Configuration OAuth2 Gmail
**Objectif** : Permettre la connexion sécurisée à l'API Gmail
- [ ] Créer projet Google Cloud Console
- [ ] Configurer écran de consentement OAuth
- [ ] Créer credentials OAuth2 (Client ID + Secret)
- [ ] Documenter scopes nécessaires (`https://www.googleapis.com/auth/gmail.readonly`)
- [ ] Implémenter flux OAuth2 (authorization code → refresh token)
- [ ] Chiffrer les refresh tokens en DB

### T2: Structure base de données
**Objectif** : Créer les tables pour stockage emails
- [ ] Créer fichier `db/schema/020_email_tables.sql`
- [ ] Table `email_accounts` (config OAuth par org)
- [ ] Table `emails` (métadonnées + contenu)
- [ ] Table `email_attachments` (pièces jointes)
- [ ] Table `email_embeddings` (vecteurs pgvector)
- [ ] Types ENUM (`email_status`, `embedding_source`)
- [ ] Indexes (performance recherche)
- [ ] Triggers `updated_at`

### T3: Service Gmail API
**Objectif** : Communiquer avec Gmail (synchro incrémentale et historique)
- [ ] Créer `app/services/gmail/gmail_client.py`
- [ ] Authentification OAuth2 (access token depuis refresh token)
- [ ] Méthode `list_messages(since_uid)` - récupération emails incrémentale
- [ ] Méthode `list_messages_by_date_range(start_date, end_date)` - **polling paramétrable pour traitement historique par période** (gestion de l'existant)
- [ ] Méthode `get_message(message_id)` - détail complet
- [ ] Méthode `get_thread(thread_id)` - récupération thread complet
- [ ] Gestion pagination (batch requests)
- [ ] Gestion erreurs API (rate limits, token expired)

### T4: Service de nettoyage de contenu (RAG Mail)
**Objectif** : Préparer le texte pour RAG via la logique "RAG Mail"
- [ ] Créer `app/services/emails/content_cleaner.py` avec logique **RAG Mail**
- [ ] Suppression signatures email (patterns communs : "--", "Cordialement", "Bien à vous", noms, titres)
- [ ] Suppression mentions légales ("Confidentialité...", "Si vous avez reçu ce mail par erreur...", "Disclaimer...")
- [ ] Suppression headers internes ("Forwarded by...", "De :", "À :", "Date :", "Objet :")
- [ ] Suppression blocs publicitaires / pieds de page commerciaux
- [ ] Extraction texte brut depuis HTML (si nécessaire)
- [ ] Conservation du contexte métier pertinent (dates, montants, noms chantiers)
- [ ] Tests unitaires avec exemples réels BTP

### T5: Service de synchronisation
**Objectif** : Orchestrer le polling
- [ ] Créer `app/services/emails/sync_service.py`
- [ ] Méthode `sync_account(account_id)` - synchro complète
- [ ] Gestion `last_uid` pour synchro incrémentale
- [ ] Stockage emails en DB (batch insert)
- [ ] Gestion des threads (regroupement natif Gmail)
- [ ] Mise à jour `last_sync_at` / `last_sync_uid`
- [ ] Logging détaillé (réussites/échecs par message)

### T6: Service de vectorisation
**Objectif** : Générer les embeddings pour RAG
- [ ] Créer `app/services/emails/embedding_service.py`
- [ ] Chunking texte mail (taille optimale pour embedding)
- [ ] Intégration Extracteur existant pour OCR PJ
- [ ] Génération embeddings via API (OpenAI/Supabase)
- [ ] Stockage vecteurs pgvector (`email_embeddings`)
- [ ] Mise à jour statut `processing_status = 'vectorized'`
- [ ] Gestion erreurs (marquage `error` si échec)

### T7: Endpoints API
**Objectif** : Exposer le fonctionnement
- [ ] Ajouter routes dans OpenAPI (`openapi/api.yaml`)
- [ ] Contrôleur `POST /{org}/emails/sync` - déclenche synchro
- [ ] Contrôleur `GET /{org}/emails/sync-status` - statut synchro
- [ ] Contrôleur CRUD comptes email
- [ ] Contrôleur consultation emails (liste/détail)
- [ ] Génération code depuis OpenAPI
- [ ] Validation JWT + org

### T8: Intégration FileStorageService
**Objectif** : Stocker les pièces jointes
- [ ] Téléchargement PJ depuis Gmail (format binaire)
- [ ] Stockage via `FileStorageService.store_file()`
- [ ] Génération URL/thumbnail si applicable
- [ ] Nettoyage fichiers temporaires après traitement

### T9: Tests & Validation
**Objectif** : S'assurer de la robustesse
- [ ] Tests unitaires services (mocks Gmail API)
- [ ] Tests intégration synchro (compte de test Gmail)
- [ ] Tests vectorisation (embeddings cohérents)
- [ ] Test charge (polling 100+ emails)
- [ ] Tests polling historique par période (gestion de l'existant)

### T10: Documentation & Monitoring
**Objectif** : Faciliter maintenance et debug
- [ ] Métriques synchro (temps, volume, erreurs)
- [ ] Logging structuré (JSON) pour audit
- [ ] Documenter procédure renouvellement OAuth
- [ ] Documenter troubleshooting connexions

---

## Dépendances avec autres modules

### Modules existants utilisés
- `FileStorageService` : Stockage temporaire PJ
- `GenericDocumentExtractor` : OCR des pièces jointes
- `CapabilityChecker` : Permissions (`emails:read`, `emails:sync`)

### Interface avec module Secrétariat (futur)
```python
# Le module Secrétariat utilisera ces données :
emails_to_analyze = await db.query("""
    SELECT * FROM emails 
    WHERE processing_status = 'vectorized'
    AND id NOT IN (SELECT email_id FROM secretariat_analysis)
""")
```

---

## Conventions & Patterns

### Nommage
- Tables : `emails`, `email_accounts`, `email_attachments`, `email_embeddings`
- Services : `gmail_client.py`, `sync_service.py`, `embedding_service.py`
- Types ENUM : `email_status`, `embedding_source`

### Gestion des erreurs
- Erreur Gmail API → `processing_status = 'error'` + log
- Erreur vectorisation → Marquage + retry possible
- OAuth expired → Notification admin + refresh token

---

## Notes de conception

### Pourquoi séparation Email / Secrétariat ?

1. **Testabilité** : On peut tester l'ingestion sans logique métier complexe
2. **Évolution** : Gmail peut être remplacé par Microsoft 365 sans toucher au Secrétariat
3. **Performance** : Vectorisation = batch technique, Secrétariat = temps réel
4. **Équipe** : Devops/data = Emails, Métier/IA = Secrétariat

### Pourquoi table `email_embeddings` séparée ?

Un email peut générer N embeddings :
- 1 par chunk du corps du mail
- 1 par chunk de chaque pièce jointe

La recherche vectorielle est plus performante et précise avec cette séparation.

### Pourquoi polling synchrone HTTP ?

- **Simplicité** : Pas d'infrastructure Celery/Redis à gérer
- **Cloud Run compatible** : Scale-to-zero préservé
- **Contrôle** : Déclenchement manuel ou via cron externe (Cloud Scheduler)

---

## Références

- [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)
- [Supabase pgvector](https://supabase.com/docs/guides/database/extensions/pgvector)
- `docs/SECRETARIAT.md` - Module décisions métier (futur)
- `docs/CAPABILITIES.md` - Système de permissions
- `docs/gemini-extraction-agent.md` - OCR existant
