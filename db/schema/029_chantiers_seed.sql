-- 029_chantiers_seed.sql
-- Seed data for chantiers module
-- Run AFTER 028_chantiers.sql
-- Each INSERT is independent (no CTEs) for Supabase SQL Editor compatibility

-- === CONFIG: Replace these IDs with your actual Supabase IDs ===
-- Run these queries to find your IDs:
--   SELECT id FROM organizations LIMIT 1;
--   SELECT id, email FROM users LIMIT 5;
-- Then paste them below.

-- Configuration: set your actual org_id
-- Example: SELECT 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'::uuid AS _org_id;
-- We use a subquery to find the first org if you don't set a specific one.
WITH _cfg AS (
    SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1
),
_crf AS (
    INSERT INTO chantiers (id, org_id, ref, nom, adresse, conducteur, commentaires,
        montant_base, ts_avenants, montant_revise, situations_facturees, pourcentage_facture,
        total_depenses, marge_brute, solde_a_facturer, statut, priorite,
        date_opr_prevue, date_opr_realisee, created_by, created_at, updated_at)
    SELECT
        gen_random_uuid(), (SELECT _org_id FROM _cfg), 'CRF', 'CRF', '6/8 rue Entroncamento 94350 Villiers-sur-Marne', 'Mohsan MAHMOOD',
        'Chantier de renovation complete - Suivi financier Excel',
        929613.50, 88498.82, 1018112.32, 900789.04, 88.48,
        613254.33, 287534.71, 117323.28,
        'en_cours'::chantier_statut, 0,
        NULL::date, NULL::date,
        NULL::uuid,
        '2024-01-15'::timestamp, NOW()
    WHERE NOT EXISTS (SELECT 1 FROM chantiers WHERE ref = 'CRF' AND org_id = (SELECT _org_id FROM _cfg))
    RETURNING id
),
_ch014 AS (
    INSERT INTO chantiers (id, org_id, ref, nom, adresse, conducteur, commentaires,
        montant_base, ts_avenants, montant_revise, situations_facturees, pourcentage_facture,
        total_depenses, marge_brute, solde_a_facturer, statut, priorite,
        date_opr_prevue, date_opr_realisee, created_by, created_at, updated_at)
    SELECT
        gen_random_uuid(), (SELECT _org_id FROM _cfg), 'CH-014', 'Renovation Appartement Paris 15', '12 rue de Vaugirard, 75015 Paris', 'Jean DUPONT',
        'Renovation complete appartement 80m2',
        125000, 15000, 140000, 85000, 60.71,
        95000, 45000, 55000,
        'en_cours'::chantier_statut, 1, '2026-06-30'::date, NULL::date, NULL::uuid,
        '2024-02-10'::timestamp, NOW()
    WHERE NOT EXISTS (SELECT 1 FROM chantiers WHERE ref = 'CH-014' AND org_id = (SELECT _org_id FROM _cfg))
    RETURNING id
),
_ch015 AS (
    INSERT INTO chantiers (id, org_id, ref, nom, adresse, conducteur, commentaires,
        montant_base, ts_avenants, montant_revise, situations_facturees, pourcentage_facture,
        total_depenses, marge_brute, solde_a_facturer, statut, priorite,
        date_opr_prevue, date_opr_realisee, created_by, created_at, updated_at)
    SELECT
        gen_random_uuid(), (SELECT _org_id FROM _cfg), 'CH-015', 'Extension Maison Versailles', '45 avenue de Paris, 78000 Versailles', 'Marie LEROY',
        'Extension + renovation cuisine',
        285000, 35000, 320000, 220000, 68.75,
        195000, 125000, 100000,
        'en_cours'::chantier_statut, 2, '2026-08-15'::date, NULL::date, NULL::uuid,
        '2024-03-05'::timestamp, NOW()
    WHERE NOT EXISTS (SELECT 1 FROM chantiers WHERE ref = 'CH-015' AND org_id = (SELECT _org_id FROM _cfg))
    RETURNING id
),
_ch016 AS (
    INSERT INTO chantiers (id, org_id, ref, nom, adresse, conducteur, commentaires,
        montant_base, ts_avenants, montant_revise, situations_facturees, pourcentage_facture,
        total_depenses, marge_brute, solde_a_facturer, statut, priorite,
        date_opr_prevue, date_opr_realisee, created_by, created_at, updated_at)
    SELECT
        gen_random_uuid(), (SELECT _org_id FROM _cfg), 'CH-016', 'Bureaux Societe Tech', 'Tour Montparnasse, 75014 Paris', 'Pierre MARTIN',
        'Amenagement bureaux open space 500m2',
        450000, 50000, 500000, 400000, 80.00,
        320000, 180000, 100000,
        'en_cours'::chantier_statut, 0, '2026-05-20'::date, '2026-05-18'::date, NULL::uuid,
        '2024-01-20'::timestamp, NOW()
    WHERE NOT EXISTS (SELECT 1 FROM chantiers WHERE ref = 'CH-016' AND org_id = (SELECT _org_id FROM _cfg))
    RETURNING id
),
_ch017 AS (
    INSERT INTO chantiers (id, org_id, ref, nom, adresse, conducteur, commentaires,
        montant_base, ts_avenants, montant_revise, situations_facturees, pourcentage_facture,
        total_depenses, marge_brute, solde_a_facturer, statut, priorite,
        date_opr_prevue, date_opr_realisee, created_by, created_at, updated_at)
    SELECT
        gen_random_uuid(), (SELECT _org_id FROM _cfg), 'CH-017', 'Renovation Hotel Particulier', '8 rue de la Paix, 75002 Paris', 'Sophie DURAND',
        'En attente de permis de construire',
        750000, 125000, 875000, 600000, 68.57,
        520000, 355000, 275000,
        'en_attente'::chantier_statut, 3, '2026-09-30'::date, NULL::date, NULL::uuid,
        '2024-04-01'::timestamp, NOW()
    WHERE NOT EXISTS (SELECT 1 FROM chantiers WHERE ref = 'CH-017' AND org_id = (SELECT _org_id FROM _cfg))
    RETURNING id
),
_ch018 AS (
    INSERT INTO chantiers (id, org_id, ref, nom, adresse, conducteur, commentaires,
        montant_base, ts_avenants, montant_revise, situations_facturees, pourcentage_facture,
        total_depenses, marge_brute, solde_a_facturer, statut, priorite,
        date_opr_prevue, date_opr_realisee, created_by, created_at, updated_at)
    SELECT
        gen_random_uuid(), (SELECT _org_id FROM _cfg), 'CH-018', 'Magasin Commercial', 'Centre Commercial, 93100 Montreuil', 'Thomas BERNARD',
        'Livre avec 5 jours avance',
        320000, 30000, 350000, 350000, 100.00,
        280000, 70000, 0,
        'termine'::chantier_statut, 0, '2026-03-15'::date, '2026-03-10'::date, NULL::uuid,
        '2024-02-15'::timestamp, NOW()
    WHERE NOT EXISTS (SELECT 1 FROM chantiers WHERE ref = 'CH-018' AND org_id = (SELECT _org_id FROM _cfg))
    RETURNING id
)
SELECT 'chantiers OK' AS result;
