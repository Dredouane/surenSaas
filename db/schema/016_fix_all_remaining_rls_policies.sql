-- 016_fix_all_remaining_rls_policies.sql
-- Correction des politiques RLS restantes pour toutes les tables
--
-- PROBLÈME : Les migrations 006-011 ont créé des politiques RLS utilisant 
-- la table DEPRECATED user_org_membership pour vérifier l'accès.
--
-- CONTEXTE : Le script 999_cleanup_user_org_membership.sql a migré les données 
-- vers users.org_id et désactivé RLS sur user_org_membership, cassant ainsi 
-- toutes les vérifications d'accès sur ces tables.
--
-- SOLUTION : Mettre à jour toutes les politiques RLS restantes pour utiliser 
-- directement la table users avec users.org_id
--
-- TABLES CORRIGÉES :
--   - telegram_bots (009)
--   - telegram_users (010) 
--   - telegram_audit (011)
--   - companies (007)
--   - organization_capabilities (006)
--   - user_capabilities (006)
--   - invoice_status_history (012) - complément au 015
--
-- À exécuter après : 015_fix_rls_policies.sql
-- À exécuter avant : 999_cleanup_user_org_membership.sql (si pas déjà fait)

-- ============================================
-- 1. TELEGRAM_BOTS (Migration 009)
-- ============================================

-- Supprimer les anciennes politiques
DROP POLICY IF EXISTS "admin_manage_telegram_bots" ON telegram_bots;
DROP POLICY IF EXISTS "members_read_bots" ON telegram_bots;

-- NOUVELLE Politique ALL : Seuls les admins peuvent gérer les bots
CREATE POLICY "admin_manage_telegram_bots" ON telegram_bots
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = telegram_bots.org_id
            AND users.role = 'admin'
        )
    );

-- NOUVELLE Politique SELECT : Tous les membres peuvent voir les bots actifs
CREATE POLICY "members_read_bots" ON telegram_bots
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = telegram_bots.org_id
        )
        AND telegram_bots.is_active = true
    );

COMMENT ON TABLE telegram_bots IS 'Configuration des bots Telegram - RLS corrigée via users.org_id (migration 016)';

-- ============================================
-- 2. TELEGRAM_USERS (Migration 010)
-- ============================================

-- Supprimer l'ancienne politique (la policy user_manage_own_telegram est OK)
DROP POLICY IF EXISTS "admin_read_org_telegram" ON telegram_users;

-- NOUVELLE Politique SELECT : Les admins peuvent voir tous les users Telegram de l'org
CREATE POLICY "admin_read_org_telegram" ON telegram_users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = telegram_users.org_id
            AND users.role = 'admin'
        )
    );

COMMENT ON TABLE telegram_users IS 'Users Telegram liés aux comptes - RLS corrigée via users.org_id (migration 016)';

-- ============================================
-- 3. TELEGRAM_AUDIT (Migration 011)
-- ============================================

-- Supprimer l'ancienne politique (la policy user_read_own_audit est OK)
DROP POLICY IF EXISTS "admin_read_audit" ON telegram_audit;

-- NOUVELLE Politique SELECT : Les admins peuvent voir les logs d'audit
CREATE POLICY "admin_read_audit" ON telegram_audit
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = telegram_audit.org_id
            AND users.role = 'admin'
        )
    );

COMMENT ON TABLE telegram_audit IS 'Logs daudit Telegram - RLS corrigée via users.org_id (migration 016)';

-- ============================================
-- 4. COMPANIES (Migration 007)
-- ============================================

-- Supprimer les anciennes politiques
DROP POLICY IF EXISTS "members_read_companies" ON companies;
DROP POLICY IF EXISTS "admin_manage_companies" ON companies;

-- NOUVELLE Politique SELECT : Tous les membres peuvent voir les entreprises actives
CREATE POLICY "members_read_companies" ON companies
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = companies.org_id
        )
        AND companies.is_active = true
    );

-- NOUVELLE Politique ALL : Les admins peuvent gérer les entreprises
CREATE POLICY "admin_manage_companies" ON companies
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = companies.org_id
            AND users.role = 'admin'
        )
    );

COMMENT ON TABLE companies IS 'Entreprises/PME - RLS corrigée via users.org_id (migration 016)';

-- ============================================
-- 5. ORGANIZATION_CAPABILITIES (Migration 006)
-- ============================================

-- Supprimer l'ancienne politique
DROP POLICY IF EXISTS "admin_manage_org_capabilities" ON organization_capabilities;

-- NOUVELLE Politique ALL : Seuls les admins peuvent gérer les capabilities org
CREATE POLICY "admin_manage_org_capabilities" ON organization_capabilities
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = organization_capabilities.org_id
            AND users.role = 'admin'
        )
    );

COMMENT ON TABLE organization_capabilities IS 'Capabilities par organisation - RLS corrigée via users.org_id (migration 016)';

-- ============================================
-- 6. USER_CAPABILITIES (Migration 006)
-- ============================================

-- Supprimer l'ancienne politique (user_read_own_capabilities est OK)
DROP POLICY IF EXISTS "admin_manage_user_capabilities" ON user_capabilities;

-- NOUVELLE Politique ALL : Les admins peuvent gérer les capabilities users
CREATE POLICY "admin_manage_user_capabilities" ON user_capabilities
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users u_admin
            JOIN users u_target ON u_target.org_id = u_admin.org_id
            WHERE u_admin.id = auth.uid() 
            AND u_target.id = user_capabilities.user_id
            AND u_admin.role = 'admin'
        )
    );

COMMENT ON TABLE user_capabilities IS 'Capabilities par utilisateur - RLS corrigée via users.org_id (migration 016)';

-- ============================================
-- 7. INVOICE_STATUS_HISTORY (Migration 012) - Complément au 015
-- ============================================

-- Supprimer l'ancienne politique si elle existe encore
DROP POLICY IF EXISTS "members_read_status_history" ON invoice_status_history;
DROP POLICY IF EXISTS "members_read_invoice_history" ON invoice_status_history;

-- NOUVELLE Politique SELECT : Les membres de l'org peuvent voir l'historique
CREATE POLICY "members_read_invoice_history" ON invoice_status_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM invoices i
            JOIN users u ON u.org_id = i.org_id
            WHERE i.id = invoice_status_history.invoice_id
            AND u.id = auth.uid()
        )
    );

COMMENT ON TABLE invoice_status_history IS 'Historique des statuts des factures - RLS corrigée via users.org_id (migration 016)';

-- ============================================
-- 8. RÉSUMÉ ET VÉRIFICATION
-- ============================================

SELECT 'Politiques RLS corrigées pour toutes les tables restantes' AS status;

-- Afficher un résumé des tables corrigées
SELECT 
    tablename,
    COUNT(*) as policy_count
FROM pg_policies 
WHERE tablename IN (
    'telegram_bots', 
    'telegram_users', 
    'telegram_audit',
    'companies',
    'organization_capabilities',
    'user_capabilities',
    'invoice_status_history'
)
GROUP BY tablename
ORDER BY tablename;
