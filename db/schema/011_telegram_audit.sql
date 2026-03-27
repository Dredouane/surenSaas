-- 011_telegram_audit.sql
-- Audit de toutes les interactions avec les bots Telegram

CREATE TYPE telegram_interaction_type AS ENUM (
    'message_received',     -- Message reçu
    'command_received',     -- Commande reçue (/start, etc.)
    'button_clicked',       -- Bouton cliqué
    'file_received',        -- Fichier reçu (photo, PDF)
    'workflow_started',     -- Workflow démarré
    'workflow_step',        -- Étape de workflow
    'workflow_completed',   -- Workflow terminé
    'workflow_failed',      -- Workflow échoué
    'notification_sent',    -- Notification envoyée
    'error'                 -- Erreur
);

CREATE TYPE telegram_interaction_status AS ENUM (
    'pending',              -- En attente
    'processing',           -- En cours
    'completed',            -- Terminé avec succès
    'failed',               -- Échoué
    'cancelled'             -- Annulé
);

CREATE TABLE IF NOT EXISTS telegram_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    bot_id UUID NOT NULL REFERENCES telegram_bots(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,       -- ID Telegram
    
    -- Type et status
    interaction_type telegram_interaction_type NOT NULL,
    status telegram_interaction_status DEFAULT 'pending',
    
    -- Données
    payload JSONB DEFAULT '{}'::jsonb,      -- Données reçues (message, fichier, etc.)
    result JSONB DEFAULT '{}'::jsonb,       -- Résultat/réponse
    error_message TEXT,                     -- Message d'erreur si failed
    
    -- Workflow (si applicable)
    workflow_name TEXT,                     -- Nom du workflow (ex: 'invoice_upload')
    workflow_step TEXT,                     -- Étape actuelle
    workflow_id UUID,                       -- ID de l'objet créé (ex: invoice_id)
    
    -- Métadonnées
    processing_duration_ms INTEGER,         -- Durée traitement en ms
    ip_address INET,                        -- IP (si disponible)
    user_agent TEXT,                        -- User-Agent
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes pour monitoring et debugging
CREATE INDEX IF NOT EXISTS idx_telegram_audit_org ON telegram_audit(org_id);
CREATE INDEX IF NOT EXISTS idx_telegram_audit_bot ON telegram_audit(bot_id);
CREATE INDEX IF NOT EXISTS idx_telegram_audit_user ON telegram_audit(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_audit_type ON telegram_audit(interaction_type);
CREATE INDEX IF NOT EXISTS idx_telegram_audit_status ON telegram_audit(status);
CREATE INDEX IF NOT EXISTS idx_telegram_audit_workflow ON telegram_audit(workflow_name);
CREATE INDEX IF NOT EXISTS idx_telegram_audit_created ON telegram_audit(created_at);
CREATE INDEX IF NOT EXISTS idx_telegram_audit_failed ON telegram_audit(org_id, status) WHERE status = 'failed';

-- Trigger updated_at
CREATE TRIGGER update_telegram_audit_updated_at
    BEFORE UPDATE ON telegram_audit
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE telegram_audit ENABLE ROW LEVEL SECURITY;

-- Admins peuvent tout voir dans leur org
CREATE POLICY "admin_read_audit" ON telegram_audit
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- Users peuvent voir leurs propres interactions
CREATE POLICY "user_read_own_audit" ON telegram_audit
    FOR SELECT USING (
        telegram_user_id IN (
            SELECT telegram_id FROM telegram_users WHERE user_id = auth.uid()
        )
    );

-- Function pour cleanup anciens audits (à exécuter via cron)
CREATE OR REPLACE FUNCTION cleanup_old_telegram_audit(days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM telegram_audit 
    WHERE created_at < NOW() - (days || ' days')::INTERVAL
    AND status IN ('completed', 'cancelled');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
