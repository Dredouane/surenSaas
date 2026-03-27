-- 006_capabilities.sql
-- Extension du système de rôles avec capabilities granulaires

-- Table des capabilities disponibles par organisation
CREATE TABLE IF NOT EXISTS organization_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    capability_code TEXT NOT NULL,  -- ex: 'construction:facturation:read'
    description TEXT,
    resource TEXT NOT NULL,         -- ex: 'construction', 'planning'
    action TEXT NOT NULL,           -- ex: 'read', 'write', 'validate'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(org_id, capability_code)
);

CREATE INDEX IF NOT EXISTS idx_org_capabilities_org ON organization_capabilities(org_id);

-- Table de liaison user-capabilities (capabilities assignées aux users)
CREATE TABLE IF NOT EXISTS user_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    capability_code TEXT NOT NULL,
    granted_by UUID REFERENCES auth.users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, org_id, capability_code)
);

CREATE INDEX IF NOT EXISTS idx_user_capabilities_user ON user_capabilities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_capabilities_org ON user_capabilities(org_id);
CREATE INDEX IF NOT EXISTS idx_user_capabilities_code ON user_capabilities(capability_code);

-- Vue pour récupérer les capabilities actives d'un user
CREATE OR REPLACE VIEW user_active_capabilities AS
SELECT 
    uc.user_id,
    uc.org_id,
    uc.capability_code,
    oc.resource,
    oc.action,
    uc.granted_at
FROM user_capabilities uc
JOIN organization_capabilities oc 
    ON uc.org_id = oc.org_id 
    AND uc.capability_code = oc.capability_code
WHERE uc.is_active = true 
    AND uc.revoked_at IS NULL;

-- Function pour vérifier si un user a une capability (ou est admin)
CREATE OR REPLACE FUNCTION check_user_capability(
    p_user_id UUID,
    p_org_id UUID,
    p_capability_code TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_is_admin BOOLEAN;
    v_has_capability BOOLEAN;
BEGIN
    -- Vérifier si admin (bypass)
    SELECT EXISTS (
        SELECT 1 FROM user_org_membership 
        WHERE user_id = p_user_id 
        AND org_id = p_org_id 
        AND role = 'admin'
    ) INTO v_is_admin;
    
    IF v_is_admin THEN
        RETURN true;
    END IF;
    
    -- Vérifier la capability
    SELECT EXISTS (
        SELECT 1 FROM user_active_capabilities
        WHERE user_id = p_user_id
        AND org_id = p_org_id
        AND capability_code = p_capability_code
    ) INTO v_has_capability;
    
    RETURN v_has_capability;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS Policies pour capabilities
ALTER TABLE organization_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_capabilities ENABLE ROW LEVEL SECURITY;

-- Seuls les admins peuvent voir/modifier les capabilities
CREATE POLICY "admin_manage_org_capabilities" ON organization_capabilities
    FOR ALL USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "admin_manage_user_capabilities" ON user_capabilities
    FOR ALL USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- Users peuvent voir leurs propres capabilities
CREATE POLICY "user_read_own_capabilities" ON user_capabilities
    FOR SELECT USING (user_id = auth.uid());
