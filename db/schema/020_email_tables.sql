-- 020_email_tables.sql
-- Module Emails : Tables pour ingestion, stockage et vectorisation des emails Gmail
-- Ce module est purement technique (data layer) - pas de logique métier ici
-- La logique métier (Secrétariat IA) sera dans 025_secretariat_tables.sql

-- ============================================
-- EXTENSION PVECTOR (pour embeddings)
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- TYPES ENUM
-- ============================================

-- Statut de traitement d'un email
CREATE TYPE email_status AS ENUM (
    'pending',      -- Reçu, en attente de vectorisation
    'processing',   -- En cours de traitement
    'vectorized',   -- Prêt pour le module Secrétariat
    'error'         -- Erreur lors du traitement
);

-- Type de source pour les embeddings
CREATE TYPE embedding_source AS ENUM (
    'email_body',   -- Contenu du corps du mail
    'attachment'    -- Contenu d'une pièce jointe
);

-- ============================================
-- TABLE : email_accounts
-- Configuration des comptes Gmail par organisation
-- ============================================
CREATE TABLE IF NOT EXISTS email_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Configuration du compte
    email_address TEXT NOT NULL,
    email_address_display TEXT,                    -- Nom d'affichage (optionnel)
    
    -- OAuth2 (refresh token chiffré - à gérer côté applicatif)
    oauth_refresh_token TEXT NOT NULL,
    oauth_token_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Synchronisation
    last_sync_uid BIGINT DEFAULT 0,                -- Dernier UID Gmail synchronisé
    last_sync_at TIMESTAMP WITH TIME ZONE,         -- Dernière synchro
    sync_enabled BOOLEAN DEFAULT true,             -- Activer/désactiver synchro
    
    -- Métadonnées
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Contrainte d'unicité par org/email
    CONSTRAINT unique_email_per_org UNIQUE (org_id, email_address)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_accounts_org ON email_accounts(org_id);
CREATE INDEX IF NOT EXISTS idx_email_accounts_active ON email_accounts(org_id, is_active, sync_enabled);
CREATE INDEX IF NOT EXISTS idx_email_accounts_last_sync ON email_accounts(last_sync_at);

-- Trigger updated_at
CREATE TRIGGER update_email_accounts_updated_at
    BEFORE UPDATE ON email_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TABLE : emails
-- Stockage des emails récupérés
-- ============================================
CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email_account_id UUID NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,
    
    -- Identifiants Gmail natifs
    gmail_thread_id TEXT NOT NULL,                 -- ID du thread (conversation)
    gmail_message_id TEXT UNIQUE NOT NULL,         -- ID unique du message
    gmail_history_id BIGINT,                       -- Pour les notifications push (futur)
    
    -- En-têtes
    subject TEXT,                                  -- Sujet
    subject_cleaned TEXT,                          -- Sujet nettoyé (sans FW:, RE:)
    
    -- Expéditeur
    sender_email TEXT NOT NULL,                    -- Email expéditeur
    sender_name TEXT,                              -- Nom affiché expéditeur
    sender_domain TEXT GENERATED ALWAYS AS (
        split_part(sender_email, '@', 2)
    ) STORED,                                      -- Domaine extrait pour filtrage
    
    -- Destinataires
    recipient_emails TEXT[],                       -- Liste emails destinataires
    cc_emails TEXT[],                              -- Liste emails en copie
    
    -- Dates
    sent_at TIMESTAMP WITH TIME ZONE,              -- Date d'envoi (Gmail)
    received_at TIMESTAMP WITH TIME ZONE,          -- Date de réception
    
    -- Contenu (RAG Mail - nettoyé pour vectorisation)
    content_text TEXT,                             -- Corps texte brut nettoyé (RAG Mail)
    content_text_raw TEXT,                         -- Corps texte brut original
    content_html TEXT,                             -- Corps HTML (si disponible)
    content_cleaned_at TIMESTAMP WITH TIME ZONE,   -- Quand le nettoyage RAG Mail a été fait
    
    -- Traitement
    processing_status email_status DEFAULT 'pending',
    processing_error TEXT,                         -- Message d'erreur si status = 'error'
    processing_attempts INTEGER DEFAULT 0,         -- Nombre de tentatives
    
    -- Métadonnées Gmail
    gmail_labels TEXT[],                           -- Labels Gmail
    gmail_snippet TEXT,                            -- Extrait Gmail
    headers JSONB DEFAULT '{}'::jsonb,             -- Headers complets
    
    -- Références
    in_reply_to TEXT,                              -- Message-ID auquel on répond
    references TEXT[],                             -- Chaîne de références
    
    -- Métadonnées internes
    has_attachments BOOLEAN DEFAULT false,
    attachments_count INTEGER DEFAULT 0,
    total_size_bytes INTEGER DEFAULT 0,            -- Taille totale avec PJ
    
    -- Traçabilité
    synced_by UUID REFERENCES auth.users(id),      -- Qui a lancé la synchro (si manuel)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_emails_org ON emails(org_id);
