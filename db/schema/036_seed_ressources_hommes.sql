-- 036_seed_ressources_hommes.sql
-- Alimente chantier_ressources avec les ressources humaines de l'org
-- org_id = REDACTEDORG (REDACTED_ORG_SLUG)

DO $$
DECLARE
    v_org_id UUID := 'REDACTEDORG';
    v_chantier_id UUID := 'd02e9843-a3a5-46f3-a2d2-5a9bc9c31fb5';
    v_count INTEGER := 0;
BEGIN

-- Supprimer les anciennes ressources pour éviter les doublons
DELETE FROM chantier_ressources WHERE org_id = v_org_id AND type = 'homme';

INSERT INTO chantier_ressources (org_id, chantier_id, nom, type, specialite) VALUES
(v_org_id, v_chantier_id, 'ABERBOUR Idris',       'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'BELIZAIRE Jilbert',     'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'BEN HASSINE Walid',     'homme', 'Manœuvre'),
(v_org_id, v_chantier_id, 'BEN JEMAA Adnane',      'homme', 'Manœuvre'),
(v_org_id, v_chantier_id, 'BENKADI Samir',         'homme', 'Ravaleur peintre'),
(v_org_id, v_chantier_id, 'BOUAZIZ Med Ali',       'homme', 'Façadier'),
(v_org_id, v_chantier_id, 'BOUAZIZ Rabie',         'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'BOUBADJA Faras',        'homme', 'Ravaleur peintre'),
(v_org_id, v_chantier_id, 'BOUBADJA Mouad',        'homme', 'Manœuvre'),
(v_org_id, v_chantier_id, 'DARIA Nabil',           'homme', 'Plombier'),
(v_org_id, v_chantier_id, 'DRIDI Mohsen',          'homme', 'Manœuvre'),
(v_org_id, v_chantier_id, 'EL AROUCH JAZOULI Ahmed', 'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'ESSID Youssef',          'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'GUIRAT Mohamed',         'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'IDJEGA Chafir',          'homme', 'Ouvrier polyvalent'),
(v_org_id, v_chantier_id, 'JACQUET Jean Enol',      'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'JEAN LOUIS Marcelio',    'homme', 'Ouvrier polyvalent'),
(v_org_id, v_chantier_id, 'JEAN PIERRE Robert',     'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'KEFSI Elhosseyn',        'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'KEFSI Fatih',            'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'LAYOUNI Aymen',          'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'LIBDRI Djamel',          'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'LYMAT RESSOIR',          'homme', 'Ravaleur peintre'),
(v_org_id, v_chantier_id, 'LYVRET Vincent',         'homme', 'Ravaleur peintre'),
(v_org_id, v_chantier_id, 'MANSEUR Ahmed',          'homme', 'Ouvrier polyvalent'),
(v_org_id, v_chantier_id, 'MEDDOUR Assad',          'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'OUSADI Nabil',           'homme', 'Façadier'),
(v_org_id, v_chantier_id, 'PIERRE Dady',            'homme', 'Ravaleur peintre'),
(v_org_id, v_chantier_id, 'POMPE Obede',            'homme', 'Ouvrier polyvalent'),
(v_org_id, v_chantier_id, 'TENKHI Loucif',          'homme', 'Ravaleur façadier'),
(v_org_id, v_chantier_id, 'ZAKARYAN Vardan',        'homme', 'Manœuvre'),
(v_org_id, v_chantier_id, 'ZAOUGA Abdennaceur',     'homme', 'Ravaleur peintre');

GET DIAGNOSTICS v_count = ROW_COUNT;
RAISE NOTICE '✅ % ressources hommes insérées', v_count;

END $$;
