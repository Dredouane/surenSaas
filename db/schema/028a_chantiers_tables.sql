-- 028a_chantiers_tables.sql
-- Tables, enums, indexes only (no functions, no triggers)

-- ============================================
-- ENUMS
-- ============================================
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_statut') THEN CREATE TYPE chantier_statut AS ENUM ('en_cours', 'termine', 'en_attente', 'cloture'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_operation_type') THEN CREATE TYPE chantier_operation_type AS ENUM ('demolition', 'nettoyage', 'pose_bso', 'commande', 'achat_materiel', 'sous_traitance', 'autre'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_operation_source') THEN CREATE TYPE chantier_operation_source AS ENUM ('telegram_voice', 'telegram_photo', 'telegram_text', 'telegram_pdf', 'manuel', 'email'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_operation_statut') THEN CREATE TYPE chantier_operation_statut AS ENUM ('en_attente', 'valide', 'rejete'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_depense_categorie') THEN CREATE TYPE chantier_depense_categorie AS ENUM ('sous_traitant', 'fournisseur', 'autre'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_reception_statut') THEN CREATE TYPE chantier_reception_statut AS ENUM ('planifiee', 'en_cours', 'terminee', 'annulee'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_reception_type') THEN CREATE TYPE chantier_reception_type AS ENUM ('livraison', 'validation', 'probleme', 'suivi'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_tache_statut') THEN CREATE TYPE chantier_tache_statut AS ENUM ('en_attente', 'en_cours', 'terminee', 'annulee'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_tache_type') THEN CREATE TYPE chantier_tache_type AS ENUM ('information', 'action', 'validation', 'rapport'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_tache_source') THEN CREATE TYPE chantier_tache_source AS ENUM ('direction', 'systeme', 'client'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_tache_priorite') THEN CREATE TYPE chantier_tache_priorite AS ENUM ('basse', 'moyenne', 'haute'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_ressource_type') THEN CREATE TYPE chantier_ressource_type AS ENUM ('homme', 'machine'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_pointage_periode') THEN CREATE TYPE chantier_pointage_periode AS ENUM ('matin', 'apres_midi', 'journee'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_notification_type') THEN CREATE TYPE chantier_notification_type AS ENUM ('tache', 'reception', 'pointage', 'validation', 'alerte', 'info', 'urgence'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_notification_statut') THEN CREATE TYPE chantier_notification_statut AS ENUM ('envoyee', 'lue', 'validee', 'refusee', 'en_attente'); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chantier_audit_action') THEN CREATE TYPE chantier_audit_action AS ENUM ('creation', 'modification', 'validation', 'rejet', 'suppression'); END IF; END $$;

-- ============================================
-- TABLES
-- ============================================
CREATE TABLE IF NOT EXISTS chantiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    dossier_id UUID REFERENCES dossiers(id) ON DELETE SET NULL,
    ref TEXT NOT NULL, nom TEXT NOT NULL, adresse TEXT NOT NULL DEFAULT '', conducteur TEXT NOT NULL DEFAULT '', commentaires TEXT DEFAULT '',
    montant_base DECIMAL(15,2) DEFAULT 0, ts_avenants DECIMAL(15,2) DEFAULT 0, montant_revise DECIMAL(15,2) DEFAULT 0,
    situations_facturees DECIMAL(15,2) DEFAULT 0, pourcentage_facture DECIMAL(5,2) DEFAULT 0,
    total_depenses DECIMAL(15,2) DEFAULT 0, marge_brute DECIMAL(15,2) DEFAULT 0, solde_a_facturer DECIMAL(15,2) DEFAULT 0,
    statut chantier_statut DEFAULT 'en_cours', priorite INTEGER DEFAULT 0 CHECK (priorite >= 0 AND priorite <= 3),
    date_opr_prevue DATE, date_opr_realisee DATE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, ref)
);

CREATE TABLE IF NOT EXISTS chantier_situations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    date DATE NOT NULL, numero INTEGER NOT NULL, libelle TEXT NOT NULL, montant DECIMAL(15,2) NOT NULL DEFAULT 0, reglement_observation TEXT DEFAULT '',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chantier_id, numero)
);

