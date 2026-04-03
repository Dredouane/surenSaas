-- Désactiver RLS sur toutes les tables (Quick Fix)
-- À exécuter dans Supabase SQL Editor
-- Cette requête désactive immédiatement RLS sur toutes les tables applicatives

ALTER TABLE IF EXISTS organizations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pre_authorized_emails DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_org_membership DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS organization_capabilities DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_capabilities DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS companies DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS clients DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS invoices DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS invoice_items DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS invoice_status_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS telegram_bots DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS telegram_users DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS telegram_audit DISABLE ROW LEVEL SECURITY;

-- Vérification
SELECT 
    relname as table_name,
    CASE WHEN relrowsecurity THEN '❌ ENCORE ACTIVÉ' ELSE '✅ DÉSACTIVÉ' END as status
FROM pg_class
WHERE relname IN (
    'organizations', 'users', 'pre_authorized_emails',
    'organization_capabilities', 'user_capabilities',
    'companies', 'clients', 'invoices', 'invoice_items',
    'invoice_status_history', 'telegram_bots',
    'telegram_users', 'telegram_audit'
)
AND relnamespace = 'public'::regnamespace
ORDER BY relname;
