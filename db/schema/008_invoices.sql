-- 008_invoices.sql
-- Table des factures chantiers pour l'entreprise construction

CREATE TYPE invoice_status AS ENUM (
    'brouillon',
    'en_attente_validation',
    'validee',
    'rejetee',
    'en_traitement_comptable',
    'archivee'
);

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Informations facture
    invoice_number TEXT,                    -- Numéro de facture (si déjà existant)
    supplier_name TEXT NOT NULL,            -- Nom fournisseur
    supplier_address TEXT,                  -- Adresse fournisseur
    supplier_siret TEXT,                    -- SIRET fournisseur
    
    -- Montants
    amount_ht DECIMAL(12, 2),              -- Montant HT
    amount_ttc DECIMAL(12, 2) NOT NULL,     -- Montant TTC
    vat_amount DECIMAL(12, 2),             -- Montant TVA
    vat_rate DECIMAL(5, 2),                -- Taux TVA (%)
    
    -- Dates
    invoice_date DATE,                      -- Date facture
    due_date DATE,                          -- Date échéance
    
    -- Description et détails
    description TEXT,                       -- Description/descriptif
    items JSONB DEFAULT '[]'::jsonb,        -- Lignes de facture [{label, qty, unit_price}]
    
    -- Médias
    original_file_url TEXT,                 -- URL fichier original (PDF ou photo)
    thumbnail_url TEXT,                     -- URL miniature
    
    -- Status et workflow
    status invoice_status DEFAULT 'brouillon',
    
    -- Traçabilité
    created_by UUID REFERENCES auth.users(id),           -- Qui a créé (bot ou user)
    created_by_telegram BOOLEAN DEFAULT false,            -- Créé via Telegram
    validated_by UUID REFERENCES auth.users(id),         -- Qui a validé (gérant)
    validated_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,                                -- Raison rejet
    
    -- Métadonnées
    ocr_data JSONB DEFAULT '{}'::jsonb,      -- Données brutes OCR
    metadata JSONB DEFAULT '{}'::jsonb,      -- Métadonnées diverses
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_invoices_org ON invoices(org_id);
CREATE INDEX IF NOT EXISTS idx_invoices_company ON invoices(company_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_created_by ON invoices(created_by);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_supplier ON invoices(supplier_name);

-- Trigger updated_at
CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Users peuvent voir les factures de leur org
CREATE POLICY "members_read_invoices" ON invoices
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
    );

-- Insertion: users avec capability write ou admin
CREATE POLICY "authorized_insert_invoices" ON invoices
    FOR INSERT WITH CHECK (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
        AND (
            -- Admin
            EXISTS (
                SELECT 1 FROM user_org_membership 
                WHERE user_id = auth.uid() 
                AND org_id = invoices.org_id 
                AND role = 'admin'
            )
            OR
            -- Capability construction:facturation:write
            EXISTS (
                SELECT 1 FROM user_active_capabilities
                WHERE user_id = auth.uid()
                AND org_id = invoices.org_id
                AND capability_code = 'construction:facturation:write'
            )
        )
    );

-- Update: même logique
CREATE POLICY "authorized_update_invoices" ON invoices
    FOR UPDATE USING (
        org_id IN (
            SELECT org_id FROM user_org_membership 
            WHERE user_id = auth.uid()
        )
        AND (
            EXISTS (
                SELECT 1 FROM user_org_membership 
                WHERE user_id = auth.uid() 
                AND org_id = invoices.org_id 
                AND role = 'admin'
            )
            OR
            EXISTS (
                SELECT 1 FROM user_active_capabilities
                WHERE user_id = auth.uid()
                AND org_id = invoices.org_id
                AND capability_code = 'construction:facturation:write'
            )
        )
    );
