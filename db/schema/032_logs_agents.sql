-- 032_logs_agents.sql
-- Table générique de traçabilité des interactions IA (agnostique domaine)
-- Stocke chaque appel LLM avec son contexte, prompt, réponse et métriques

CREATE TYPE log_agent_type AS ENUM (
    'gemini_extraction',
    'gemini_chat',
    'gemini_ocr',
    'gemini_classification',
    'custom'
);

CREATE TYPE log_agent_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed'
);

CREATE TABLE IF NOT EXISTS logs_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Corrélation
    correlation_id UUID NOT NULL,
    parent_correlation_id UUID,

    -- Agent
    agent_type log_agent_type NOT NULL,
    agent_version TEXT DEFAULT '',
    model TEXT NOT NULL,

    -- Payloads
    system_prompt TEXT,
    user_prompt TEXT NOT NULL,
    raw_input JSONB DEFAULT '{}'::jsonb,
    raw_output JSONB DEFAULT '{}'::jsonb,
    response_text TEXT,
    extracted_data JSONB DEFAULT '{}'::jsonb,

    -- Métriques
    status log_agent_status DEFAULT 'pending',
    processing_duration_ms INTEGER,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_estimate NUMERIC(10,6) DEFAULT 0,

    -- Guardrails
    input_validated BOOLEAN DEFAULT false,
    output_validated BOOLEAN DEFAULT false,
    validation_result JSONB DEFAULT '{}'::jsonb,
    guardrail_issues JSONB DEFAULT '[]'::jsonb,

    -- HITL Feedback (lien vers validation humaine)
    hitl_feedback JSONB DEFAULT NULL,
    hitl_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    hitl_action TEXT,
    hitl_reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Référence à l'entité métier (si applicable)
    entity_table TEXT,
    entity_id UUID,

    -- Stockage blob R2
    blob_storage_path TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_logs_agents_org ON logs_agents(org_id);
CREATE INDEX IF NOT EXISTS idx_logs_agents_correlation ON logs_agents(correlation_id);
CREATE INDEX IF NOT EXISTS idx_logs_agents_parent ON logs_agents(parent_correlation_id);
CREATE INDEX IF NOT EXISTS idx_logs_agents_type ON logs_agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_logs_agents_model ON logs_agents(model);
CREATE INDEX IF NOT EXISTS idx_logs_agents_status ON logs_agents(status);
CREATE INDEX IF NOT EXISTS idx_logs_agents_hitl ON logs_agents(hitl_user_id) WHERE hitl_feedback IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_logs_agents_entity ON logs_agents(entity_table, entity_id);
CREATE INDEX IF NOT EXISTS idx_logs_agents_created ON logs_agents(created_at DESC);

-- RLS
ALTER TABLE logs_agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_read_logs_agents" ON logs_agents
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "insert_logs_agents" ON logs_agents
    FOR INSERT WITH CHECK (true);
