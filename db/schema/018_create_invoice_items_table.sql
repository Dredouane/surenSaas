
-- 018_create_invoice_items_table.sql
-- Création de la table invoice_items pour stocker les lignes de détail des factures

-- Table des lignes de facture
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Détails de la ligne
    description TEXT NOT NULL,
    quantity DECIMAL(10, 2),
    unit_price DECIMAL(10, 2),
    total_ht DECIMAL(10, 2),
    vat_rate DECIMAL(5, 2),
    
    -- Ordre d'affichage
    sort_order INTEGER DEFAULT 0,
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_org ON invoice_items(org_id);

-- Trigger pour updated_at
CREATE TRIGGER update_invoice_items_updated_at
    BEFORE UPDATE ON invoice_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Commentaires
COMMENT ON TABLE invoice_items IS 'Lignes de détail des factures (items extraits par OCR)';
COMMENT ON COLUMN invoice_items.invoice_id IS 'Référence vers la facture parent';
COMMENT ON COLUMN invoice_items.description IS 'Description du produit/service';
COMMENT ON COLUMN invoice_items.quantity IS 'Quantité';
COMMENT ON COLUMN invoice_items.unit_price IS 'Prix unitaire HT';
COMMENT ON COLUMN invoice_items.total_ht IS 'Total HT (quantity * unit_price)';
COMMENT ON COLUMN invoice_items.vat_rate IS 'Taux de TVA en %';
COMMENT ON COLUMN invoice_items.sort_order IS 'Ordre daffichage des lignes';

-- Migration des données existantes
-- Si des factures ont des items dans le champ JSON 'items', les migrer
DO $$
BEGIN
    -- Vérifier si la colonne items existe dans invoices
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'invoices' AND column_name = 'items') THEN
        
        -- Migrer les items existants depuis le JSON
        INSERT INTO invoice_items (invoice_id, org_id, description, quantity, unit_price, total_ht, vat_rate, sort_order)
        SELECT 
            i.id as invoice_id,
            i.org_id,
            item->>'description' as description,
            (item->>'quantity')::decimal as quantity,
            (item->>'unit_price')::decimal as unit_price,
            (item->>'total_ht')::decimal as total_ht,
            (item->>'vat_rate')::decimal as vat_rate,
            (item->>'sort_order')::integer as sort_order
        FROM invoices i
        CROSS JOIN LATERAL jsonb_array_elements(i.items::jsonb) as item
        WHERE i.items IS NOT NULL 
          AND i.items != '[]'
          AND i.items != 'null';
        
        RAISE NOTICE 'Migration des items existants terminée';
    END IF;
END $$;

-- RLS Policies (désactivées par défaut pour le prototypage)
-- À activer en production avec les bonnes policies
-- ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;

SELECT 'Table invoice_items créée avec succès' AS status;
