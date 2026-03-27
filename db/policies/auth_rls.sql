-- 004_rls_policies.sql
-- RLS policies pour les tables auth

-- pre_authorized_emails : lecture par org_id, écriture par admins
ALTER TABLE pre_authorized_emails ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_read_pre_auth" ON pre_authorized_emails
    FOR SELECT
    USING (org_id IN (
        SELECT org_id FROM user_org_membership 
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

CREATE POLICY "admin_insert_pre_auth" ON pre_authorized_emails
    FOR INSERT
    WITH CHECK (org_id IN (
        SELECT org_id FROM user_org_membership 
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- user_org_membership : user voit ses propres memberships
ALTER TABLE user_org_membership ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_read_own_memberships" ON user_org_membership
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "admin_read_org_members" ON user_org_membership
    FOR SELECT
    USING (org_id IN (
        SELECT org_id FROM user_org_membership 
        WHERE user_id = auth.uid() AND role = 'admin'
    ));
