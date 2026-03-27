-- 012_invoice_status_history.sql
-- Historique de tous les changements de status des factures (traçabilité complète)

CREATE TABLE IF NOT EXISTS invoice_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Changement de status
    previous_status invoice_status,
    new_status invoice_status NOT NULL,
    
    -- Qui a fait le changement
    changed_by UUID REFERENCES auth.users(id),           -- User interne
    changed_by_telegram BOOLEAN DEFAULT false,            -- Via Telegram
    telegram_user_id BIGINT,                              -- Si via Telegram
    
    -- Contexte
    change_reason TEXT,                                   -- Raison du changement
    context JSONB DEFAULT '{}'::jsonb,                    -- Contexte (IP, user-agent, etc.)
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_invoice_status_history_invoice ON invoice_status_history(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status_history_org ON invoice_status_history(org_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status_history_created ON invoice_status_history(created_at);
CREATE INDEX IF NOT EXISTS idx_invoice_status_history_changed_by ON invoice_status_history(changed_by);

-- RLS Policies
ALTER TABLE invoice_status_history ENABLE ROW LEVEL SECURITY;

-- Tous les membres de l'org peuvent voir l'historique
CREATE POLICY "members_read_status_history" ON invoice_status_history
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
    );

-- Trigger pour enregistrer automatiquement les changements de status
CREATE OR REPLACE FUNCTION log_invoice_status_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Ne logger que si le status a changé
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO invoice_status_history (
            invoice_id,
            org_id,
            previous_status,
            new_status,
            changed_by,
            changed_by_telegram,
            telegram_user_id,
            change_reason,
            context
        ) VALUES (
            NEW.id,
            NEW.org_id,
            OLD.status,
            NEW.status,
            NEW.updated_by,
            NEW.created_by_telegram,
            NULL,  -- TODO: récupérer telegram_user_id si applicable
            NEW.rejection_reason,  -- Si rejet, la raison est stockée ici
            jsonb_build_object(
                'updated_at', NEW.updated_at
            )
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_log_invoice_status_change
    AFTER UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION log_invoice_status_change();
