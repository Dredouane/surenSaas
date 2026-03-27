-- 004_user_org_membership.sql
-- Association utilisateur-organisation avec rôle

CREATE TABLE IF NOT EXISTS user_org_membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);

CREATE INDEX IF NOT EXISTS idx_user_org_membership_user ON user_org_membership(user_id);
CREATE INDEX IF NOT EXISTS idx_user_org_membership_org ON user_org_membership(org_id);

COMMENT ON TABLE user_org_membership IS 'Association user-org avec rôle';
