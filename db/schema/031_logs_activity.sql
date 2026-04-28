-- 031_logs_activity.sql
-- Table générique de traçabilité des mutations CRUD (agnostique domaine)
-- Remplace: chantier_audit_trail, invoice_status_history

CREATE TYPE log_activity_action AS ENUM (
    'create',
    'update',
    'delete',
    'validate',
    'reject',
    'status_change'
);

CREATE TABLE IF NOT EXISTS logs_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Corrélation
    correlation_id UUID NOT NULL,

    -- Mutation
    action log_activity_action NOT NULL,
    table_name TEXT NOT NULL,
    entity_id UUID,
    entity_ref TEXT,

    -- Données
    previous_state JSONB DEFAULT '{}'::jsonb,
    new_state JSONB DEFAULT '{}'::jsonb,
    delta JSONB DEFAULT '{}'::jsonb,

    -- Qui
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_name TEXT DEFAULT '',
    source_system TEXT DEFAULT 'api',
    source_details JSONB DEFAULT '{}'::jsonb,

    -- Métadonnées
    ip_address INET,
    user_agent TEXT,
    processing_duration_ms INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_logs_activity_org ON logs_activity(org_id);
CREATE INDEX IF NOT EXISTS idx_logs_activity_correlation ON logs_activity(correlation_id);
CREATE INDEX IF NOT EXISTS idx_logs_activity_entity ON logs_activity(table_name, entity_id);
CREATE INDEX IF NOT EXISTS idx_logs_activity_action ON logs_activity(action);
CREATE INDEX IF NOT EXISTS idx_logs_activity_user ON logs_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_activity_created ON logs_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_activity_source ON logs_activity(source_system);

-- RLS
ALTER TABLE logs_activity ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_read_logs_activity" ON logs_activity
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "insert_logs_activity" ON logs_activity
    FOR INSERT WITH CHECK (true);
