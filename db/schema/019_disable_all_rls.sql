-- 019_disable_all_rls.sql
-- Désactivation complète de RLS sur toutes les tables applicatives
-- 
-- ATTENTION: Cette migration est pour le prototypage uniquement.
-- En production, RLS doit être activé avec des policies appropriées.
-- 
-- Contexte: Les erreurs RLS bloquent les opérations du bot Telegram
-- et créent des frictions inutiles pendant la phase de développement.
-- Le contrôle d'accès est géré par l'application (capabilities) plutôt
-- que par la base de données.

-- Liste des tables avec RLS à désactiver
-- Cette migration est idempotente (peut être exécutée plusieurs fois sans erreur)

-- 1. Tables métier principales
DO $$
BEGIN
    -- Organizations
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations') THEN
        ALTER TABLE IF EXISTS organizations DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: organizations';
    END IF;

    -- Users (table custom, pas auth.users)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users' AND table_schema = 'public') THEN
        ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: users';
    END IF;

    -- Pre-authorized emails
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pre_authorized_emails') THEN
        ALTER TABLE IF EXISTS pre_authorized_emails DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: pre_authorized_emails';
    END IF;

    -- User org membership (legacy, mais au cas où)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_org_membership') THEN
        ALTER TABLE IF EXISTS user_org_membership DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: user_org_membership';
    END IF;
END $$;

-- 2. Tables de capabilities
DO $$
BEGIN
    -- Organization capabilities
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_capabilities') THEN
        ALTER TABLE IF EXISTS organization_capabilities DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: organization_capabilities';
    END IF;

    -- User capabilities
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_capabilities') THEN
        ALTER TABLE IF EXISTS user_capabilities DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: user_capabilities';
    END IF;
END $$;

-- 3. Tables métier Construction
DO $$
BEGIN
    -- Companies
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'companies') THEN
        ALTER TABLE IF EXISTS companies DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: companies';
    END IF;

    -- Clients
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'clients') THEN
        ALTER TABLE IF EXISTS clients DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: clients';
    END IF;

    -- Invoices
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoices') THEN
        ALTER TABLE IF EXISTS invoices DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: invoices';
    END IF;

    -- Invoice items
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoice_items') THEN
        ALTER TABLE IF EXISTS invoice_items DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: invoice_items';
    END IF;

    -- Invoice status history
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoice_status_history') THEN
        ALTER TABLE IF EXISTS invoice_status_history DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: invoice_status_history';
    END IF;
END $$;

-- 4. Tables Telegram
DO $$
BEGIN
    -- Telegram bots
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'telegram_bots') THEN
        ALTER TABLE IF EXISTS telegram_bots DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: telegram_bots';
    END IF;

    -- Telegram users
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'telegram_users') THEN
        ALTER TABLE IF EXISTS telegram_users DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: telegram_users';
    END IF;

    -- Telegram audit (source de l'erreur actuelle)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'telegram_audit') THEN
        ALTER TABLE IF EXISTS telegram_audit DISABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'RLS désactivé sur: telegram_audit';
    END IF;
END $$;

-- 5. Suppression des policies existantes (optionnel, pour nettoyer)
-- On garde les policies en place mais RLS désactivé = policies non exécutées
-- Si vous voulez vraiment supprimer les policies, décommentez ci-dessous:

/*
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN 
        SELECT schemaname, tablename, policyname 
        FROM pg_policies 
        WHERE schemaname = 'public'
        AND tablename IN (
            'organizations', 'users', 'pre_authorized_emails', 
            'organization_capabilities', 'user_capabilities',
            'companies', 'clients', 'invoices', 'invoice_items', 
            'invoice_status_history', 'telegram_bots', 
            'telegram_users', 'telegram_audit'
        )
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', 
            policy_record.policyname, 
            policy_record.schemaname, 
            policy_record.tablename);
        RAISE NOTICE 'Policy supprimée: %.%', policy_record.tablename, policy_record.policyname;
    END LOOP;
END $$;
*/

-- Vérification finale
DO $$
DECLARE
    rls_status RECORD;
BEGIN
    RAISE NOTICE '===============================================';
    RAISE NOTICE 'STATUT RLS APRÈS MIGRATION:';
    RAISE NOTICE '===============================================';
    
    FOR rls_status IN 
        SELECT relname as table_name, relrowsecurity as rls_enabled
        FROM pg_class
        WHERE relname IN (
            'organizations', 'users', 'pre_authorized_emails',
            'organization_capabilities', 'user_capabilities',
            'companies', 'clients', 'invoices', 'invoice_items',
            'invoice_status_history', 'telegram_bots',
            'telegram_users', 'telegram_audit'
        )
        AND relnamespace = 'public'::regnamespace
        ORDER BY relname
    LOOP
        IF rls_status.rls_enabled THEN
            RAISE NOTICE '⚠️  %: RLS encore activé!', rls_status.table_name;
        ELSE
            RAISE NOTICE '✅ %: RLS désactivé', rls_status.table_name;
        END IF;
    END LOOP;
    
    RAISE NOTICE '===============================================';
    RAISE NOTICE 'Migration 019 terminée avec succès';
    RAISE NOTICE 'RLS est maintenant désactivé sur toutes les tables';
    RAISE NOTICE '===============================================';
END $$;

SELECT 'Migration 019: RLS désactivé sur toutes les tables' AS status;
