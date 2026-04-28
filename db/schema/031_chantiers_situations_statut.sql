-- 031_chantiers_situations_statut.sql
-- Ajoute le statut aux situations + table lignes de détail
-- Doit être exécuté APRÈS 028b_chantiers_fonctions.sql

-- ============================================
-- ENUM : statut de situation
-- ============================================
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_situation_statut')
THEN CREATE TYPE chantier_situation_statut AS ENUM ('ouverte', 'validee', 'transmise', 'payee'); END IF; END $$;

-- ============================================
-- COLONNES ajoutées à chantier_situations
-- ============================================
ALTER TABLE chantier_situations ADD COLUMN IF NOT EXISTS statut chantier_situation_statut DEFAULT 'ouverte';
ALTER TABLE chantier_situations ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'situation';
ALTER TABLE chantier_situations ADD COLUMN IF NOT EXISTS periode_debut DATE;
ALTER TABLE chantier_situations ADD COLUMN IF NOT EXISTS periode_fin DATE;

UPDATE chantier_situations SET statut = 'ouverte' WHERE statut IS NULL OR statut = 'validee';

-- ============================================
-- TABLE : chantier_situation_lignes
-- ============================================
CREATE TABLE IF NOT EXISTS chantier_situation_lignes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    situation_id UUID NOT NULL REFERENCES chantier_situations(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantite DECIMAL(10,2) DEFAULT 0,
    unite TEXT DEFAULT '',
    prix_unitaire DECIMAL(15,2) DEFAULT 0,
    montant_total DECIMAL(15,2) DEFAULT 0,
    avancement_pourcentage DECIMAL(5,2) DEFAULT 0,
    avancement_montant DECIMAL(15,2) DEFAULT 0,
    photo_url TEXT DEFAULT '',
    approuvee BOOLEAN DEFAULT FALSE,
    approuvee_par UUID REFERENCES users(id) ON DELETE SET NULL,
    approuvee_le TIMESTAMP,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_situation_lignes_situation ON chantier_situation_lignes(situation_id);
CREATE INDEX IF NOT EXISTS idx_situation_lignes_org ON chantier_situation_lignes(org_id);
CREATE INDEX IF NOT EXISTS idx_situation_lignes_approuvee ON chantier_situation_lignes(approuvee);

-- ============================================
-- PHOTO preuve pour opérations HITL
-- ============================================
ALTER TABLE chantier_operations_htl ADD COLUMN IF NOT EXISTS photo_url TEXT DEFAULT '';

-- ============================================
-- INDEX sur photo_url (recherche par preuve)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_chantier_operations_photo ON chantier_operations_htl(photo_url) WHERE photo_url != '';