CREATE INDEX IF NOT EXISTS idx_emails_account ON emails(email_account_id);
CREATE INDEX IF NOT EXISTS idx_emails_thread ON emails(gmail_thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_message ON emails(gmail_message_id);
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(processing_status);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender_email);
CREATE INDEX IF NOT EXISTS idx_emails_sent_at ON emails(sent_at);
CREATE INDEX IF NOT EXISTS idx_emails_thread_sent ON emails(gmail_thread_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_emails_status_account ON emails(email_account_id, processing_status);

-- Index pour recherche textuelle (Full Text Search)
CREATE INDEX IF NOT EXISTS idx_emails_fts ON emails 
    USING gin(to_tsvector('french', coalesce(subject, '') || ' ' || coalesce(content_text, '')));

-- Trigger updated_at
CREATE TRIGGER update_emails_updated_at
    BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TABLE : email_attachments
-- Pièces jointes des emails
-- ============================================
CREATE TABLE IF NOT EXISTS email_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- Identifiants
    gmail_attachment_id TEXT,                      -- ID Gmail de la PJ (si disponible)
    
    -- Métadonnées fichier
    filename TEXT NOT NULL,
    filename_clean TEXT,                           -- Nom nettoyé (sans caractères spéciaux)
    mime_type TEXT,                                -- application/pdf, image/jpeg...
    file_extension TEXT GENERATED ALWAYS AS (
        lower(split_part(filename, '.', array_length(string_to_array(filename, '.'), 1)))
    ) STORED,                                      -- Extension extraite
    file_size_bytes INTEGER,
    
    -- Stockage
    storage_path TEXT NOT NULL,                    -- Chemin FileStorageService
    storage_backend TEXT DEFAULT 'local',          -- local, s3, gcs...
    
    -- OCR et contenu
    is_processed BOOLEAN DEFAULT false,            -- OCR/traite effectué
    ocr_text TEXT,                                 -- Texte extrait (si applicable)
    ocr_confidence DECIMAL(3,2),                   -- Confiance OCR (0.00 à 1.00)
    ocr_processed_at TIMESTAMP WITH TIME ZONE,
    ocr_error TEXT,                                -- Erreur OCR si échec
    
    -- Métadonnées
    content_hash TEXT,                             -- Hash MD5/SHA pour déduplication
    is_inline BOOLEAN DEFAULT false,               -- Image inline dans HTML
    content_id TEXT,                               -- Content-ID pour images inline
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_attachments_org ON email_attachments(org_id);
CREATE INDEX IF NOT EXISTS idx_email_attachments_email ON email_attachments(email_id);
CREATE INDEX IF NOT EXISTS idx_email_attachments_mime ON email_attachments(mime_type);
CREATE INDEX IF NOT EXISTS idx_email_attachments_processed ON email_attachments(is_processed);
CREATE INDEX IF NOT EXISTS idx_email_attachments_hash ON email_attachments(content_hash);

-- Trigger updated_at
CREATE TRIGGER update_email_attachments_updated_at
    BEFORE UPDATE ON email_attachments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TABLE : email_embeddings
-- Vecteurs pour recherche sémantique (RAG)
-- ============================================
CREATE TABLE IF NOT EXISTS email_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    
    -- Source du contenu vectorisé
    source_type embedding_source NOT NULL,         -- 'email_body' ou 'attachment'
    source_id UUID,                                -- email_id ou attachment_id selon source_type
    
    -- Contenu chunké
    content_chunk TEXT NOT NULL,                   -- Morceau de texte vectorisé
    chunk_index INTEGER DEFAULT 0,                 -- Position du chunk (0 = premier)
    chunk_total INTEGER DEFAULT 1,                 -- Nombre total de chunks
    chunk_char_start INTEGER,                      -- Position caractère début
    chunk_char_end INTEGER,                        -- Position caractère fin
    
    -- Vecteur (dimension 1536 pour text-embedding-ada-002, ajuster selon modèle)
    embedding VECTOR(1536),
    
    -- Métadonnées du modèle
    model_name TEXT DEFAULT 'text-embedding-ada-002', -- Nom du modèle utilisé
    embedding_version INTEGER DEFAULT 1,           -- Version du modèle/embedding
    
    -- Contexte pour RAG
    surrounding_context TEXT,                      -- Phrases avant/après (pour affichage)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_embeddings_org ON email_embeddings(org_id);
CREATE INDEX IF NOT EXISTS idx_email_embeddings_email ON email_embeddings(email_id);
CREATE INDEX IF NOT EXISTS idx_email_embeddings_source ON email_embeddings(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_email_embeddings_vector ON email_embeddings 
    USING ivfflat (embedding vector_cosine_ops);

-- Index pour recherche hybride (combinaison filtre + similarité)
CREATE INDEX IF NOT EXISTS idx_email_embeddings_org_vector ON email_embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100) 
    WHERE org_id IS NOT NULL;

-- ============================================
-- FONCTIONS UTILITAIRES
-- ============================================

-- Fonction de recherche par similarité (cosine distance)
CREATE OR REPLACE FUNCTION search_similar_emails(
    query_embedding VECTOR(1536),
    target_org_id UUID,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE(
    embedding_id UUID,
    email_id UUID,
    source_type embedding_source,
    content_chunk TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ee.id as embedding_id,
        ee.email_id,
        ee.source_type,
        ee.content_chunk,
        1 - (ee.embedding <=> query_embedding) as similarity
    FROM email_embeddings ee
    WHERE ee.org_id = target_org_id
    AND 1 - (ee.embedding <=> query_embedding) > match_threshold
    ORDER BY ee.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour obtenir le thread complet d'un email
CREATE OR REPLACE FUNCTION get_email_thread(thread_id TEXT, target_org_id UUID)
RETURNS TABLE(
    id UUID,
    gmail_message_id TEXT,
    subject TEXT,
    sender_email TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    content_text TEXT,
    processing_status email_status
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.gmail_message_id,
        e.subject,
        e.sender_email,
        e.sent_at,
        e.content_text,
        e.processing_status
    FROM emails e
    WHERE e.gmail_thread_id = thread_id
    AND e.org_id = target_org_id
    ORDER BY e.sent_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour marquer un email comme traité (appelé par module Secrétariat)
CREATE OR REPLACE FUNCTION mark_email_processed(email_uuid UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE emails 
    SET processing_status = 'vectorized',
        updated_at = NOW()
    WHERE id = email_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- COMMENTAIRES
-- ============================================

COMMENT ON TABLE email_accounts IS 'Configuration des comptes Gmail connectés par organisation';
COMMENT ON TABLE emails IS 'Emails récupérés depuis Gmail avec métadonnées et contenu nettoyé (RAG Mail)';
COMMENT ON TABLE email_attachments IS 'Pièces jointes des emails avec OCR et stockage';
COMMENT ON TABLE email_embeddings IS 'Vecteurs d''embeddings pour recherche sémantique RAG';

COMMENT ON COLUMN emails.processing_status IS 'pending=à vectoriser, vectorized=prêt pour Secrétariat, error=échec';
COMMENT ON COLUMN emails.content_text IS 'Contenu nettoyé par RAG Mail (suppression signatures, mentions légales...)';
COMMENT ON COLUMN email_embeddings.embedding IS 'Vecteur 1536 dimensions (text-embedding-ada-002)';

-- ============================================
-- NOTES DE MIGRATION
-- ============================================

-- Pour activer pgvector sur Supabase :
-- 1. Aller dans Database > Extensions
-- 2. Activer "vector"
-- Ou exécuter : CREATE EXTENSION vector;

-- Pour ajuster la dimension des vecteurs selon votre modèle :
-- - OpenAI text-embedding-ada-002 : 1536 (défaut)
-- - OpenAI text-embedding-3-small : 1536
-- - OpenAI text-embedding-3-large : 3072
-- Modifier la colonne embedding si nécessaire :
-- ALTER TABLE email_embeddings ALTER COLUMN embedding TYPE vector(3072);
