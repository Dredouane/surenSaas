-- Migration pour supporter le workflow générique (HITL)
-- Appliquer sur les tables concernées

DO $$ BEGIN
    -- chantier_pointages
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chantier_pointages' AND column_name='status') THEN
        ALTER TABLE chantier_pointages ADD COLUMN status TEXT DEFAULT 'en_attente_validation';
        ALTER TABLE chantier_pointages ADD COLUMN ocr_data JSONB DEFAULT '{}';
        ALTER TABLE chantier_pointages ADD COLUMN metadata JSONB DEFAULT '{}';
    END IF;

    -- chantier_depenses
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chantier_depenses' AND column_name='status') THEN
        ALTER TABLE chantier_depenses ADD COLUMN status TEXT DEFAULT 'en_attente_validation';
        ALTER TABLE chantier_depenses ADD COLUMN ocr_data JSONB DEFAULT '{}';
        ALTER TABLE chantier_depenses ADD COLUMN metadata JSONB DEFAULT '{}';
    END IF;
    
    -- chantier_taches
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chantier_taches' AND column_name='status') THEN
        -- Tâches a déjà un statut, on va le conserver mais ajouter ocr_data/metadata
        ALTER TABLE chantier_taches ADD COLUMN IF NOT EXISTS ocr_data JSONB DEFAULT '{}';
        ALTER TABLE chantier_taches ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
    END IF;
END $$;



ALTER TABLE telegram_users 
   ADD COLUMN IF NOT EXISTS last_state TEXT,
   ADD COLUMN IF NOT EXISTS last_state_data JSONB DEFAULT '{}';