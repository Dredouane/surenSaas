-- 029e_chantiers_seed_receptions.sql
-- Run AFTER 029_chantiers_seed.sql

WITH _cfg AS (SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1)
INSERT INTO chantier_receptions (id, chantier_id, org_id, date, type, statut, participants, ordre_du_jour, decisions, points_a_regler, documents, created_by, created_at, updated_at)
SELECT gen_random_uuid(), c.id, (SELECT _org_id FROM _cfg), d::timestamp, tp::chantier_reception_type, st::chantier_reception_statut, parts, odj, dec, pts, ARRAY[]::text[], NULL::uuid, d::timestamp, d::timestamp
FROM (VALUES
    ('CRF', '2026-04-10T14:00:00Z', 'validation', 'terminee', ARRAY['Client Dupont', 'Mohsan MAHMOOD', 'Gerant Principal']::text[], 'Validation finition peinture - Electricite - Plomberie', 'Peinture validee - Electricite a revoir - Plomberie OK', 'Prise salle de bain mal positionnee - Joints sanitaires a refaire'),
    ('CRF', '2026-04-17T10:00:00Z', 'livraison', 'en_cours', ARRAY['Client Dupont', 'Mohsan MAHMOOD']::text[], 'Livraison materiaux finition - Validation planning final', '', ''),
    ('CH-014', '2026-04-15T11:00:00Z', 'probleme', 'terminee', ARRAY['Client Martin', 'Jean DUPONT', 'Gerant Principal']::text[], 'Probleme infiltration eau - Diagnostic et solution', 'Reparation toiture prevue le 22/04 - Dedommagement client', 'Nettoyage degats eau - Peinture a refaire')
) AS t(ref_chantier, d, tp, st, parts, odj, dec, pts)
JOIN chantiers c ON c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg);

SELECT 'receptions OK' AS result;
