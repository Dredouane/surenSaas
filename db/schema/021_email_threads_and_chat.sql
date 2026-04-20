-- 021_email_threads_and_chat.sql
-- Module Emails Management : Threads et Chat IA
-- 
-- VISIBILITÉ : L'utilisateur voit des THREADS (conversations), pas des emails isolés
-- Un email entrant est ajouté à un thread existant ou crée un nouveau thread
-- La page "Emails" affiche la liste des threads, pas des emails individuels

-- ============================================
-- TABLE : email_threads
-- Métadonnées d'une conversation (ce que voit l'utilisateur)
-- ============================================
CREATE TABLE IF NOT EXISTS email_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Identifiant Gmail (unique par org)
    gmail_thread_id TEXT NOT NULL,
    
    -- Sujet principal (extrait du premier email)
    subject TEXT,
    subject_cleaned TEXT,
    
    -- Participants (pour affichage rapide)
    participant_emails TEXT[],  -- ['client@acorus.fr', 'contact@fournisseur.fr']
    participant_names TEXT[],   -- ['ACORUS', 'Jean Dupont']
    
    -- Résumé & Analyse IA (peut être mocké initialement)
    ai_summary TEXT,            -- "Relance pour le devis du chantier Sanibatiment"
    ai_context TEXT,            -- "Context RAG: J'ai trouvé 2 échanges similaires en mars"
    ai_urgency TEXT CHECK (ai_urgency IN ('low', 'medium', 'high')) DEFAULT 'medium',
    ai_status TEXT CHECK (ai_status IN ('new', 'in_progress', 'waiting', 'resolved', 'urgent')) DEFAULT 'new',
    
    -- Métriques
    email_count INTEGER DEFAULT 0,
    attachment_count INTEGER DEFAULT 0,
    first_email_at TIMESTAMP WITH TIME ZONE,
    last_email_at TIMESTAMP WITH TIME ZONE,
    
    -- Statut du thread
    is_archived BOOLEAN DEFAULT false,
    is_starred BOOLEAN DEFAULT false,
    
    -- Indicateur reconstruction historique
    is_historical_partial BOOLEAN DEFAULT false,  -- True si thread créé depuis un seul email (forward externe)
    historical_notes TEXT,  -- Notes sur la reconstruction (logs pour debug)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Contrainte : un thread Gmail unique par org/company
    UNIQUE(org_id, company_id, gmail_thread_id)
);

