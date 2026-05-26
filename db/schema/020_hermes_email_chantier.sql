-- ============================================================================
-- Migration 020 : Hermès Email-Agent
-- Ajoute:
--   1. Colonne chantier_id dans email_threads (FK vers chantiers)
--   2. Table chantier_embeddings (pgvector 768 dims)
--   3. RPC match_chantiers (recherche sémantique)
--   4. Table hermes_dispatch_log (audit)
-- ============================================================================

-- 1. Colonne chantier_id dans email_threads
ALTER TABLE email_threads
  ADD COLUMN IF NOT EXISTS chantier_id UUID REFERENCES chantiers(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS hermes_processed_at TIMESTAMPTz,
  ADD COLUMN IF NOT EXISTS hermes_confidence FLOAT,
  ADD COLUMN IF NOT EXISTS hermes_ignore_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_email_threads_chantier_id
  ON email_threads(chantier_id)
  WHERE chantier_id IS NOT NULL;

-- 2. Table chantier_embeddings
CREATE TABLE IF NOT EXISTS chantier_embeddings (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  chantier_id    UUID NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
  content_chunk  TEXT NOT NULL,         -- Texte du chunk embarqué
  embedding      VECTOR(768),           -- text-embedding-004 Matryoshka
  chunk_index    INT NOT NULL DEFAULT 0,
  chunk_total    INT NOT NULL DEFAULT 1,
  model_name     TEXT NOT NULL DEFAULT 'text-embedding-004',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chantier_embeddings_chantier_id
  ON chantier_embeddings(chantier_id);

CREATE INDEX IF NOT EXISTS idx_chantier_embeddings_org_id
  ON chantier_embeddings(org_id);

-- Index HNSW pour la recherche ANN rapide
CREATE INDEX IF NOT EXISTS idx_chantier_embeddings_vector
  ON chantier_embeddings USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 3. Fonction RPC match_chantiers
CREATE OR REPLACE FUNCTION match_chantiers(
  query_embedding VECTOR(768),
  org_id_filter   UUID,
  match_threshold FLOAT DEFAULT 0.70,
  match_count     INT   DEFAULT 5
)
RETURNS TABLE (
  chantier_id  UUID,
  content      TEXT,
  similarity   FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    ce.chantier_id,
    ce.content_chunk,
    1 - (ce.embedding <=> query_embedding) AS similarity
  FROM chantier_embeddings ce
  WHERE ce.org_id = org_id_filter
    AND 1 - (ce.embedding <=> query_embedding) > match_threshold
  ORDER BY ce.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 4. Table hermes_dispatch_log (audit des actions automatiques)
CREATE TABLE IF NOT EXISTS hermes_dispatch_log (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        UUID NOT NULL,
  email_id      UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  chantier_id   UUID REFERENCES chantiers(id) ON DELETE SET NULL,
  action_type   TEXT NOT NULL,  -- 'task_created' | 'expense_created' | 'notification_sent' | 'ignored'
  action_id     UUID,           -- ID de l'objet créé (tache_id ou depense_id)
  payload       JSONB,          -- Données extraites par Hermès
  success       BOOLEAN NOT NULL DEFAULT TRUE,
  error_message TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hermes_log_email_id ON hermes_dispatch_log(email_id);
CREATE INDEX IF NOT EXISTS idx_hermes_log_chantier_id ON hermes_dispatch_log(chantier_id);
