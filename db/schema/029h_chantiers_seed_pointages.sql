-- 029h_chantiers_seed_pointages.sql
-- Run AFTER 029_chantiers_seed.sql and 029g_chantiers_seed_ressources.sql

WITH _cfg AS (SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1),
point_insert AS (
    INSERT INTO chantier_pointages (id, chantier_id, org_id, conducteur_id, date, commentaires, valide_par, valide_le, created_at, updated_at)
    SELECT gen_random_uuid(), c.id, (SELECT _org_id FROM _cfg), NULL::uuid, d::date, comm, NULL::uuid, vl::timestamp, cr_at::timestamp, vl::timestamp
    FROM (VALUES
        ('CRF', '2026-04-21', 'Journee dediee a la finition beton et electricite', '2026-04-21T09:00:00Z', '2026-04-21T07:30:00Z'),
        ('CRF', '2026-04-20', 'Pierre absent apres-midi - rendez-vous medical', '2026-04-20T08:45:00Z', '2026-04-20T07:15:00Z')
    ) AS t(ref_chantier, d, comm, vl, cr_at)
    JOIN chantiers c ON c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg)
    RETURNING id, date
),
p21 AS (SELECT id FROM point_insert WHERE date = '2026-04-21'::date),
p20 AS (SELECT id FROM point_insert WHERE date = '2026-04-20'::date),
jean AS (SELECT id FROM chantier_ressources WHERE nom = 'Jean DUPONT'),
pierre AS (SELECT id FROM chantier_ressources WHERE nom = 'Pierre MARTIN'),
grue AS (SELECT id FROM chantier_ressources WHERE nom = 'Grue 5T'),
beton AS (SELECT id FROM chantier_ressources WHERE nom = 'Betonniere')
INSERT INTO chantier_pointage_ressources (pointage_id, ressource_id, org_id, periode, heures_prevues, presence)
SELECT pid, rid, (SELECT _org_id FROM _cfg), per::chantier_pointage_periode, hp, TRUE
FROM (VALUES
    ((SELECT id FROM p21), (SELECT id FROM jean), 'journee', 8),
    ((SELECT id FROM p21), (SELECT id FROM pierre), 'journee', 8),
    ((SELECT id FROM p21), (SELECT id FROM grue), 'matin', 4),
    ((SELECT id FROM p21), (SELECT id FROM beton), 'apres_midi', 4),
    ((SELECT id FROM p20), (SELECT id FROM jean), 'journee', 8),
    ((SELECT id FROM p20), (SELECT id FROM pierre), 'matin', 4),
    ((SELECT id FROM p20), (SELECT id FROM beton), 'journee', 8)
) AS t(pid, rid, per, hp);

SELECT 'pointages OK' AS result;
