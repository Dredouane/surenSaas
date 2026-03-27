-- 007_companies.sql
-- Entreprises filiales au sein d'une organisation

CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,                    -- ex: 'construction', 'nettoyage'
    name TEXT NOT NULL,
    description TEXT,
    logo_url TEXT,
    theme_config JSONB DEFAULT '{}',       -- CSS variables spécifiques
    telegram_bot_id UUID,                  -- Référence vers telegram_bots (créé après)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(org_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_companies_org ON companies(org_id);
CREATE INDEX IF NOT EXISTS idx_companies_slug ON companies(slug);
CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(org_id, is_active);

-- Trigger pour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

-- Tous les membres de l'org peuvent voir les entreprises actives
CREATE POLICY "members_read_companies" ON companies
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
        AND is_active = true
    );

-- Admins peuvent tout faire
CREATE POLICY "admin_manage_companies" ON companies
    FOR ALL USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- Insertion de l'entreprise construction par défaut
-- À exécuter après création d'une organization
-- INSERT INTO companies (org_id, slug, name, description) 
-- VALUES ('org-uuid', 'construction', 'Construction', 'Gestion des chantiers et factures');
