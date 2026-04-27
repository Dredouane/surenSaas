-- Ajout du champ statut sur chantier_depenses pour permettre la validation
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_depense_statut') THEN
        CREATE TYPE chantier_depense_statut AS ENUM ('en_attente', 'validee', 'rejetee');
    END IF;
END $$;

ALTER TABLE chantier_depenses ADD COLUMN IF NOT EXISTS statut chantier_depense_statut DEFAULT 'validee';
ALTER TABLE chantier_depenses ADD COLUMN IF NOT EXISTS valide_par UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE chantier_depenses ADD COLUMN IF NOT EXISTS valide_le TIMESTAMP;
