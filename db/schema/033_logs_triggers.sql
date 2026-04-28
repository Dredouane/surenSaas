-- 033_logs_triggers.sql
-- Triggers génériques pour alimenter logs_activity automatiquement
-- Remplace: trigger_chantier_audit, log_invoice_status_change

-- Trigger générique: insère dans logs_activity sur INSERT
CREATE OR REPLACE FUNCTION log_activity_insert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO logs_activity (org_id, correlation_id, action, table_name, entity_id, entity_ref, new_state, source_system)
    VALUES (
        NEW.org_id,
        COALESCE(NEW.correlation_id, gen_random_uuid()),
        'create',
        TG_TABLE_NAME,
        NEW.id,
        NEW.ref,
        row_to_json(NEW)::jsonb,
        'db_trigger'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger générique: insère dans logs_activity sur UPDATE
CREATE OR REPLACE FUNCTION log_activity_update()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO logs_activity (org_id, correlation_id, action, table_name, entity_id, entity_ref, previous_state, new_state, delta, source_system)
    VALUES (
        NEW.org_id,
        COALESCE(NEW.correlation_id, gen_random_uuid()),
        'update',
        TG_TABLE_NAME,
        NEW.id,
        NEW.ref,
        row_to_json(OLD)::jsonb,
        row_to_json(NEW)::jsonb,
        jsonb_strip_nulls(jsonb_build_object(
            'changed_fields', (SELECT jsonb_object_agg(key, jsonb_build_object('old', OLD[key], 'new', NEW[key]))
                FROM jsonb_object_keys(row_to_json(NEW)::jsonb) AS key
                WHERE OLD[key] IS DISTINCT FROM NEW[key])
        )),
        'db_trigger'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger générique: insère dans logs_activity sur DELETE
CREATE OR REPLACE FUNCTION log_activity_delete()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO logs_activity (org_id, correlation_id, action, table_name, entity_id, entity_ref, previous_state, source_system)
    VALUES (
        OLD.org_id,
        COALESCE(OLD.correlation_id, gen_random_uuid()),
        'delete',
        TG_TABLE_NAME,
        OLD.id,
        OLD.ref,
        row_to_json(OLD)::jsonb,
        'db_trigger'
    );
    RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