CREATE TABLE IF NOT EXISTS chantier_depenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    date DATE NOT NULL, fournisseur TEXT NOT NULL, categorie chantier_depense_categorie NOT NULL DEFAULT 'autre',
    description TEXT DEFAULT '', montant DECIMAL(15,2) NOT NULL DEFAULT 0, facture_ref TEXT DEFAULT '',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chantier_operations_htl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    description TEXT NOT NULL, type chantier_operation_type NOT NULL DEFAULT 'autre',
    date TIMESTAMP NOT NULL DEFAULT NOW(), source chantier_operation_source NOT NULL DEFAULT 'manuel',
    source_details TEXT DEFAULT '', statut chantier_operation_statut DEFAULT 'en_attente',
    valide_par UUID REFERENCES users(id) ON DELETE SET NULL, valide_le TIMESTAMP, commentaire TEXT DEFAULT '',
    montant DECIMAL(15,2), unite TEXT DEFAULT '', quantite DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chantier_receptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    date TIMESTAMP NOT NULL, type chantier_reception_type NOT NULL, statut chantier_reception_statut DEFAULT 'planifiee',
    participants TEXT[] DEFAULT '{}', ordre_du_jour TEXT DEFAULT '', decisions TEXT DEFAULT '', points_a_regler TEXT DEFAULT '', documents TEXT[] DEFAULT '{}',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chantier_taches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    reception_id UUID REFERENCES chantier_receptions(id) ON DELETE SET NULL,
    titre TEXT NOT NULL, description TEXT DEFAULT '',
    type chantier_tache_type NOT NULL DEFAULT 'action', source chantier_tache_source NOT NULL DEFAULT 'direction',
    priorite chantier_tache_priorite DEFAULT 'moyenne', statut chantier_tache_statut DEFAULT 'en_attente',
    createur_id UUID REFERENCES users(id) ON DELETE SET NULL, createur_nom TEXT DEFAULT '',
    assignee_id UUID REFERENCES users(id) ON DELETE SET NULL, assignee_nom TEXT DEFAULT '',
    echeance TIMESTAMP, reponse TEXT DEFAULT '', documents TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chantier_ressources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chantier_id UUID REFERENCES chantiers(id) ON DELETE SET NULL,
    nom TEXT NOT NULL, type chantier_ressource_type NOT NULL, specialite TEXT DEFAULT '',
    disponible BOOLEAN DEFAULT TRUE, indisponible_jusquau DATE, raison_indisponibilite TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chantier_pointages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    conducteur_id UUID REFERENCES users(id) ON DELETE SET NULL,
    date DATE NOT NULL, commentaires TEXT DEFAULT '',
    valide_par UUID REFERENCES users(id) ON DELETE SET NULL, valide_le TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chantier_id, date)
);

CREATE TABLE IF NOT EXISTS chantier_pointage_ressources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pointage_id UUID NOT NULL REFERENCES chantier_pointages(id) ON DELETE CASCADE,
    ressource_id UUID NOT NULL REFERENCES chantier_ressources(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    periode chantier_pointage_periode NOT NULL DEFAULT 'journee',
    heures_prevues DECIMAL(5,2), presence BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(pointage_id, ressource_id, periode)
);

