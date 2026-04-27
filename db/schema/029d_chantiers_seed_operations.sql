-- 029d_chantiers_seed_operations.sql
-- Run AFTER 029_chantiers_seed.sql

WITH _cfg AS (SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1)
INSERT INTO chantier_operations_htl (id, chantier_id, org_id, description, type, date, source, source_details, statut, valide_par, valide_le, commentaire, montant, unite, quantite, created_at, updated_at)
SELECT gen_random_uuid(), c.id, (SELECT _org_id FROM _cfg), descr, tp::chantier_operation_type, dt::timestamp, src::chantier_operation_source, src_det, st::chantier_operation_statut, NULL::uuid, vl, comm, mont, unt, qte, dt::timestamp, COALESCE(vl, dt::timestamp)
FROM (VALUES
    ('CRF', 'Demolition mur est', 'demolition', '2026-04-15T09:42:00Z'::timestamp, 'telegram_voice', 'Voice Telegram - Mohsan - 15/04/2026 09:42', 'valide', '2026-04-15T10:05:00Z'::timestamp, 'Travail conforme aux plans', NULL::numeric, NULL::text, NULL::numeric),
    ('CRF', 'Nettoyage facade sud', 'nettoyage', '2026-04-16T14:30:00Z'::timestamp, 'telegram_text', 'Texte Telegram - Mohsan - 16/04/2026 14:30', 'valide', '2026-04-16T15:15:00Z'::timestamp, '180 m2 nettoyes', NULL::numeric, 'm2', 180::numeric),
    ('CRF', 'Commande 3 echafaudages chez PointP', 'commande', '2026-04-17T11:20:00Z'::timestamp, 'telegram_voice', 'Voice Telegram - Mohsan - 17/04/2026 11:20', 'valide', '2026-04-17T12:00:00Z'::timestamp, 'Pour livraison le 20/04', 12000::numeric, 'unites', 3::numeric),
    ('CRF', 'Pose de 4 BSO (Blocs Securite Ouvrants)', 'pose_bso', '2026-04-18T16:45:00Z'::timestamp, 'telegram_photo', 'Photo Telegram - Mohsan - 18/04/2026 16:45', 'en_attente', NULL::timestamp, 'En attente de validation du gerant', NULL::numeric, 'unites', 4::numeric),
    ('CRF', 'Reception bon de livraison materiaux', 'achat_materiel', '2026-04-19T10:15:00Z'::timestamp, 'telegram_pdf', 'PDF Telegram - Mohsan - 19/04/2026 10:15', 'en_attente', NULL::timestamp, 'Document a verifier', NULL::numeric, NULL::text, NULL::numeric),
    ('CRF', 'Preparation chantier pour peinture', 'autre', '2026-04-20T08:30:00Z'::timestamp, 'manuel', 'Ajout manuel - Gerant - 20/04/2026 08:30', 'valide', '2026-04-20T08:30:00Z'::timestamp, 'A faire avant le 22/04', NULL::numeric, NULL::text, NULL::numeric)
) AS t(ref_chantier, descr, tp, dt, src, src_det, st, vl, comm, mont, unt, qte)
JOIN chantiers c ON c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg);

SELECT 'operations OK' AS result;