-- Indexes pour performance
CREATE INDEX IF NOT EXISTS idx_email_threads_org ON email_threads(org_id);
CREATE INDEX IF NOT EXISTS idx_email_threads_company ON email_threads(company_id);
CREATE INDEX IF NOT EXISTS idx_email_threads_gmail ON email_threads(gmail_thread_id);
CREATE INDEX IF NOT EXISTS idx_email_threads_status ON email_threads(ai_status);
CREATE INDEX IF NOT EXISTS idx_email_threads_urgency ON email_threads(ai_urgency);
CREATE INDEX IF NOT EXISTS idx_email_threads_last_email ON email_threads(last_email_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_threads_updated ON email_threads(updated_at DESC);

-- Trigger updated_at
CREATE TRIGGER update_email_threads_updated_at
    BEFORE UPDATE ON email_threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TABLE : thread_chat_sessions
-- Session de chat liée à un thread (plusieurs sessions possibles par thread)
-- ============================================
CREATE TABLE IF NOT EXISTS thread_chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Lien au thread
    thread_id UUID NOT NULL REFERENCES email_threads(id) ON DELETE CASCADE,
    
    -- Nom de la session (pour distinguer si plusieurs)
    name TEXT DEFAULT 'Chat principal',
    
    -- Contexte RAG (JSON libre)
    rag_context JSONB DEFAULT '{}',
    
    -- Métadonnées
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,
    
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,  -- Session par défaut pour ce thread
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chat_sessions_thread ON thread_chat_sessions(thread_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_org ON thread_chat_sessions(org_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_active ON thread_chat_sessions(thread_id, is_active);

-- Trigger updated_at
CREATE TRIGGER update_thread_chat_sessions_updated_at
    BEFORE UPDATE ON thread_chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TABLE : thread_chat_messages
-- Messages d'une session de chat
-- ============================================
CREATE TABLE IF NOT EXISTS thread_chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES thread_chat_sessions(id) ON DELETE CASCADE,
    
    role TEXT NOT NULL CHECK (role IN ('system', 'assistant', 'user')),
    content TEXT NOT NULL,
    
    -- Métadonnées (JSON libre : sources, actions, etc.)
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON thread_chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON thread_chat_messages(session_id, created_at);

-- ============================================
-- FONCTIONS UTILITAIRES
-- ============================================

-- Fonction pour récupérer ou créer un thread
CREATE OR REPLACE FUNCTION get_or_create_thread(
    p_org_id UUID,
    p_company_id UUID,
    p_gmail_thread_id TEXT,
    p_subject TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_thread_id UUID;
BEGIN
    -- Chercher le thread existant
    SELECT id INTO v_thread_id
    FROM email_threads
    WHERE org_id = p_org_id
    AND company_id = p_company_id
    AND gmail_thread_id = p_gmail_thread_id;
    
    -- Si pas trouvé, créer
    IF v_thread_id IS NULL THEN
        INSERT INTO email_threads (
            org_id, company_id, gmail_thread_id, subject, subject_cleaned,
            email_count, first_email_at, last_email_at
        ) VALUES (
            p_org_id, p_company_id, p_gmail_thread_id, p_subject, p_subject,
            0, NOW(), NOW()
        )
        RETURNING id INTO v_thread_id;
    END IF;
    
    RETURN v_thread_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour mettre à jour les métriques d'un thread
CREATE OR REPLACE FUNCTION update_thread_metrics(p_thread_id UUID)
RETURNS VOID AS $$
DECLARE
    v_email_count INTEGER;
    v_attachment_count INTEGER;
    v_first_email TIMESTAMP;
    v_last_email TIMESTAMP;
    v_participant_emails TEXT[];
    v_participant_names TEXT[];
BEGIN
    -- Compter les emails
    SELECT 
        COUNT(*),
        MIN(sent_at),
        MAX(sent_at),
        ARRAY_AGG(DISTINCT sender_email),
        ARRAY_AGG(DISTINCT sender_name)
    INTO v_email_count, v_first_email, v_last_email, v_participant_emails, v_participant_names
    FROM emails
    WHERE gmail_thread_id = (SELECT gmail_thread_id FROM email_threads WHERE id = p_thread_id);
    
    -- Compter les pièces jointes
    SELECT COUNT(*) INTO v_attachment_count
    FROM email_attachments ea
    JOIN emails e ON ea.email_id = e.id
    WHERE e.gmail_thread_id = (SELECT gmail_thread_id FROM email_threads WHERE id = p_thread_id);
    
    -- Mettre à jour le thread
    UPDATE email_threads
    SET email_count = v_email_count,
        attachment_count = v_attachment_count,
        first_email_at = v_first_email,
        last_email_at = v_last_email,
        participant_emails = v_participant_emails,
        participant_names = v_participant_names,
        updated_at = NOW()
    WHERE id = p_thread_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour obtenir le chat par défaut d'un thread
CREATE OR REPLACE FUNCTION get_default_chat_session(p_thread_id UUID)
RETURNS UUID AS $$
DECLARE
    v_session_id UUID;
BEGIN
    -- Chercher une session active par défaut
    SELECT id INTO v_session_id
    FROM thread_chat_sessions
    WHERE thread_id = p_thread_id
    AND is_active = true
    AND is_default = true;
    
    -- Si pas trouvée, prendre la première active
    IF v_session_id IS NULL THEN
        SELECT id INTO v_session_id
        FROM thread_chat_sessions
        WHERE thread_id = p_thread_id
        AND is_active = true
        ORDER BY created_at ASC
        LIMIT 1;
    END IF;
    
    -- Si toujours pas trouvée, créer une session par défaut
    IF v_session_id IS NULL THEN
        INSERT INTO thread_chat_sessions (
            org_id, company_id, thread_id, name, is_default, is_active
        )
        SELECT 
            org_id, company_id, p_thread_id, 'Chat principal', true, true
        FROM email_threads
        WHERE id = p_thread_id
        RETURNING id INTO v_session_id;
    END IF;
    
    RETURN v_session_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- COMMENTAIRES
-- ============================================

COMMENT ON TABLE email_threads IS 'Conversations email visibles par l''utilisateur (regroupement d''emails par thread Gmail)';
COMMENT ON TABLE thread_chat_sessions IS 'Sessions de chat IA liées à un thread (plusieurs sessions possibles)';
COMMENT ON TABLE thread_chat_messages IS 'Messages des chats IA (assistant + user)';

COMMENT ON COLUMN email_threads.ai_summary IS 'Résumé généré par IA du contenu du thread';
COMMENT ON COLUMN email_threads.ai_urgency IS 'Niveau d''urgence détecté par IA (low/medium/high)';
COMMENT ON COLUMN email_threads.ai_status IS 'Statut du dossier (new/in_progress/waiting/resolved)';
