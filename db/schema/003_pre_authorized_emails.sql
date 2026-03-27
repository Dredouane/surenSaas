-- 003_pre_authorized_emails.sql
-- Table pour les emails pré-autorisés à créer un compte

CREATE TABLE IF NOT EXISTS pre_authorized_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    invited_by UUID REFERENCES auth.users(id),
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_pre_authorized_emails_email ON pre_authorized_emails(email);
CREATE INDEX IF NOT EXISTS idx_pre_authorized_emails_org ON pre_authorized_emails(org_id);

COMMENT ON TABLE pre_authorized_emails IS 'Emails autorisés à créer un compte';
