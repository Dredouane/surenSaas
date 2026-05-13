# AO_SPECIFICATION_V2 — Moteur de Pricing Prédictif et de Benchmarking de Candidatures

> **Source of Truth** — Version 2.0
> **Statut** : En cours de développement
> **Remplace** : `docs/AO.md` (v1 — analyse documentaire simple, archivée)
> **Date** : 2026-05-11

---

## Table des Matières

1. [Vision & Contexte Métier](#1-vision--contexte-métier)
2. [Architecture des Données](#2-architecture-des-données)
3. [Workflow d'Ingestion & Processing](#3-workflow-dingestion--processing)
4. [Stratégie RAG & Knowledge Base](#4-stratégie-rag--knowledge-base)
5. [Features de l'Interface](#5-features-de-linterface)
6. [Stack Technique](#6-stack-technique)
7. [Backlog d'Implémentation](#7-backlog-dimplémentation)
8. [Décisions Architecturales (ADR)](#8-décisions-architecturales-adr)

---

## 1. Vision & Contexte Métier

### 1.1 Problème à résoudre

Le client (groupement de PME — diagnostics immobiliers et travaux, Île-de-France) répond à des appels d'offres en fixant ses prix unitaires "à l'instinct" ou par habitude. Il ne dispose d'aucune vision structurée de :

- Ses propres prix historiques (gagnants vs perdants)
- Les prix des concurrents (partenaires ou entreprises identifiées via ATTRI)
- L'écart entre son offre globale et l'offre retenue (le "Gap de compétitivité")

### 1.2 Solution cible

Un **Moteur de Pricing Prédictif et de Benchmarking** qui :

1. Ingère les dossiers passés (BPU, DQE, CCTP, RC, ATTRI) sous forme de PDF, Excel ou DOCX
2. Extrait et contextualise chaque **Ligne de Prix** (prix + unité + contraintes techniques associées)
3. Normalise les libellés sur une **Taxonomie Métier** unifiée (ex: `DIAG_PLOMB_CREP`)
4. Alimente une **Knowledge Base de Référence** consultable
5. Permet à l'utilisateur de voir, pour n'importe quelle prestation : `prix moyen KB | dernier prix client | prix gagnant` avec traçabilité vers le document source

### 1.3 Périmètre métier

| Domaine | Codes métier de niveau 1 |
|---|---|
| Diagnostics | DIAG_AMIANTE, DIAG_PLOMB, DIAG_DPE, DIAG_ELEC, DIAG_GAZ, DIAG_TERMITES, DIAG_PEMD |
| Travaux | TRAV_DEMO, TRAV_DESAMIANTAGE, TRAV_REHAB, TRAV_SECOND_OEUVRE |

Zone géographique : Île-de-France, granularité **Département** (75, 77, 78, 91, 92, 93, 94, 95).

---

## 2. Architecture des Données

### 2.1 Modèle Parent-Enfant

```
ao_dossiers (Parent — publié par l'Acheteur)
    └── ao_candidatures (Enfants — réponses déposées)
            ├── Candidature "Notre Offre" (type: OUR_OFFER)
            ├── Candidature "Concurrent A" (type: COMPETITOR)
            └── Candidature "Partenaire B" (type: PARTNER)
```

**Règle métier** : Un `ao_dossier` représente le dossier de consultation publié par l'acheteur (contient le BPU vierge, CCTP, RC). Les `ao_candidatures` sont les réponses financières déposées — qu'elles émanent du client, d'un concurrent identifié via ATTRI, ou d'un partenaire.

### 2.2 Entité Centrale — La Ligne de Prix Contextualisée

C'est **l'unité atomique de valeur** du système. Chaque ligne extraite d'un BPU/DQE doit être enrichie de son contexte technique (CCTP) et de son statut compétitif (via ATTRI).

#### Schéma JSON cible d'une Ligne de Prix

```json
{
  "id": "uuid",
  "candidature_id": "uuid",
  "dossier_id": "uuid",
  "org_id": "uuid",

  "designation": "Diagnostic amiante avant travaux — immeuble collectif",
  "code_metier": "DIAG_AMIANTE_AVT_TRAVAUX",
  "categorie_niveau1": "DIAG_AMIANTE",
  "categorie_niveau2": "AVANT_TRAVAUX",

  "prix_unitaire_ht": 145.00,
  "unite": "U",
  "quantite": 12.0,
  "prix_total_ht": 1740.00,

  "zone_geo": "92",
  "type_acheteur": "BAILLEUR_SOCIAL",
  "date_ao": "2024-03-15",

  "statut_candidature": "GAGNANT",

  "source_extraction": {
    "r2_file_id": "ao/2024/bpu_lot2.xlsx",
    "page_number": 3,
    "row_number": 12,
    "sheet_name": "BPU",
    "formule_brute": "=C12*D12",
    "valeur_calculee": 145.00
  },

  "contexte_technique": {
    "cctp_section_id": "uuid",
    "justification_snippet": "Les diagnostics amiante AVT seront réalisés selon la norme NF X46-020...",
    "confidence_score": 0.91
  },

  "normalisation": {
    "designation_originale": "Constat Amiante Avant Travaux immeuble > 10 lots",
    "mapped_by": "agent_synthetiseur",
    "confidence_score": 0.88
  },

  "validation_humain": "VALIDE",
  "created_at": "2026-05-11T10:00:00Z"
}
```

### 2.3 Schéma SQL Cible (028_ao_v2.sql)

> **Note** : Ce schéma **remplace** entièrement les tables du fichier `027_ao_tables.sql`. Migration : DROP + RECREATE (pas de données prod à préserver).

#### ENUMs

```sql
-- Type de candidature
CREATE TYPE ao_candidature_type AS ENUM (
    'OUR_OFFER',      -- Offre déposée par notre client
    'COMPETITOR',     -- Offre d'un concurrent (source: ATTRI + BPU reconstitué)
    'PARTNER'         -- BPU d'une entreprise partenaire uploadé manuellement
);

-- Statut d'une candidature
CREATE TYPE ao_candidature_statut AS ENUM (
    'EN_COURS',       -- Candidature en cours d'analyse
    'GAGNANT',        -- ATTRI confirme que cette offre a été retenue
    'PERDANT',        -- ATTRI reçu, offre non retenue
    'INCONNU'         -- Pas encore d'ATTRI
);

-- Types de documents acceptés
CREATE TYPE ao_document_type AS ENUM (
    'BPU',            -- Bordereau des Prix Unitaires
    'DQE',            -- Détail Quantitatif Estimatif
    'CCTP',           -- Cahier des Clauses Techniques Particulières
    'RC',             -- Règlement de Consultation
    'ATTRI',          -- Avis d'Attribution
    'AUTRE'
);

-- Statut de traitement d'un document
CREATE TYPE ao_traitement_statut AS ENUM (
    'PENDING',
    'PROCESSING',
    'PROCESSED',
    'ERROR'
);

-- Statut de validation HITL d'une ligne de prix
CREATE TYPE ao_validation_statut AS ENUM (
    'AUTO_VALIDE',    -- Confiance >= 85%, validé automatiquement
    'EN_ATTENTE',     -- Confiance < 85%, attend validation humaine
    'VALIDE',         -- Validé manuellement par l'utilisateur
    'REJETE',         -- Rejeté manuellement (données erronées)
    'CORRIGE'         -- Corrigé manuellement avant validation
);

-- Statut de traitement global du dossier
CREATE TYPE ao_dossier_statut AS ENUM (
    'INCOMPLET',      -- Documents obligatoires manquants
    'PRET',           -- Tous les docs obligatoires présents, analyse possible
    'EN_ANALYSE',     -- Agent Synthétiseur en cours
    'ANALYSE_OK',     -- Analyse terminée, lignes injectées en KB
    'ERROR'
);
```

#### Table `ao_dossiers` — Parent

```sql
CREATE TABLE ao_dossiers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Identification du dossier de consultation
    reference_ao            TEXT,                          -- Ex: "SIEMP-2024-LOT3"
    nom_projet              TEXT NOT NULL,
    acheteur_nom            TEXT,                          -- Nom de l'entité publique/privée
    type_acheteur           TEXT,                          -- BAILLEUR_SOCIAL, COLLECTIVITE, PRIVE, etc.
    zone_geo                TEXT,                          -- Code département IDF (ex: "92")
    date_publication        DATE,
    date_limite_remise      DATE,

    -- Statut pipeline
    statut                  ao_dossier_statut DEFAULT 'INCOMPLET',
    docs_obligatoires_ok    BOOLEAN DEFAULT FALSE,         -- BPU + DQE + CCTP présents
    candidature_count       INTEGER DEFAULT 0,
    prix_line_count         INTEGER DEFAULT 0,

    -- Données ATTRI (si reçu)
    attri_montant_retenu    DECIMAL(15,2),                 -- Montant global HT de l'offre gagnante
    attri_gagnant_nom       TEXT,                          -- Nom de l'entreprise retenue

    created_by              UUID REFERENCES users(id),
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ao_dossiers_org ON ao_dossiers(org_id);
CREATE INDEX idx_ao_dossiers_zone_geo ON ao_dossiers(zone_geo);
CREATE INDEX idx_ao_dossiers_statut ON ao_dossiers(statut);
```

#### Table `ao_candidatures` — Enfants

```sql
CREATE TABLE ao_candidatures (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dossier_id              UUID NOT NULL REFERENCES ao_dossiers(id) ON DELETE CASCADE,
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Identification de l'offreur
    candidat_nom            TEXT NOT NULL,                 -- "Notre Client", "Bouygues Diag", etc.
    type_candidature        ao_candidature_type NOT NULL DEFAULT 'OUR_OFFER',
    statut                  ao_candidature_statut DEFAULT 'INCONNU',

    -- Données financières consolidées
    montant_total_ht        DECIMAL(15,2),                 -- Total DQE HT
    gap_vs_attri_pct        DECIMAL(5,2),                  -- Écart % vs montant ATTRI

    -- Pipeline docs
    document_count          INTEGER DEFAULT 0,
    prix_line_count         INTEGER DEFAULT 0,
    has_bpu                 BOOLEAN DEFAULT FALSE,
    has_dqe                 BOOLEAN DEFAULT FALSE,

    created_by              UUID REFERENCES users(id),
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ao_candidatures_dossier ON ao_candidatures(dossier_id);
CREATE INDEX idx_ao_candidatures_org ON ao_candidatures(org_id);
CREATE INDEX idx_ao_candidatures_statut ON ao_candidatures(statut);
```

#### Table `ao_documents` — Documents par Candidature

```sql
CREATE TABLE ao_documents (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidature_id          UUID NOT NULL REFERENCES ao_candidatures(id) ON DELETE CASCADE,
    dossier_id              UUID NOT NULL REFERENCES ao_dossiers(id) ON DELETE CASCADE,
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    type_doc                ao_document_type NOT NULL,
    nom_fichier             TEXT NOT NULL,
    mime_type               TEXT,                          -- application/pdf, application/xlsx, etc.
    taille_bytes            BIGINT,
    r2_file_id              TEXT,                          -- Clé dans Cloudflare R2
    checksum_sha256         TEXT,

    -- Extraction
    contenu_texte           TEXT,                          -- Texte brut extrait (OCR ou parse)
    nombre_pages            INTEGER,
    statut_traitement       ao_traitement_statut DEFAULT 'PENDING',
    message_erreur          TEXT,
    date_extraction         TIMESTAMPTZ,
    model_extraction        TEXT,                          -- Ex: "gemini-2.5-flash"

    -- Metadata format
    metadata                JSONB DEFAULT '{}',            -- Ex: {sheets: ["BPU", "DQE"], rows: 142}

    uploaded_by             UUID REFERENCES users(id),
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ao_documents_candidature ON ao_documents(candidature_id);
CREATE INDEX idx_ao_documents_type ON ao_documents(type_doc);
CREATE INDEX idx_ao_documents_statut ON ao_documents(statut_traitement);
CREATE INDEX idx_ao_documents_metadata ON ao_documents USING GIN(metadata);
```

#### Table `ao_price_lines` — Entité Centrale

```sql
CREATE TABLE ao_price_lines (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidature_id          UUID NOT NULL REFERENCES ao_candidatures(id) ON DELETE CASCADE,
    dossier_id              UUID NOT NULL REFERENCES ao_dossiers(id) ON DELETE CASCADE,
    document_id             UUID NOT NULL REFERENCES ao_documents(id) ON DELETE CASCADE,
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Désignation brute et normalisée
    designation_originale   TEXT NOT NULL,
    designation_normalisee  TEXT,
    code_metier             TEXT,                          -- Ex: DIAG_AMIANTE_AVT_TRAVAUX
    categorie_niveau1       TEXT,                          -- Ex: DIAG_AMIANTE
    categorie_niveau2       TEXT,                          -- Ex: AVANT_TRAVAUX

    -- Prix
    prix_unitaire_ht        DECIMAL(15,4),
    unite                   TEXT,                          -- U, m², ml, forfait, etc.
    quantite                DECIMAL(15,4),
    prix_total_ht           DECIMAL(15,4),

    -- Contexte AO
    zone_geo                TEXT,                          -- Hérité du ao_dossier
    type_acheteur           TEXT,                          -- Hérité du ao_dossier
    date_ao                 DATE,                          -- Hérité de ao_dossier.date_publication
    statut_candidature      ao_candidature_statut,         -- Hérité de ao_candidatures.statut

    -- Traçabilité source (pour ouvrir le doc à la bonne page)
    r2_file_id              TEXT,                          -- Copie de ao_documents.r2_file_id
    page_number             INTEGER,
    row_number              INTEGER,                       -- Numéro de ligne (Excel)
    sheet_name              TEXT,                          -- Nom de l'onglet (Excel)

    -- Extraction Excel spécifique
    formule_brute           TEXT,                          -- Ex: "=C12*D12"
    valeur_calculee         DECIMAL(15,4),                 -- Valeur calculée au moment de l'extraction

    -- Normalisation IA
    normalisation_confiance FLOAT CHECK (normalisation_confiance BETWEEN 0 AND 1),
    normalisation_model     TEXT,

    -- Validation HITL
    validation_statut       ao_validation_statut DEFAULT 'EN_ATTENTE',
    valide_par              UUID REFERENCES users(id),
    date_validation         TIMESTAMPTZ,
    correction_notes        TEXT,

    -- Flag KB : injecté en Knowledge Base seulement si validé
    in_knowledge_base       BOOLEAN DEFAULT FALSE,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ao_price_lines_candidature ON ao_price_lines(candidature_id);
CREATE INDEX idx_ao_price_lines_dossier ON ao_price_lines(dossier_id);
CREATE INDEX idx_ao_price_lines_code_metier ON ao_price_lines(code_metier);
CREATE INDEX idx_ao_price_lines_zone_geo ON ao_price_lines(zone_geo);
CREATE INDEX idx_ao_price_lines_statut_candidature ON ao_price_lines(statut_candidature);
CREATE INDEX idx_ao_price_lines_validation ON ao_price_lines(validation_statut);
CREATE INDEX idx_ao_price_lines_kb ON ao_price_lines(in_knowledge_base);
-- Full-text search sur désignation
CREATE INDEX idx_ao_price_lines_fts ON ao_price_lines
    USING GIN(to_tsvector('french', COALESCE(designation_normalisee, '') || ' ' || designation_originale));
```

#### Table `ao_price_technical_context` — Jointure BPU ↔ CCTP

```sql
CREATE TABLE ao_price_technical_context (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_line_id           UUID NOT NULL REFERENCES ao_price_lines(id) ON DELETE CASCADE,
    cctp_section_id         UUID NOT NULL REFERENCES ao_embeddings(id) ON DELETE CASCADE,

    -- Résultat du matching sémantique
    confidence_score        FLOAT NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    justification_snippet   TEXT NOT NULL,                 -- Extrait CCTP expliquant le lien

    -- Traçabilité de l'agent
    matched_by_model        TEXT,                          -- Ex: "gemini-2.5-pro"
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ao_ptc_price_line ON ao_price_technical_context(price_line_id);
CREATE INDEX idx_ao_ptc_cctp_section ON ao_price_technical_context(cctp_section_id);
CREATE INDEX idx_ao_ptc_confidence ON ao_price_technical_context(confidence_score);
```

#### Table `ao_embeddings` — Vecteurs pour RAG

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE ao_embeddings (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id             UUID NOT NULL REFERENCES ao_documents(id) ON DELETE CASCADE,
    candidature_id          UUID NOT NULL REFERENCES ao_candidatures(id) ON DELETE CASCADE,
    dossier_id              UUID NOT NULL REFERENCES ao_dossiers(id) ON DELETE CASCADE,
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Contenu du chunk
    content                 TEXT NOT NULL,
    embedding               VECTOR(768),                   -- Gemini text-embedding-004

    -- Chunking
    chunk_index             INTEGER DEFAULT 0,
    chunk_total             INTEGER DEFAULT 1,

    -- Metadata obligatoires pour filtrage SQL avant recherche vectorielle
    doc_type                ao_document_type NOT NULL,
    page_number             INTEGER,
    code_metier             TEXT,                          -- Si chunk issu d'un BPU
    zone_geo                TEXT,
    categorie               TEXT,
    r2_file_id              TEXT,                          -- Pour traçabilité source

    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Index HNSW pour la recherche cosine
CREATE INDEX idx_ao_embeddings_vector ON ao_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index pour filtrage par metadata avant recherche vectorielle
CREATE INDEX idx_ao_embeddings_org ON ao_embeddings(org_id);
CREATE INDEX idx_ao_embeddings_dossier ON ao_embeddings(dossier_id);
CREATE INDEX idx_ao_embeddings_doc_type ON ao_embeddings(doc_type);
CREATE INDEX idx_ao_embeddings_code_metier ON ao_embeddings(code_metier);
CREATE INDEX idx_ao_embeddings_zone_geo ON ao_embeddings(zone_geo);
```

#### Fonctions SQL Utilitaires

```sql
-- Mise à jour des compteurs sur ao_dossiers
CREATE OR REPLACE FUNCTION update_dossier_counters(p_dossier_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE ao_dossiers SET
        candidature_count = (SELECT COUNT(*) FROM ao_candidatures WHERE dossier_id = p_dossier_id),
        prix_line_count   = (SELECT COUNT(*) FROM ao_price_lines WHERE dossier_id = p_dossier_id AND in_knowledge_base = TRUE),
        updated_at        = NOW()
    WHERE id = p_dossier_id;
END;
$$ LANGUAGE plpgsql;

-- Mise à jour docs_obligatoires_ok sur ao_dossiers
CREATE OR REPLACE FUNCTION check_dossier_completude(p_dossier_id UUID)
RETURNS VOID AS $$
DECLARE
    v_has_bpu   BOOLEAN;
    v_has_dqe   BOOLEAN;
    v_has_cctp  BOOLEAN;
BEGIN
    SELECT
        BOOL_OR(d.type_doc = 'BPU') AS has_bpu,
        BOOL_OR(d.type_doc = 'DQE') AS has_dqe,
        BOOL_OR(d.type_doc = 'CCTP') AS has_cctp
    INTO v_has_bpu, v_has_dqe, v_has_cctp
    FROM ao_documents d
    JOIN ao_candidatures c ON d.candidature_id = c.id
    WHERE c.dossier_id = p_dossier_id
      AND d.statut_traitement = 'PROCESSED';

    UPDATE ao_dossiers SET
        docs_obligatoires_ok = (v_has_bpu AND v_has_dqe AND v_has_cctp),
        statut = CASE
            WHEN (v_has_bpu AND v_has_dqe AND v_has_cctp) THEN 'PRET'
            ELSE 'INCOMPLET'
        END,
        updated_at = NOW()
    WHERE id = p_dossier_id;
END;
$$ LANGUAGE plpgsql;

-- Recherche vectorielle avec pré-filtrage metadata
CREATE OR REPLACE FUNCTION search_ao_embeddings(
    p_org_id        UUID,
    p_query_vector  VECTOR(768),
    p_doc_type      ao_document_type DEFAULT NULL,
    p_zone_geo      TEXT DEFAULT NULL,
    p_code_metier   TEXT DEFAULT NULL,
    p_limit         INTEGER DEFAULT 10
)
RETURNS TABLE (
    id              UUID,
    document_id     UUID,
    content         TEXT,
    similarity      FLOAT,
    doc_type        ao_document_type,
    page_number     INTEGER,
    r2_file_id      TEXT,
    code_metier     TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id, e.document_id, e.content,
        1 - (e.embedding <=> p_query_vector) AS similarity,
        e.doc_type, e.page_number, e.r2_file_id, e.code_metier
    FROM ao_embeddings e
    WHERE e.org_id = p_org_id
      AND (p_doc_type IS NULL  OR e.doc_type   = p_doc_type)
      AND (p_zone_geo IS NULL  OR e.zone_geo   = p_zone_geo)
      AND (p_code_metier IS NULL OR e.code_metier = p_code_metier)
    ORDER BY e.embedding <=> p_query_vector
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Vue Knowledge Base — Prix de référence par code_metier
CREATE OR REPLACE VIEW ao_kb_prix_reference AS
SELECT
    pl.org_id,
    pl.code_metier,
    pl.categorie_niveau1,
    pl.categorie_niveau2,
    pl.unite,
    pl.zone_geo,
    pl.type_acheteur,

    COUNT(*) FILTER (WHERE pl.statut_candidature = 'GAGNANT')  AS nb_prix_gagnants,
    COUNT(*) FILTER (WHERE pl.statut_candidature = 'PERDANT')  AS nb_prix_perdants,
    COUNT(*) FILTER (WHERE pl.statut_candidature = 'INCONNU')  AS nb_prix_inconnus,
    COUNT(*)                                                     AS nb_total,

    -- Prix gagnants
    AVG(pl.prix_unitaire_ht)  FILTER (WHERE pl.statut_candidature = 'GAGNANT') AS prix_moyen_gagnant,
    MIN(pl.prix_unitaire_ht)  FILTER (WHERE pl.statut_candidature = 'GAGNANT') AS prix_min_gagnant,
    MAX(pl.prix_unitaire_ht)  FILTER (WHERE pl.statut_candidature = 'GAGNANT') AS prix_max_gagnant,

    -- Tous statuts
    AVG(pl.prix_unitaire_ht)                                     AS prix_moyen_global,

    -- Dernier prix client (OUR_OFFER uniquement)
    (SELECT pl2.prix_unitaire_ht
     FROM ao_price_lines pl2
     JOIN ao_candidatures c2 ON pl2.candidature_id = c2.id
     WHERE pl2.org_id = pl.org_id
       AND pl2.code_metier = pl.code_metier
       AND c2.type_candidature = 'OUR_OFFER'
       AND pl2.in_knowledge_base = TRUE
     ORDER BY pl2.created_at DESC
     LIMIT 1
    ) AS dernier_prix_client,

    MAX(pl.date_ao) AS date_derniere_reference

FROM ao_price_lines pl
WHERE pl.in_knowledge_base = TRUE
GROUP BY pl.org_id, pl.code_metier, pl.categorie_niveau1, pl.categorie_niveau2, pl.unite, pl.zone_geo, pl.type_acheteur;
```

---

## 3. Workflow d'Ingestion & Processing

### 3.1 Vue d'ensemble du Pipeline

```
[Upload UI]
    │
    ▼
[Worker Extraction Brute]
    ├── PDF → OCR Gemini Flash (texte + numéro de page)
    ├── Excel (.xlsx/.xls) → openpyxl (valeurs + formules + nom d'onglet)
    └── DOCX → python-docx (texte structuré par section)
    │
    ▼
[Vectorisation]
    └── Chunking sémantique → Gemini text-embedding-004 → ao_embeddings
    │
    ▼
[Check Complétude Dossier]
    └── BPU + DQE + CCTP présents et PROCESSED ? → Bouton "Lancer l'Analyse" activé
    │
    ▼ (déclenché manuellement par l'utilisateur)
[Agent Synthétiseur]
    ├── Extraction Lignes de Prix (BPU/DQE) → ao_price_lines (brut)
    ├── Normalisation Taxonomie (Gemini Pro) → code_metier assigné
    ├── Matching BPU ↔ CCTP (similarité cosine) → ao_price_technical_context
    └── Calcul Gap vs ATTRI (si présent) → ao_candidatures.gap_vs_attri_pct
    │
    ▼
[HITL — Validation Humaine]
    └── Lignes avec confidence_score < 0.85 → statut EN_ATTENTE → Interface de validation
    │
    ▼ (après validation)
[Injection Knowledge Base]
    └── ao_price_lines.in_knowledge_base = TRUE → Visible dans Explorateur de Prix
```

### 3.2 Phase 1 — Workers d'Extraction Brute

#### Worker PDF (OCR Gemini)

- **Modèle** : `gemini-2.5-flash-lite` (rapide, cost-efficient)
- **Input** : Fichier PDF uploadé dans R2
- **Output** : Texte extrait avec métadonnées de page
- **Format de sortie** : `{"pages": [{"page_number": 1, "content": "..."}]}`
- **Cas BPU PDF** : Extraction structurée en tableau (prompt spécifique)

#### Worker Excel (openpyxl)

- **Librairie** : `openpyxl` (lecture valeurs + formules)
- **Mode lecture** : `load_workbook(filename, data_only=False)` pour les formules, `data_only=True` pour les valeurs calculées — **les deux lectures sont effectuées**
- **Output par ligne** :
  ```json
  {
    "sheet": "BPU",
    "row": 12,
    "col_designation": "Diagnostic amiante AVT — immeuble collectif",
    "col_unite": "U",
    "col_quantite": 12,
    "col_pu_value": 145.00,
    "col_pu_formula": "=ARRONDI(C12/D12,2)",
    "col_total_value": 1740.00,
    "col_total_formula": "=E12*F12"
  }
  ```
- **Détection des onglets** : Scan automatique des noms d'onglets contenant "BPU", "DQE", "Prix", "Bordereau"

#### Worker DOCX (python-docx)

- **Librairie** : `python-docx`
- **Stratégie** : Extraction par section/heading pour respecter la structure du CCTP
- **Output** : `{"sections": [{"heading": "3.2 Diagnostic Amiante", "content": "..."}]}`

### 3.3 Phase 2 — Chunking & Vectorisation

| Type de Document | Stratégie de Chunking | Taille Cible | Overlap |
|---|---|---|---|
| CCTP / RC | Sémantique/Structurel (par section) | 800–1000 tokens | 15–20% (~150 tokens) |
| BPU / DQE | 1 ligne = 1 chunk | Variable | 0 (atomique) |

**Metadata obligatoires par vecteur** :
```json
{
  "ao_id": "uuid",
  "doc_type": "CCTP",
  "page_number": 12,
  "r2_file_id": "ao/2024/.../cctp.pdf",
  "code_metier": null,
  "zone_geo": "92",
  "categorie": "DIAG_AMIANTE"
}
```

### 3.4 Phase 3 — Agent Synthétiseur

C'est le cœur du moteur. Il est déclenché **manuellement** par l'utilisateur une fois les documents obligatoires traités.

#### 3.4.1 Extraction et Normalisation des Lignes de Prix

**Prompt système** : Expert taxonomie diagnostics immobiliers IDF. Pour chaque ligne de prix brute, assigner un `code_metier` standardisé.

**Règles de mapping** :
- `"Constat Amiante Avant Travaux"` → `DIAG_AMIANTE_AVT_TRAVAUX`
- `"Diagnostic Plomb CREP"` → `DIAG_PLOMB_CREP`
- `"Constat d'exposition au Plomb"` → `DIAG_PLOMB_CREP`
- `"DPE Collectif"` → `DIAG_DPE_COLLECTIF`

**Output attendu** :
```json
{
  "code_metier": "DIAG_AMIANTE_AVT_TRAVAUX",
  "categorie_niveau1": "DIAG_AMIANTE",
  "categorie_niveau2": "AVANT_TRAVAUX",
  "designation_normalisee": "Diagnostic amiante avant travaux",
  "confidence_score": 0.92
}
```

#### 3.4.2 Matching BPU ↔ CCTP

**Algorithme** :
1. Pour chaque `ao_price_line`, générer un embedding de la `designation_normalisee`
2. Recherche cosine dans `ao_embeddings` filtrée sur `doc_type = 'CCTP'` du même `dossier_id`
3. Prendre le top-3 résultats avec `similarity > 0.75`
4. Pour chaque match, Gemini génère le `justification_snippet`
5. Insérer dans `ao_price_technical_context`

**Seuil de confiance** : `0.85`
- `>= 0.85` → `validation_statut = AUTO_VALIDE`, `in_knowledge_base = TRUE`
- `< 0.85` → `validation_statut = EN_ATTENTE` → HITL requis

#### 3.4.3 Calcul du Gap vs ATTRI

Si un document `ATTRI` est présent dans le dossier :
```
gap_vs_attri_pct = ((montant_total_ht - attri_montant_retenu) / attri_montant_retenu) * 100
```
Stocké sur `ao_candidatures.gap_vs_attri_pct`. Un gap positif signifie que l'offre est au-dessus du prix retenu.

### 3.5 Phase 4 — HITL (Human-In-The-Loop)

**Déclencheur** : Toute `ao_price_line` avec `validation_statut = EN_ATTENTE`

**Interface** : Tableau de validation avec colonnes :
| Désignation originale | Code Métier proposé | Confiance | Actions |
|---|---|---|---|
| "Constat amiante parties communes" | DIAG_AMIANTE_PARTIES_COM | 72% | ✓ Valider \| ✗ Rejeter \| ✎ Corriger |

**Actions disponibles** :
- **Valider** : `validation_statut = VALIDE`, `in_knowledge_base = TRUE`
- **Rejeter** : `validation_statut = REJETE`, ligne exclue de la KB
- **Corriger** : Modifier le `code_metier` ou le `prix_unitaire_ht`, puis valider → `validation_statut = CORRIGE`

---

## 4. Stratégie RAG & Knowledge Base

### 4.1 Deux niveaux de KB

| Niveau | Portée | Contenu | Usage |
|---|---|---|---|
| **KB Locale (Dossier)** | Un seul `ao_dossier` | CCTP + RC vectorisés | Matching BPU↔CCTP de l'Agent Synthétiseur |
| **KB Cross-AO (Marché)** | Tous les dossiers de l'org | Lignes de prix validées (`in_knowledge_base = TRUE`) | Benchmarking, Explorateur de Prix |

### 4.2 Traçabilité Source (Cliquable)

Chaque `ao_price_line` et chaque vecteur dans `ao_embeddings` conservent :
- `r2_file_id` : clé R2 pour générer une URL signée
- `page_number` : numéro de page PDF pour ouverture directe
- `row_number` + `sheet_name` : position exacte dans le fichier Excel

**Endpoint dédié** : `GET /ao/documents/{doc_id}/source?page={n}` → URL signée R2 avec fragment de page.

### 4.3 Modèle d'Embedding

- **Modèle** : `models/text-embedding-004` (Gemini, Google AI)
- **Dimensions** : 768
- **Implémentation** : Remplacement du placeholder `[0.0]*768` dans `ao_rag_service.py`
- **Client** : `google.generativeai` (déjà présent dans le codebase)

---

## 5. Features de l'Interface

### 5.1 Liste des Dossiers AO

**Route** : `/dashboard/ao`

Tableau listant les `ao_dossiers` avec :
- Référence AO, Nom projet, Acheteur, Zone géo, Date limite
- Statut pipeline (badge coloré : INCOMPLET / PRET / EN_ANALYSE / ANALYSE_OK)
- Nombre de candidatures | Nombre de lignes en KB
- CTA "Nouveau Dossier" → formulaire de création

### 5.2 Détail d'un Dossier AO

**Route** : `/dashboard/ao/[dossierId]`

Onglets :
1. **Vue d'ensemble** : métadonnées dossier, liste candidatures, Gap vs ATTRI si disponible
2. **Documents** : tableau des documents uploadés par candidature, statut traitement, bouton "Lancer l'Analyse" (actif si `docs_obligatoires_ok = TRUE`)
3. **Validation HITL** : tableau des lignes `EN_ATTENTE` (visible seulement si des lignes sont à valider)
4. **Prix Extraits** : tableau de toutes les `ao_price_lines` validées du dossier

### 5.3 Explorateur de Prix (KB Référentielle)

**Route** : `/dashboard/ao/explorer`

Interface de consultation de la Knowledge Base globale.

**Composants** :

#### Barre de Recherche Sémantique
- Input texte libre → recherche dans `ao_embeddings` (RAG) + full-text sur `designation_normalisee`
- Filtres : Zone géo (département), Type acheteur, Catégorie niveau 1, Période

#### Carte de Résultat par Code Métier

Pour chaque `code_metier` trouvé, afficher :

```
┌─────────────────────────────────────────────────────────────┐
│  DIAG_AMIANTE_AVT_TRAVAUX                                   │
│  "Diagnostic amiante avant travaux"                         │
│  Zone: 92 | Acheteur: Bailleur Social | Unité: U            │
│                                                             │
│  Prix moyen (gagnants)  │  Dernier prix client  │  Min/Max  │
│        145 € HT         │       138 € HT        │  120–180  │
│                                                             │
│  Basé sur 12 références  [Voir les sources →]               │
└─────────────────────────────────────────────────────────────┘
```

**Données affichées** (issues de la vue `ao_kb_prix_reference`) :
- Prix moyen des offres gagnantes
- Dernier prix utilisé par notre client (`OUR_OFFER`)
- Prix minimum et maximum observés
- Nombre de références en KB
- Bouton "Voir les sources" → liste des références avec lien cliquable vers doc source (page précise)

---

## 6. Stack Technique

### 6.1 Extraction de Documents

| Format | Librairie | Notes |
|---|---|---|
| PDF | Gemini 2.5 Flash (OCR) | Via `generic_extractor.py` existant |
| Excel (.xlsx) | `openpyxl` | Deux passes : formules + valeurs |
| Excel (.xls) | `xlrd` | Legacy format |
| DOCX | `python-docx` | Extraction par heading/section |

### 6.2 IA & Embeddings

| Usage | Modèle | Notes |
|---|---|---|
| OCR | `gemini-2.5-flash-lite` | Rapide, cost-efficient |
| Normalisation Taxonomie | `gemini-2.5-pro` | Précision sur termes métier |
| Matching BPU↔CCTP | `gemini-2.5-pro` | Génération du justification_snippet |
| Embeddings | `models/text-embedding-004` | 768 dims, Gemini API |

### 6.3 Stockage

- **Fichiers** : Cloudflare R2 — chemin : `{env}/org/{org_id}/ao/{dossier_id}/{candidature_id}/{filename}`
- **Vecteurs** : pgvector (Supabase) — index HNSW cosine
- **Base de données** : PostgreSQL (Supabase)

### 6.4 Dependencies Python à ajouter

```
openpyxl>=3.1.0
python-docx>=1.1.0
xlrd>=2.0.1
```

---

## 7. Backlog d'Implémentation

### Task 1 — Réparer le RAG (Embedding Réel)

**Fichier** : `surenSaasBack/app/services/ao_rag_service.py`
**Problème** : `_generate_embedding()` retourne `[0.0]*768` (placeholder)
**Solution** : Appel réel à `google.generativeai.embed_content(model="models/text-embedding-004", content=text)`
**Priorité** : CRITIQUE — bloque toute la feature vectorielle

---

### Task 2 — Worker Excel (openpyxl)

**Fichier à créer** : `surenSaasBack/app/services/ao_excel_extractor.py`
**Responsabilités** :
- Détecter les onglets BPU/DQE
- Double lecture (formules + valeurs)
- Détecter automatiquement les colonnes (désignation, unité, quantité, PU, total)
- Retourner une liste de `ExcelPriceLine` avec `formule_brute` + `valeur_calculee`

---

### Task 3 — Worker DOCX

**Fichier à créer** : `surenSaasBack/app/services/ao_docx_extractor.py`
**Responsabilités** :
- Extraction par heading (structure CCTP)
- Retourner `{"sections": [{"heading": "...", "level": 1, "content": "..."}]}`

---

### Task 4 — Refonte DB (028_ao_v2.sql)

**Fichier à créer** : `db/schema/028_ao_v2.sql`
**Actions** :
- DROP des 5 tables `ao_*` existantes (027)
- Créer les 6 nouvelles tables : `ao_dossiers`, `ao_candidatures`, `ao_documents`, `ao_price_lines`, `ao_price_technical_context`, `ao_embeddings`
- Créer les ENUMs, indexes, fonctions SQL et vue `ao_kb_prix_reference`

---

### Task 5 — Agent Synthétiseur

**Fichier à refactoriser** : `surenSaasBack/app/services/ao_lens_engine.py` → remplacé par `ao_synthetiseur.py`
**Fichier à refactoriser** : `surenSaasBack/app/agents/prompts/ao_prompts.py` → garder uniquement les prompts de normalisation et matching
**Responsabilités** :
- Orchestration du pipeline : extraction → normalisation → matching → gap ATTRI
- Gestion du statut `ao_dossiers.statut` pendant le processing

---

### Task 6 — Refonte API Router

**Fichier** : `surenSaasBack/app/api/ao.py`
**Endpoints à conserver/refactoriser** :

| Endpoint | Action |
|---|---|
| `POST /ao/dossiers` | Créer un dossier AO |
| `GET /ao/dossiers` | Lister les dossiers |
| `GET /ao/dossiers/{id}` | Détail dossier |
| `PATCH /ao/dossiers/{id}` | Mise à jour dossier |
| `POST /ao/dossiers/{id}/candidatures` | Ajouter une candidature |
| `POST /ao/candidatures/{id}/documents/upload` | Upload document |
| `POST /ao/dossiers/{id}/analyze` | Déclencher Agent Synthétiseur |
| `GET /ao/candidatures/{id}/price-lines` | Lignes de prix d'une candidature |
| `POST /ao/price-lines/{id}/validate` | Valider/rejeter une ligne HITL |
| `GET /ao/kb/explorer` | Recherche dans la KB référentielle |
| `GET /ao/documents/{id}/source` | URL signée R2 avec page |
| `GET /ao/stats/dashboard` | Stats globales |

---

### Task 7 — Interface HITL (Frontend)

**Composant à créer** : `surenSaasFront/components/ao/HITLValidationTable.tsx`
**Fonctionnalités** :
- Tableau filtrable par statut validation
- Actions en ligne (valider / rejeter / corriger)
- Indicateur de progression (X lignes validées sur Y)
- Badge de confiance coloré (vert >= 85%, orange 70-85%, rouge < 70%)

---

### Task 8 — Explorateur de Prix (Frontend)

**Page à créer** : `surenSaasFront/app/dashboard/ao/explorer/page.tsx`
**Composant à créer** : `surenSaasFront/components/ao/PriceExplorer.tsx`
**Fonctionnalités** :
- Barre de recherche sémantique
- Filtres (zone géo, type acheteur, catégorie)
- Cartes de résultats avec prix moyen / dernier prix client / prix gagnant
- Lien cliquable vers document source (page précise)

---

## 8. Décisions Architecturales (ADR)

| ID | Décision | Contexte | Statut |
|---|---|---|---|
| ADR-01 | Gemini `text-embedding-004` (768d) | Zéro nouvelle dépendance API, déjà dans le codebase | RETENU |
| ADR-02 | Tabula rasa sur les 5 lentilles | La nouvelle spec est un moteur de prix, pas un analyseur documentaire | RETENU |
| ADR-03 | Statut Gagnant/Perdant = manuel | Automatisation différée (matching ATTRI trop fragile en MVP) | RETENU |
| ADR-04 | Seuil HITL = 85% de confiance | Compromis qualité KB vs charge de validation | RETENU |
| ADR-05 | Dossier AO comme entité parent | Sépare le contexte acheteur (invariant) des réponses (variables) | RETENU |
| ADR-06 | 1 ligne BPU = 1 chunk embedding | Atomicité obligatoire — ne jamais couper la relation désignation/montant | RETENU |
| ADR-07 | KB Cross-AO = par org (single-tenant) | Instance mono-org, confidentialité des prix garantie | RETENU |
| ADR-08 | `openpyxl` double-passe (formules + valeurs) | Les formules révèlent les marges et règles de calcul — donnée stratégique | RETENU |
