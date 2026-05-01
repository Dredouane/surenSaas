-- 037_langgraph_persistence.sql
-- Migration pour la persistance de LangGraph dans le schéma 'agents'

-- 1. Création du schéma
CREATE SCHEMA IF NOT EXISTS agents;

-- 2. Tables techniques LangGraph (PostgresSaver)
-- Ces tables sont requises par LangGraph pour la gestion des checkpoints

CREATE TABLE IF NOT EXISTS agents.checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_id TEXT,
    checkpoint BYTEA NOT NULL,
    metadata BYTEA NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS agents.writes (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    value BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_id, task_id, idx)
);

CREATE TABLE IF NOT EXISTS agents.blobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Table de Logs Agents étendue (Audit & Corrélation)
-- (On complète la table logs_agents existante si nécessaire)

CREATE TABLE IF NOT EXISTS agents.logs_agents_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id UUID NOT NULL,
    thread_id TEXT NOT NULL,
    from_node TEXT,
    to_node TEXT,
    action TEXT,
    input_data JSONB,
    output_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour la performance
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON agents.checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_logs_transitions_thread ON agents.logs_agents_transitions(thread_id);
CREATE INDEX IF NOT EXISTS idx_logs_transitions_correlation ON agents.logs_agents_transitions(correlation_id);

-- RLS (Optionnel si accès via Service Role)
ALTER TABLE agents.checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents.writes ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents.blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents.logs_agents_transitions ENABLE ROW LEVEL SECURITY;

-- Note: En mode "Full Agentic", le backend utilise généralement le Service Role 
-- pour manipuler ces tables techniques.
