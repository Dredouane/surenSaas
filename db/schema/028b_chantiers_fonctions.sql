-- 028b_chantiers_fonctions.sql
-- Functions, metriques triggers, audit triggers
-- Run AFTER 028a_chantiers_tables.sql

-- ============================================
-- FONCTION : recalculer_metriques_chantier
-- ============================================
CREATE OR REPLACE FUNCTION recalculer_metriques_chantier(p_chantier_id UUID) RETURNS VOID LANGUAGE plpgsql AS $body$
DECLARE v_montant_base DECIMAL(15,2); v_ts_avenants DECIMAL(15,2); v_total_situations DECIMAL(15,2); v_total_depenses DECIMAL(15,2); v_montant_revise DECIMAL(15,2); v_pourcentage DECIMAL(5,2); v_marge DECIMAL(15,2); v_solde DECIMAL(15,2);
BEGIN
    SELECT montant_base, ts_avenants INTO v_montant_base, v_ts_avenants FROM chantiers WHERE id = p_chantier_id;
    v_montant_revise := COALESCE(v_montant_base, 0) + COALESCE(v_ts_avenants, 0);
    SELECT COALESCE(SUM(montant), 0) INTO v_total_situations FROM chantier_situations WHERE chantier_id = p_chantier_id;
    SELECT COALESCE(SUM(montant), 0) INTO v_total_depenses FROM chantier_depenses WHERE chantier_id = p_chantier_id;
    IF v_montant_revise > 0 THEN v_pourcentage := (v_total_situations / v_montant_revise) * 100; ELSE v_pourcentage := 0; END IF;
    v_marge := v_montant_revise - v_total_depenses; v_solde := v_montant_revise - v_total_situations;
    UPDATE chantiers SET montant_revise = v_montant_revise, situations_facturees = v_total_situations, pourcentage_facture = v_pourcentage, total_depenses = v_total_depenses, marge_brute = v_marge, solde_a_facturer = v_solde, updated_at = NOW() WHERE id = p_chantier_id;
END;
$body$;

-- ============================================
-- FONCTION : trigger recalcul metriques
-- ============================================
CREATE OR REPLACE FUNCTION trigger_recalculer_metriques_chantier() RETURNS TRIGGER LANGUAGE plpgsql AS $body$
DECLARE v_chantier_id UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN v_chantier_id := OLD.chantier_id; ELSE v_chantier_id := NEW.chantier_id; END IF;
    PERFORM recalculer_metriques_chantier(v_chantier_id); RETURN COALESCE(NEW, OLD);
END;
$body$;

CREATE TRIGGER trigger_chantier_situations_metriques AFTER INSERT OR UPDATE OR DELETE ON chantier_situations FOR EACH ROW EXECUTE FUNCTION trigger_recalculer_metriques_chantier();
CREATE TRIGGER trigger_chantier_depenses_metriques AFTER INSERT OR UPDATE OR DELETE ON chantier_depenses FOR EACH ROW EXECUTE FUNCTION trigger_recalculer_metriques_chantier();

-- ============================================
-- FONCTION : Audit trail automatique
-- ============================================
CREATE OR REPLACE FUNCTION trigger_chantier_audit() RETURNS TRIGGER LANGUAGE plpgsql AS $body$
DECLARE v_entity_type TEXT; v_action chantier_audit_action; v_changes JSONB := '{}'::jsonb; v_chantier_id UUID; v_org_id UUID;
BEGIN
    v_entity_type := TG_TABLE_NAME;
    IF TG_OP = 'INSERT' THEN v_action := 'creation'; ELSIF TG_OP = 'UPDATE' THEN v_action := 'modification'; v_changes := jsonb_build_object('old', row_to_json(OLD), 'new', row_to_json(NEW)); ELSIF TG_OP = 'DELETE' THEN v_action := 'suppression'; END IF;
    IF TG_TABLE_NAME = 'chantiers' THEN v_chantier_id := COALESCE(NEW.id, OLD.id); v_org_id := COALESCE(NEW.org_id, OLD.org_id); ELSE v_chantier_id := COALESCE(NEW.chantier_id, OLD.chantier_id); v_org_id := COALESCE(NEW.org_id, OLD.org_id); END IF;
    INSERT INTO chantier_audit_trail (chantier_id, org_id, entity_type, entity_id, action, details, changes) VALUES (v_chantier_id, v_org_id, v_entity_type, COALESCE(NEW.id, OLD.id), v_action, CASE WHEN TG_OP = 'INSERT' THEN 'Creation' WHEN TG_OP = 'UPDATE' THEN 'Modification' ELSE 'Suppression' END, v_changes);
    RETURN COALESCE(NEW, OLD);
END;
$body$;

CREATE TRIGGER audit_chantiers AFTER INSERT OR UPDATE OR DELETE ON chantiers FOR EACH ROW EXECUTE FUNCTION trigger_chantier_audit();
CREATE TRIGGER audit_chantier_situations AFTER INSERT OR UPDATE OR DELETE ON chantier_situations FOR EACH ROW EXECUTE FUNCTION trigger_chantier_audit();
CREATE TRIGGER audit_chantier_depenses AFTER INSERT OR UPDATE OR DELETE ON chantier_depenses FOR EACH ROW EXECUTE FUNCTION trigger_chantier_audit();
