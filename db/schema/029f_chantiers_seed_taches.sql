-- 029f_chantiers_seed_taches.sql
-- Run AFTER 029_chantiers_seed.sql

WITH _cfg AS (SELECT id AS _org_id FROM organizations ORDER BY created_at LIMIT 1)
INSERT INTO chantier_taches (id, chantier_id, org_id, reception_id, titre, description, type, source, priorite, statut, createur_id, createur_nom, assignee_id, assignee_nom, echeance, reponse, documents, created_at, updated_at)
SELECT gen_random_uuid(), c.id, (SELECT _org_id FROM _cfg), NULL::uuid, titre, descr, tp::chantier_tache_type, src::chantier_tache_source, prio::chantier_tache_priorite, st::chantier_tache_statut, NULL::uuid, cr_nom, NULL::uuid, as_nom, ech::timestamp, rep, ARRAY[]::text[], cr_at::timestamp, cr_at::timestamp
FROM (VALUES
    ('CRF', 'Envoyer photos avancement peinture', 'Photos des pieces principales apres finition peinture', 'rapport', 'direction', 'moyenne', 'en_attente', 'Gerant Principal', 'Mohsan MAHMOOD', '2026-04-18T17:00:00Z', '', '2026-04-17T09:00:00Z'),
    ('CRF', 'Confirmer livraison carrelage', 'Verifier quantite et qualite carrelage livre ce matin', 'validation', 'direction', 'haute', 'terminee', 'Gerant Principal', 'Mohsan MAHMOOD', '2026-04-17T12:00:00Z', 'Livraison conforme - 120m2 carrelage gris 60x60', '2026-04-17T08:30:00Z'),
    (NULL, 'Mettre a jour certifications securite', 'Renouvellement CACES grue pour equipe chantier', 'action', 'systeme', 'moyenne', 'en_attente', 'Systeme', 'Gerant Principal', '2026-05-15T18:00:00Z', '', '2026-04-17T10:00:00Z'),
    ('CH-014', 'Corriger position prise salle de bain selon plan electrique', 'A faire avant prochaine reception client', 'action', 'direction', 'haute', 'en_cours', 'Gerant Principal', 'Mohsan MAHMOOD', '2026-04-12T18:00:00Z', '', '2026-04-10T16:30:00Z'),
    ('CH-014', 'Refaire joints sanitaires salle de bain', 'Attente arrivee produit joint', 'action', 'direction', 'moyenne', 'en_attente', 'Gerant Principal', 'Mohsan MAHMOOD', '2026-04-13T18:00:00Z', '', '2026-04-10T16:35:00Z'),
    ('CH-014', 'Organiser reparation toiture', 'Coordination avec couvreur pour reparation infiltration', 'action', 'direction', 'haute', 'en_cours', 'Gerant Principal', 'Mohsan MAHMOOD', '2026-04-22T18:00:00Z', '', '2026-04-15T13:30:00Z')
) AS t(ref_chantier, titre, descr, tp, src, prio, st, cr_nom, as_nom, ech, rep, cr_at)
LEFT JOIN chantiers c ON (t.ref_chantier IS NOT NULL AND c.ref = t.ref_chantier AND c.org_id = (SELECT _org_id FROM _cfg));

SELECT 'taches OK' AS result;
