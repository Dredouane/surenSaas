-- 029z_chantiers_seed_recalcul.sql
-- Run LAST to recalculate all chantier metrics

SELECT recalculer_metriques_chantier(id) FROM chantiers;
SELECT 'recalcul OK' AS result;





ALTER TABLE telegram_users 
ADD COLUMN IF NOT EXISTS last_chantier_id UUID REFERENCES chantiers(id) ON DELETE SET NULL;