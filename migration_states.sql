ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS last_state TEXT;
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS last_state_data JSONB DEFAULT '{}';
