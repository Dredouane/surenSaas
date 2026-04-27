-- 029i_chantiers_seed_notifications.sql
-- Run AFTER 029_chantiers_seed.sql

WITH _cfg AS (SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1)
INSERT INTO chantier_notifications (id, chantier_id, org_id, user_id, type, titre, message, url, statut, telegram_message_id, created_at)
SELECT gen_random_uuid(), c.id, (SELECT _org_id FROM _cfg), NULL::uuid, tp::chantier_notification_type, titre, msg,
    '/dashboard/chantiers/' || c.id::text || CASE WHEN tab IS NOT NULL THEN '?tab=' || tab ELSE '' END,
    st::chantier_notification_statut, tmid, cr_at::timestamp
FROM (VALUES
    ('CRF', 'tache', 'Nouvelle tache assignee', 'Vous avez une nouvelle tache: Verification fondations', 'taches', 'envoyee', 'telegram-msg-001', '2026-04-15T08:30:00Z'),
    ('CRF', 'validation', 'Tache terminee - A valider', 'Mohsan a confirme la livraison carrelage', 'taches', 'validee', 'telegram-msg-002', '2026-04-17T11:45:00Z'),
    ('CRF', 'pointage', 'Pointage valide', 'Votre pointage du 21/04 a ete valide par le gerant', 'pointages', 'lue', 'telegram-msg-003', '2026-04-21T09:00:00Z'),
    ('CRF', 'reception', 'Nouvelle reception client', 'Mohsan a ajoute une reception pour le chantier CRF', 'receptions', 'en_attente', 'telegram-msg-004', '2026-04-10T16:30:00Z'),
    ('CRF', 'alerte', 'Machine indisponible', 'Le compresseur est en maintenance jusqu a nouvel ordre', NULL, 'refusee', 'telegram-msg-005', '2026-04-20T16:30:00Z')
) AS t(ref_chantier, tp, titre, msg, tab, st, tmid, cr_at)
JOIN chantiers c ON c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg);

SELECT 'notifications OK' AS result;
