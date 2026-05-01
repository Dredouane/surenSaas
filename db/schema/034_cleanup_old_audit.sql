-- 034_cleanup_old_audit.sql
-- Supprime les anciennes tables d'audit spécifiques au profit des tables génériques
-- À exécuter APRÈS avoir vérifié que les nouveaux services écrivent dans logs_activity

DROP TABLE IF EXISTS chantier_audit_trail CASCADE;
DROP TABLE IF EXISTS invoice_status_history CASCADE;
DROP TABLE IF EXISTS telegram_audit CASCADE;

DROP TYPE IF EXISTS chantier_audit_action CASCADE;
DROP TYPE IF EXISTS telegram_interaction_type CASCADE;
DROP TYPE IF EXISTS telegram_interaction_status CASCADE;

DROP FUNCTION IF EXISTS cleanup_old_telegram_audit(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS log_chantier_audit() CASCADE;
DROP FUNCTION IF EXISTS log_invoice_status_change() CASCADE;



DROP TRIGGER IF EXISTS audit_chantier_situations ON chantier_situations;
DROP TRIGGER IF EXISTS audit_chantier_depenses ON chantier_depenses;
DROP TRIGGER IF EXISTS audit_chantier_operations ON chantier_operations_htl;
DROP TRIGGER IF EXISTS audit_chantiers ON chantiers;
DROP FUNCTION IF EXISTS trigger_chantier_audit CASCADE;