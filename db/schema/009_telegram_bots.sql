-- 009_telegram_bots.sql
-- Configuration des bots Telegram liés aux entreprises

CREATE TABLE IF NOT EXISTS telegram_bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,  -- NULL = bot organisation global
    
    -- Configuration Telegram
    bot_token_hash TEXT NOT NULL,           -- Hash du token (jamais en clair!)
    bot_username TEXT NOT NULL,
    bot_id BIGINT NOT NULL,                 -- ID Telegram du bot
    
    -- Webhook
    webhook_url TEXT NOT NULL,
    webhook_secret TEXT,                    -- Secret pour vérifier authenticité
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_configured BOOLEAN DEFAULT false,    -- Webhook configuré avec succès
    configured_at TIMESTAMP WITH TIME ZONE,
    
    -- Métadonnées
    description TEXT,
    welcome_message TEXT DEFAULT 'Bienvenue! Envoyez une photo ou PDF de facture pour la traiter.',
    
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telegram_bots_org ON telegram_bots(org_id);
CREATE INDEX IF NOT EXISTS idx_telegram_bots_company ON telegram_bots(company_id);
CREATE INDEX IF NOT EXISTS idx_telegram_bots_active ON telegram_bots(org_id, is_active);

-- Trigger updated_at
CREATE TRIGGER update_telegram_bots_updated_at
    BEFORE UPDATE ON telegram_bots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE telegram_bots ENABLE ROW LEVEL SECURITY;

-- Admins uniquement
CREATE POLICY "admin_manage_telegram_bots" ON telegram_bots
    FOR ALL USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- Members peuvent voir les bots actifs de leur org
CREATE POLICY "members_read_bots" ON telegram_bots
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
        AND is_active = true
    );