CREATE TABLE IF NOT EXISTS chantier_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type chantier_notification_type NOT NULL DEFAULT 'info',
    titre TEXT NOT NULL, message TEXT DEFAULT '', url TEXT DEFAULT '',
    statut chantier_notification_statut DEFAULT 'envoyee', telegram_message_id TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chantier_audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chantier_id UUID NOT NULL REFERENCES chantiers(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL, entity_id UUID, action chantier_audit_action NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, user_name TEXT DEFAULT '', details TEXT DEFAULT '',
    changes JSONB DEFAULT '{}', created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_chantiers_org ON chantiers(org_id);
CREATE INDEX IF NOT EXISTS idx_chantiers_statut ON chantiers(statut);
CREATE INDEX IF NOT EXISTS idx_chantiers_conducteur ON chantiers(conducteur);
CREATE INDEX IF NOT EXISTS idx_chantiers_priorite ON chantiers(priorite);
CREATE INDEX IF NOT EXISTS idx_chantiers_updated ON chantiers(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chantier_situations_chantier ON chantier_situations(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_situations_org ON chantier_situations(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_situations_date ON chantier_situations(date DESC);
CREATE INDEX IF NOT EXISTS idx_chantier_depenses_chantier ON chantier_depenses(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_depenses_org ON chantier_depenses(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_depenses_categorie ON chantier_depenses(categorie);
CREATE INDEX IF NOT EXISTS idx_chantier_depenses_date ON chantier_depenses(date DESC);
CREATE INDEX IF NOT EXISTS idx_chantier_operations_chantier ON chantier_operations_htl(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_operations_org ON chantier_operations_htl(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_operations_statut ON chantier_operations_htl(statut);
CREATE INDEX IF NOT EXISTS idx_chantier_operations_date ON chantier_operations_htl(date DESC);
CREATE INDEX IF NOT EXISTS idx_chantier_receptions_chantier ON chantier_receptions(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_receptions_org ON chantier_receptions(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_receptions_statut ON chantier_receptions(statut);
CREATE INDEX IF NOT EXISTS idx_chantier_taches_chantier ON chantier_taches(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_taches_org ON chantier_taches(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_taches_assignee ON chantier_taches(assignee_id);
CREATE INDEX IF NOT EXISTS idx_chantier_taches_statut ON chantier_taches(statut);
CREATE INDEX IF NOT EXISTS idx_chantier_taches_echeance ON chantier_taches(echeance);
CREATE INDEX IF NOT EXISTS idx_chantier_ressources_org ON chantier_ressources(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_ressources_chantier ON chantier_ressources(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_ressources_type ON chantier_ressources(type);
CREATE INDEX IF NOT EXISTS idx_chantier_ressources_disponible ON chantier_ressources(disponible);
CREATE INDEX IF NOT EXISTS idx_chantier_pointages_chantier ON chantier_pointages(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_pointages_org ON chantier_pointages(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_pointages_date ON chantier_pointages(date DESC);
CREATE INDEX IF NOT EXISTS idx_chantier_pointage_ressources_pointage ON chantier_pointage_ressources(pointage_id);
CREATE INDEX IF NOT EXISTS idx_chantier_pointage_ressources_ressource ON chantier_pointage_ressources(ressource_id);
CREATE INDEX IF NOT EXISTS idx_chantier_pointage_ressources_org ON chantier_pointage_ressources(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_notifications_chantier ON chantier_notifications(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_notifications_org ON chantier_notifications(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_notifications_user ON chantier_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_chantier_notifications_statut ON chantier_notifications(statut);
CREATE INDEX IF NOT EXISTS idx_chantier_notifications_created ON chantier_notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chantier_audit_chantier ON chantier_audit_trail(chantier_id);
CREATE INDEX IF NOT EXISTS idx_chantier_audit_org ON chantier_audit_trail(org_id);
CREATE INDEX IF NOT EXISTS idx_chantier_audit_entity ON chantier_audit_trail(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_chantier_audit_created ON chantier_audit_trail(created_at DESC);

-- ============================================
-- TRIGGER FUNCTION updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_chantier_updated_at() RETURNS TRIGGER LANGUAGE plpgsql AS $body$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $body$;

-- ============================================
-- TRIGGERS updated_at
-- ============================================
CREATE TRIGGER update_chantiers_updated_at BEFORE UPDATE ON chantiers FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
CREATE TRIGGER update_chantier_situations_updated_at BEFORE UPDATE ON chantier_situations FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
CREATE TRIGGER update_chantier_depenses_updated_at BEFORE UPDATE ON chantier_depenses FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
CREATE TRIGGER update_chantier_operations_updated_at BEFORE UPDATE ON chantier_operations_htl FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
CREATE TRIGGER update_chantier_receptions_updated_at BEFORE UPDATE ON chantier_receptions FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
CREATE TRIGGER update_chantier_taches_updated_at BEFORE UPDATE ON chantier_taches FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
CREATE TRIGGER update_chantier_ressources_updated_at BEFORE UPDATE ON chantier_ressources FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
CREATE TRIGGER update_chantier_pointages_updated_at BEFORE UPDATE ON chantier_pointages FOR EACH ROW EXECUTE FUNCTION update_chantier_updated_at();
