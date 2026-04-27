-- 029b_chantiers_seed_situations.sql
-- Run AFTER 029_chantiers_seed.sql

WITH _cfg AS (
    SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1
)
INSERT INTO chantier_situations (id, chantier_id, org_id, date, numero, libelle, montant, reglement_observation, created_by, created_at, updated_at)
SELECT gen_random_uuid(), c.id, (SELECT _org_id FROM _cfg), d::date, n, 'Situation N ' || n::text, m, '', NULL::uuid, '2024-01-15'::timestamp, '2024-01-15'::timestamp
FROM (VALUES
    ('CRF', '2025-05-23', 1, 55240.18),
    ('CRF', '2025-06-23', 2, 84978.08),
    ('CRF', '2025-07-21', 3, 129012.13),
    ('CRF', '2025-08-29', 4, 65246.58),
    ('CRF', '2025-09-29', 5, 56104.41),
    ('CRF', '2025-11-05', 6, 75411.35),
    ('CRF', '2025-12-05', 7, 61478.68),
    ('CRF', '2025-12-26', 8, 107726.24),
    ('CRF', '2026-01-21', 9, 71211.91),
    ('CRF', '2026-02-20', 10, 107760.65),
    ('CRF', '2026-04-02', 11, 86618.83)
) AS t(ref_chantier, d, n, m)
JOIN chantiers c ON c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg)
WHERE NOT EXISTS (
    SELECT 1 FROM chantier_situations s
    JOIN chantiers c2 ON c2.id = s.chantier_id
    WHERE c2.ref = t.ref_chantier AND s.numero = t.n
);

SELECT 'situations OK' AS result;
