-- 029c_chantiers_seed_depenses.sql
-- Run AFTER 029_chantiers_seed.sql

WITH _cfg AS (SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1)
INSERT INTO chantier_depenses (id, chantier_id, org_id, date, fournisseur, categorie, description, montant, facture_ref, created_by, created_at, updated_at)
SELECT gen_random_uuid(), c.id, (SELECT _org_id FROM _cfg), '2026-04-17'::date, f, cat::chantier_depense_categorie, d, m, '', NULL::uuid, '2026-04-17'::timestamp, '2026-04-17'::timestamp
FROM (VALUES
    ('CRF', 'ART CONCEPT', 'sous_traitant', 'Achat materiaux pour Fehmi PointP', 41663.61),
    ('CRF', 'ART CONCEPT', 'sous_traitant', 'Achats divers', 58218.97),
    ('CRF', 'ART CONCEPT', 'sous_traitant', 'Avances sur situations (virements)', 281256.96),
    ('CRF', 'BOB RENOV', 'fournisseur', 'Mext', 61366.99),
    ('CRF', 'PCCR', 'sous_traitant', 'Plomberie CVCPB', 48742.00),
    ('CRF', 'B6 CONCEPT', 'fournisseur', 'BET', 5850.00),
    ('CRF', 'AA Ingenierie', 'fournisseur', 'BET', 2900.00),
    ('CRF', 'Polybat', 'fournisseur', 'RAVALEMENT', 38844.00),
    ('CRF', 'SENBAIE', 'fournisseur', 'BSO', 19000.00),
    ('CRF', 'Copypage', 'fournisseur', 'IMPRESSION PLANS', 200.00),
    ('CRF', 'FULFILER', 'fournisseur', 'IMPRESSION PLANS', 265.00),
    ('CRF', 'EDM', 'fournisseur', 'INSTALLATION DE CHANTIER', 4546.80),
    ('CRF', 'MOHSAN MAHMOOD', 'autre', 'SUIVI DE CHANTIER', 50400.00)
) AS t(ref_chantier, f, cat, d, m)
JOIN chantiers c ON c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg);

SELECT 'depenses OK' AS result;
