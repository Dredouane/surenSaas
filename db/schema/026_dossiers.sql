-- 026_dossiers.sql
-- Module Dossiers (Le Classeur) pour regrouper les threads par projet/chantier
-- + Support pour Drafting Sandbox (état temporaire, pas de table persistante)

-- ============================================
-- TYPE ENUM : Statut des dossiers
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dossier_status') THEN
        CREATE TYPE dossier_status AS ENUM ('active', 'completed', 'on_hold', 'cancelled');
    END IF;
END
$$;

-- ============================================
-- TABLE : dossiers
-- Conteneur métier pour regrouper les threads par chantier/projet
-- ============================================
CREATE TABLE IF NOT EXISTS dossiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Identité du dossier/chantier
    name TEXT NOT NULL,                    -- "Résidence Les Lilas - SDB"
    client_name TEXT,                      -- "ACORUS"
    client_email TEXT,                     -- "contact@acorus.fr"
    address TEXT,                          -- "12 rue des Lilas, 75019 Paris"
    
    -- Métadonnées chantier
    project_type TEXT,                     -- "renovation", "construction", "maintenance"
    budget_estimate DECIMAL(12,2),         -- Budget estimé si mentionné
    deadline DATE,                         -- Date butoir si mentionnée
    
    -- Statut
    status dossier_status DEFAULT 'active',
    
    -- IA - Résumé cross-threads
    ai_summary TEXT,                       -- Résumé global généré par Gemini
    ai_summary_updated_at TIMESTAMP,       -- Date dernière mise à jour résumé
    
    -- Compteurs (mis à jour par triggers)
    thread_count INTEGER DEFAULT 0,        -- Nombre de threads liés
    document_count INTEGER DEFAULT 0,      -- Nombre de PJ
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Contrainte: un dossier par nom/client/org (évite doublons)
    UNIQUE(org_id, client_name, name)
);

-- ============================================
-- INDEXES pour performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_dossiers_org ON dossiers(org_id);
CREATE INDEX IF NOT EXISTS idx_dossiers_company ON dossiers(company_id);
CREATE INDEX IF NOT EXISTS idx_dossiers_status ON dossiers(status);
CREATE INDEX IF NOT EXISTS idx_dossiers_client ON dossiers(client_name);
CREATE INDEX IF NOT EXISTS idx_dossiers_updated ON dossiers(updated_at DESC);

-- ============================================
-- MODIFICATION : email_threads
-- Ajout de la FK vers dossiers
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'email_threads' AND column_name = 'dossier_id'
    ) THEN
        ALTER TABLE email_threads 
        ADD COLUMN dossier_id UUID REFERENCES dossiers(id) ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_email_threads_dossier ON email_threads(dossier_id);

-- ============================================
-- FONCTION : Mettre à jour les compteurs d'un dossier
-- ============================================
CREATE OR REPLACE FUNCTION update_dossier_counters(p_dossier_id UUID)
RETURNS VOID AS $$
DECLARE
    v_thread_count INTEGER;
    v_document_count INTEGER;
BEGIN
    -- Compter les threads liés
    SELECT COUNT(*) INTO v_thread_count
    FROM email_threads
    WHERE dossier_id = p_dossier_id;
    
    -- Compter les pièces jointes dans tous les threads du dossier
    SELECT COUNT(*) INTO v_document_count
    FROM email_attachments ea
    JOIN emails e ON ea.email_id = e.id
    JOIN email_threads t ON e.gmail_thread_id = t.gmail_thread_id
    WHERE t.dossier_id = p_dossier_id;
    
    -- Mettre à jour le dossier
    UPDATE dossiers
    SET thread_count = v_thread_count,
        document_count = v_document_count,
        updated_at = NOW()
    WHERE id = p_dossier_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGER : Mise à jour auto des compteurs
-- Quand un thread est lié/délié d'un dossier
-- ============================================
CREATE OR REPLACE FUNCTION trigger_update_dossier_counters()
RETURNS TRIGGER AS $$
BEGIN
    -- Si ancien dossier_id, mettre à jour l'ancien
    IF TG_OP = 'UPDATE' AND OLD.dossier_id IS NOT NULL AND OLD.dossier_id IS DISTINCT FROM NEW.dossier_id THEN
        PERFORM update_dossier_counters(OLD.dossier_id);
    END IF;
    
    -- Si nouveau dossier_id, mettre à jour le nouveau
    IF NEW.dossier_id IS NOT NULL THEN
        PERFORM update_dossier_counters(NEW.dossier_id);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_email_thread_dossier_link ON email_threads;
CREATE TRIGGER trigger_email_thread_dossier_link
    AFTER INSERT OR UPDATE OF dossier_id ON email_threads
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_dossier_counters();

-- ============================================
-- FONCTION : Rechercher des dossiers par similarité
-- Utilisé pour le "Suggested Link" IA
-- ============================================
CREATE OR REPLACE FUNCTION search_dossiers_by_similarity(
    p_org_id UUID,
    p_client_name TEXT DEFAULT NULL,
    p_address TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    client_name TEXT,
    address TEXT,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.name,
        d.client_name,
        d.address,
        CASE
            WHEN p_client_name IS NOT NULL AND d.client_name ILIKE '%' || p_client_name || '%' THEN 0.5
            ELSE 0.0
        END +
        CASE
            WHEN p_address IS NOT NULL AND d.address ILIKE '%' || p_address || '%' THEN 0.5
            ELSE 0.0
        END as similarity_score
    FROM dossiers d
    WHERE d.org_id = p_org_id
      AND d.status = 'active'
    ORDER BY similarity_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- FONCTION : Générer résumé cross-threads (appelé par IA)
-- ============================================
CREATE OR REPLACE FUNCTION generate_dossier_summary(p_dossier_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_summary TEXT;
    v_thread_count INTEGER;
BEGIN
    -- Récupérer les infos de base
    SELECT thread_count INTO v_thread_count
    FROM dossiers WHERE id = p_dossier_id;
    
    -- Construction simple du résumé (sera enrichi par Gemini)
    SELECT format(
        'Dossier "%s" pour %s. %s threads, %s documents. Adresse: %s. Status: %s.',
        d.name,
        COALESCE(d.client_name, 'client non spécifié'),
        v_thread_count,
        d.document_count,
        COALESCE(d.address, 'non spécifiée'),
        d.status
    ) INTO v_summary
    FROM dossiers d
    WHERE d.id = p_dossier_id;
    
    -- Mettre à jour le timestamp
    UPDATE dossiers
    SET ai_summary_updated_at = NOW()
    WHERE id = p_dossier_id;
    
    RETURN v_summary;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- NOTE : Drafting Sandbox
-- ============================================
-- Le Drafting Sandbox utilise un état TEMPORAIRE frontend.
-- Pas de table persistante pour les drafts.
-- Optionnel: Cache Redis avec TTL 1h si besoin de persistance temporaire.

-- Si vous voulez ajouter une table de cache pour les drafts:
/*
CREATE TABLE draft_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES email_threads(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT,                    -- HTML content
    context_snapshot JSONB,          -- Copy du contexte thread au moment T
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX idx_draft_sessions_thread ON draft_sessions(thread_id);
CREATE INDEX idx_draft_sessions_expires ON draft_sessions(expires_at);
*/
