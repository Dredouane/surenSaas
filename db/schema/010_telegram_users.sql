-- 010_telegram_users.sql
-- Lien entre utilisateurs Telegram et utilisateurs de l'app

CREATE TABLE IF NOT EXISTS telegram_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Identifiants Telegram
    telegram_id BIGINT NOT NULL UNIQUE,     -- ID Telegram
    telegram_username TEXT,
    telegram_first_name TEXT,
    telegram_last_name TEXT,
    
    -- Configuration
    is_verified BOOLEAN DEFAULT false,      -- Email vérifié/bot démarré
    verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Préférences
    notification_enabled BOOLEAN DEFAULT true,
    language_code TEXT DEFAULT 'fr',
    
    -- Métadonnées
    started_at TIMESTAMP WITH TIME ZONE,    -- Quand le bot a été démarré
    last_activity_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_telegram_users_org ON telegram_users(org_id);
CREATE INDEX IF NOT EXISTS idx_telegram_users_user ON telegram_users(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_id ON telegram_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_telegram_users_verified ON telegram_users(org_id, is_verified);

-- Trigger updated_at
CREATE TRIGGER update_telegram_users_updated_at
    BEFORE UPDATE ON telegram_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE telegram_users ENABLE ROW LEVEL SECURITY;

-- Users peuvent voir/modifier leurs propres infos Telegram
CREATE POLICY "user_manage_own_telegram" ON telegram_users
    FOR ALL USING (user_id = auth.uid());

-- Admins peuvent voir tous les telegram_users de leur org
CREATE POLICY "admin_read_org_telegram" ON telegram_users
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );
