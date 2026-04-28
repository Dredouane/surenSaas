-- 035_logs_agents_tma_extensions.sql
-- Enrichissement de logs_agents pour la Telegram Mini App
-- Ajoute le contexte d'origine, l'entité cible et l'empreinte appareil

-- Extension enum log_agent_type avec les sources TMA
ALTER TYPE log_agent_type ADD VALUE IF NOT EXISTS 'telegram_bot';
ALTER TYPE log_agent_type ADD VALUE IF NOT EXISTS 'tma_progress_slider';
ALTER TYPE log_agent_type ADD VALUE IF NOT EXISTS 'tma_expense_scanner';

-- Nouvelles colonnes
ALTER TABLE logs_agents
  ADD COLUMN IF NOT EXISTS origin_context TEXT,
  ADD COLUMN IF NOT EXISTS target_entity JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS device_info JSONB DEFAULT '{}'::jsonb;

-- Index pour filtrage par origine
CREATE INDEX IF NOT EXISTS idx_logs_agents_origin ON logs_agents(origin_context);
