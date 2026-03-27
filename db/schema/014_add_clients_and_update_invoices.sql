-- 014_add_clients_and_update_invoices.sql
-- Ajoute la table clients et modifie la table invoices existante pour supporter client_id

-- ============================================
-- TABLE CLIENTS
-- ============================================

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    siret VARCHAR(14),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour clients
CREATE INDEX IF NOT EXISTS idx_clients_org_id ON clients(org_id);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);

-- Trigger updated_at pour clients
DROP TRIGGER IF EXISTS update_clients_updated_at ON clients;
CREATE TRIGGER update_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies pour clients
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "members_read_clients" ON clients
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "members_insert_clients" ON clients
    FOR INSERT WITH CHECK (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "members_update_clients" ON clients
    FOR UPDATE USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "admins_delete_clients" ON clients
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM user_org_membership 
            WHERE user_id = auth.uid() 
            AND org_id = clients.org_id 
            AND role = 'admin'
        )
    );

-- ============================================
-- MISE À JOUR TABLE INVOICES EXISTANTE
-- ============================================

-- Ajoute client_id comme colonne optionnelle (lien vers clients)
-- La colonne company_id reste pour la compatibilité
ALTER TABLE invoices 
    ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id) ON DELETE SET NULL;

-- Ajoute un index sur client_id
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);

-- ============================================
-- TABLE INVOICE STATUS HISTORY
-- ============================================

CREATE TABLE IF NOT EXISTS invoice_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by UUID NOT NULL REFERENCES auth.users(id),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoice_status_history_invoice_id ON invoice_status_history(invoice_id);

-- RLS pour invoice_status_history
ALTER TABLE invoice_status_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "members_read_invoice_history" ON invoice_status_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM invoices i
            WHERE i.id = invoice_status_history.invoice_id
            AND i.org_id IN (
                SELECT org_id FROM user_org_membership 
                WHERE user_id = auth.uid()
            )
        )
    );

-- Commentaires
COMMENT ON TABLE clients IS 'Table des clients/partenaires des organisations';
COMMENT ON COLUMN invoices.client_id IS 'Lien optionnel vers la table clients (ajouté dans migration 014)';
