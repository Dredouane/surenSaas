-- 029g_chantiers_seed_ressources.sql
-- Run AFTER 029_chantiers_seed.sql

WITH _cfg AS (SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1),
res_insert AS (
    INSERT INTO chantier_ressources (id, org_id, chantier_id, nom, type, specialite, disponible, indisponible_jusquau, raison_indisponibilite, created_at, updated_at)
    SELECT gen_random_uuid(), (SELECT _org_id FROM _cfg), c.id, nom, tp::chantier_ressource_type, spec, disp, indispo::date, raison, '2026-01-15'::timestamp, '2026-04-21T07:00:00Z'::timestamp
    FROM (VALUES
        ('CRF', 'Jean DUPONT', 'homme', 'Macon', TRUE, NULL::text, ''),
        ('CRF', 'Pierre MARTIN', 'homme', 'Electricien', TRUE, NULL::text, ''),
        ('CRF', 'Paul DURAND', 'homme', 'Plombier', FALSE, '2026-04-25', 'Conges'),
        ('CH-014', 'Jacques LEROY', 'homme', 'Peintre', TRUE, NULL::text, ''),
        (NULL, 'Marc BERNARD', 'homme', 'Menuisier', TRUE, NULL::text, ''),
        ('CRF', 'Grue 5T', 'machine', 'Levage', TRUE, NULL::text, ''),
        ('CRF', 'Betonniere', 'machine', 'Beton', TRUE, NULL::text, ''),
        (NULL, 'Compresseur', 'machine', 'Air comprime', FALSE, NULL::text, 'Maintenance'),
        ('CH-014', 'Nacelle 12m', 'machine', 'Elevation', TRUE, NULL::text, ''),
        (NULL, 'Camion benne 10T', 'machine', 'Transport', TRUE, NULL::text, '')
    ) AS t(ref_chantier, nom, tp, spec, disp, indispo, raison)
    LEFT JOIN chantiers c ON (t.ref_chantier IS NOT NULL AND c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg))
    RETURNING id, nom
)
SELECT 'ressources OK' AS result;
