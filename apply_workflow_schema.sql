-- Standardiser le workflow sur toutes les tables
-- Ajout des colonnes si elles manquent (SQL compatible PostgreSQL/Supabase)

DO $$ BEGIN
  -- chantier_pointages
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chantier_pointages' AND column_name='status') THEN
    ALTER TABLE chantier_pointages ADD COLUMN status TEXT DEFAULT 'en_attente';
    ALTER TABLE chantier_pointages ADD COLUMN ocr_data JSONB DEFAULT '{}';
    ALTER TABLE chantier_pointages ADD COLUMN metadata JSONB DEFAULT '{}';
  END IF;

  -- chantier_taches
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chantier_taches' AND column_name='ocr_data') THEN
    ALTER TABLE chantier_taches ADD COLUMN ocr_data JSONB DEFAULT '{}';
    ALTER TABLE chantier_taches ADD COLUMN metadata JSONB DEFAULT '{}';
  END IF;
  
  -- Ajouter status aux opérations si absent (déjà présent dans 028a)
END $$;
