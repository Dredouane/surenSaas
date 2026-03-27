-- 015_fix_rls_policies.sql
-- Correction des politiques RLS pour invoices et clients
-- 
-- PROBLÈME : Les politiques RLS créées dans 008_invoices.sql et 014_add_clients_and_update_invoices.sql
-- utilisent encore la table DEPRECATED user_org_membership pour vérifier l'accès.
-- 
-- CONTEXTE : Le script 999_cleanup_user_org_membership.sql a migré les données vers users.org_id
-- et désactivé RLS sur user_org_membership, cassant ainsi les vérifications d'accès.
--
-- SOLUTION : Mettre à jour les politiques RLS pour utiliser directement la table users
--
-- À exécuter après : 999_cleanup_user_org_membership.sql (ou indépendamment)
-- 
-- NOTE IMPORTANTE : Cette migration doit être exécutée APRÈS que tous les utilisateurs
-- aient été migrés vers la nouvelle structure (users.org_id et users.role)

-- ============================================
-- 1. CORRECTION DES POLITIQUES RLS - INVOICES
-- ============================================

-- Supprimer les anciennes politiques basées sur user_org_membership
DROP POLICY IF EXISTS "members_read_invoices" ON invoices;
DROP POLICY IF EXISTS "authorized_insert_invoices" ON invoices;
DROP POLICY IF EXISTS "authorized_update_invoices" ON invoices;

-- NOUVELLE Politique SELECT : Les membres de l'org peuvent voir les factures
-- Utilise users.org_id directement au lieu de user_org_membership
CREATE POLICY "members_read_invoices" ON invoices
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = invoices.org_id
        )
    );

-- NOUVELLE Politique INSERT : Les users de l'org peuvent créer des factures
-- Vérification simplifiée via users.org_id
CREATE POLICY "authorized_insert_invoices" ON invoices
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = invoices.org_id
        )
    );

-- NOUVELLE Politique UPDATE : Les users de l'org peuvent modifier les factures
CREATE POLICY "authorized_update_invoices" ON invoices
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = invoices.org_id
        )
    );

-- ============================================
-- 2. CORRECTION DES POLITIQUES RLS - CLIENTS
-- ============================================

-- Supprimer les anciennes politiques basées sur user_org_membership
DROP POLICY IF EXISTS "members_read_clients" ON clients;
DROP POLICY IF EXISTS "members_insert_clients" ON clients;
DROP POLICY IF EXISTS "members_update_clients" ON clients;
DROP POLICY IF EXISTS "admins_delete_clients" ON clients;

-- NOUVELLE Politique SELECT : Les membres de l'org peuvent voir les clients
CREATE POLICY "members_read_clients" ON clients
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = clients.org_id
        )
    );

-- NOUVELLE Politique INSERT : Les users de l'org peuvent créer des clients
CREATE POLICY "members_insert_clients" ON clients
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = clients.org_id
        )
    );

-- NOUVELLE Politique UPDATE : Les users de l'org peuvent modifier les clients
CREATE POLICY "members_update_clients" ON clients
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = clients.org_id
        )
    );

-- NOUVELLE Politique DELETE : Seuls les admins peuvent supprimer les clients
CREATE POLICY "admins_delete_clients" ON clients
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.org_id = clients.org_id 
            AND users.role = 'admin'
        )
    );

-- ============================================
-- 3. MISE À JOUR DE INVOICE_STATUS_HISTORY
-- ============================================

-- Supprimer les anciennes politiques si elles existent
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

-- ============================================
-- 4. DOCUMENTATION
-- ============================================

COMMENT ON TABLE invoices IS 'Table des factures - RLS corrigée via users.org_id (migration 015)';
COMMENT ON TABLE clients IS 'Table des clients - RLS corrigée via users.org_id (migration 015)';
COMMENT ON TABLE invoice_status_history IS 'Historique des statuts - RLS corrigée (migration 015)';

SELECT 'Politiques RLS corrigées avec succès pour invoices et clients' AS status;
