-- 027_ao_tables.sql
-- Module AO (Appels d'Offres) - Tables pour gestion des candidatures
-- Intégration avec le système de Dossiers existant
-- Support pgvector pour embeddings

-- ============================================
-- EXTENSION PGVECTOR (si pas déjà activée)
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- ENUMS
-- ============================================

-- Statut des candidatures
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ao_statut') THEN
        CREATE TYPE ao_statut AS ENUM (
            'en_cours',
            'gagne',
            'perdu',
            'abandonne'
        );
    END IF;
END
$$;

-- Types de documents AO
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ao_document_type') THEN
        CREATE TYPE ao_document_type AS ENUM (
            'RC',           -- Règlement de Consultation
            'CCTP',         -- Cahier des Clauses Techniques Particulières
            'BPU',          -- Bordereau des Prix Unitaires
            'DAO',          -- Dossier d'Appel d'Offres
            'MEMOIRE',      -- Mémoire Technique
            'DQE',          -- Devis Quantitatif Estimatif
            'GARANTIE',     -- Caution, garanties
            'REJET',        -- Rapport de rejet
            'ATTRIBUE',     -- Décision d'attribution
            'NEGociation',  -- CR de négociation
            'AUTRE'         -- Autre document
        );
    END IF;
END
$$;

-- Statut de traitement des documents
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ao_traitement_status') THEN
        CREATE TYPE ao_traitement_status AS ENUM (
            'pending',
            'processing',
            'processed',
            'error'
        );
    END IF;
END
$$;

-- Types de Lentilles d'analyse
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ao_lens_type') THEN
        CREATE TYPE ao_lens_type AS ENUM (
            'pricing',
            'redaction',
            'risque',
            'comparaison',
            'opportunite'
        );
    END IF;
END
$$;

-- Statut de validation humaine
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ao_validation_status') THEN
        CREATE TYPE ao_validation_status AS ENUM (
            'pending',
            'valide',
            'rejete',
            'partiel'
        );
    END IF;
END
$$;

-- ============================================
-- TABLE : ao_candidatures
-- Regroupe les candidatures pour un même projet AO
-- ============================================
CREATE TABLE IF NOT EXISTS ao_candidatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Liaisons
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    dossier_id UUID REFERENCES dossiers(id) ON DELETE SET NULL,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    
    -- Identification du projet
    nom_projet TEXT NOT NULL,
    client_nom TEXT,
    reference_ao TEXT,                    -- Référence de l'appel d'offres
    description TEXT,                     -- Description du projet
    
    -- Statut et dates
    statut ao_statut DEFAULT 'en_cours',
    date_depot DATE,                      -- Date de dépôt des plis
    date_ouverture DATE,                  -- Date d'ouverture des plis
    date_notification DATE,               -- Date de notification du résultat
    date_limite_remise DATE,              -- Date limite de remise des candidatures
    
    -- Données financières
    montant_total DECIMAL(15,2),          -- Montant total de notre candidature
    montant_maximum DECIMAL(15,2),        -- Montant maximum accepté (seuil)
    monnaie TEXT DEFAULT 'EUR',
    
    -- Métadonnées techniques
    duree_travaux_jours INTEGER,          -- Durée des travaux en jours
    date_debut_previsionnelle DATE,
    date_fin_previsionnelle DATE,
    
    -- IA - Analyses et résumés
    ai_summary TEXT,                      -- Résumé global du projet
    ai_keywords TEXT[],                   -- Mots-clés extraits
    ai_score_gagner FLOAT,                -- Probabilité estimée de gain (0-1)
    
    -- Compteurs (mis à jour par triggers)
    document_count INTEGER DEFAULT 0,
    poste_count INTEGER DEFAULT 0,
    
    -- Métadonnées
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Contraintes
    CONSTRAINT positive_montant CHECK (montant_total IS NULL OR montant_total >= 0)
);

-- Index pour ao_candidatures
CREATE INDEX IF NOT EXISTS idx_ao_candidatures_org ON ao_candidatures(org_id);
CREATE INDEX IF NOT EXISTS idx_ao_candidatures_dossier ON ao_candidatures(dossier_id);
CREATE INDEX IF NOT EXISTS idx_ao_candidatures_company ON ao_candidatures(company_id);
CREATE INDEX IF NOT EXISTS idx_ao_candidatures_statut ON ao_candidatures(statut);
CREATE INDEX IF NOT EXISTS idx_ao_candidatures_client ON ao_candidatures(client_nom);
CREATE INDEX IF NOT EXISTS idx_ao_candidatures_dates ON ao_candidatures(date_depot, date_limite_remise);
CREATE INDEX IF NOT EXISTS idx_ao_candidatures_created ON ao_candidatures(created_at DESC);

-- ============================================
-- TABLE : ao_documents
-- Documents associés à une candidature
-- ============================================
CREATE TABLE IF NOT EXISTS ao_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Liaisons
    candidature_id UUID NOT NULL REFERENCES ao_candidatures(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Type et identification
    type_doc ao_document_type NOT NULL,
    sous_type TEXT,                       -- Précision (ex: "BPU_Initial", "BPU_Modifie_1")
    nom_fichier TEXT NOT NULL,
    
    -- Stockage
    url_stockage TEXT,                    -- Chemin S3/local
    mime_type TEXT,
    taille_bytes BIGINT,
    checksum TEXT,                        -- SHA256 pour intégrité
    
    -- Contenu extrait
    contenu_texte TEXT,                   -- Texte brut extrait (OCR ou parsing)
    nombre_pages INTEGER,
    
    -- Métadonnées extraites par IA
    metadata JSONB DEFAULT '{}',          -- Métadonnées structurées
    -- Exemple: {"client_nom": "ACORUS", "projet_nom": "...", "date_document": "..."}
    
    -- Statut de traitement
    statut_traitement ao_traitement_status DEFAULT 'pending',
    message_erreur TEXT,                  -- En cas d'erreur de traitement
    
    -- Traitement IA
    date_extraction TIMESTAMP,            -- Date du parsing/extraction
    model_extraction TEXT,                -- Modèle utilisé (gemini-2.5-pro, etc.)
    
    -- Métadonnées
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour ao_documents
CREATE INDEX IF NOT EXISTS idx_ao_documents_candidature ON ao_documents(candidature_id);
CREATE INDEX IF NOT EXISTS idx_ao_documents_org ON ao_documents(org_id);
CREATE INDEX IF NOT EXISTS idx_ao_documents_type ON ao_documents(type_doc);
CREATE INDEX IF NOT EXISTS idx_ao_documents_traitement ON ao_documents(statut_traitement);
CREATE INDEX IF NOT EXISTS idx_ao_documents_metadata ON ao_documents USING GIN(metadata);

-- ============================================
-- TABLE : ao_embeddings (pgvector)
-- Stockage vectoriel pour RAG
-- ============================================
CREATE TABLE IF NOT EXISTS ao_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Liaisons
    doc_id UUID NOT NULL REFERENCES ao_documents(id) ON DELETE CASCADE,
    candidature_id UUID NOT NULL REFERENCES ao_candidatures(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Contenu
    content TEXT NOT NULL,                -- Chunk de texte
    embedding VECTOR(768),                -- Embedding Gemini (text-embedding-004)
    
    -- Métadonnées du chunk
    chunk_index INTEGER DEFAULT 0,        -- Index du chunk dans le document
    chunk_total INTEGER DEFAULT 1,        -- Nombre total de chunks
    tags TEXT[],                          -- Tags pour filtrage (pricing, technique, risque...)
    -- Exemple: ['pricing', 'poste_beton', 'gros_oeuvre']
    
    -- Source
    page_debut INTEGER,                   -- Page de début (si applicable)
    page_fin INTEGER,                     -- Page de fin
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index pour ao_embeddings
CREATE INDEX IF NOT EXISTS idx_ao_embeddings_doc ON ao_embeddings(doc_id);
CREATE INDEX IF NOT EXISTS idx_ao_embeddings_candidature ON ao_embeddings(candidature_id);
CREATE INDEX IF NOT EXISTS idx_ao_embeddings_org ON ao_embeddings(org_id);
CREATE INDEX IF NOT EXISTS idx_ao_embeddings_tags ON ao_embeddings USING GIN(tags);

-- Index HNSW pour recherche vectorielle rapide
CREATE INDEX IF NOT EXISTS idx_ao_embeddings_vector 
ON ao_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================
-- TABLE : ao_postes_pricing
-- Postes extraits des BPU pour analyse comparative
-- ============================================
CREATE TABLE IF NOT EXISTS ao_postes_pricing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Liaisons
    candidature_id UUID NOT NULL REFERENCES ao_candidatures(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES ao_documents(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Identification du poste
    numero TEXT NOT NULL,                 -- Numéro de poste (01.01.001)
    description TEXT NOT NULL,            -- Libellé du poste
    description_normalisee TEXT,          -- Version normalisée pour recherche
    
    -- Caractéristiques
    unite TEXT,                           -- m2, m3, ml, forfait, u, etc.
    quantite DECIMAL(15,4),
    prix_unitaire_ht DECIMAL(15,4),
    prix_total_ht DECIMAL(15,4),
    
    -- Catégorisation
    categorie TEXT,                       -- GROS_OEUVRE, SECOND_OEUVRE, EQUIPEMENT, etc.
    sous_categorie TEXT,
    
    -- Pour analyse comparative
    prix_unitaire_reference DECIMAL(15,4),-- Prix de référence historique
    ecart_reference_pct DECIMAL(5,2),     -- Écart en % par rapport à référence
    
    -- Métadonnées
    ligne_bpu INTEGER,                    -- Numéro de ligne dans le BPU source
    metadata JSONB DEFAULT '{}',          -- Données additionnelles
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour ao_postes_pricing
CREATE INDEX IF NOT EXISTS idx_ao_postes_candidature ON ao_postes_pricing(candidature_id);
CREATE INDEX IF NOT EXISTS idx_ao_postes_document ON ao_postes_pricing(document_id);
CREATE INDEX IF NOT EXISTS idx_ao_postes_org ON ao_postes_pricing(org_id);
CREATE INDEX IF NOT EXISTS idx_ao_postes_numero ON ao_postes_pricing(numero);
CREATE INDEX IF NOT EXISTS idx_ao_postes_categorie ON ao_postes_pricing(categorie);
CREATE INDEX IF NOT EXISTS idx_ao_postes_desc_search ON ao_postes_pricing USING GIN(to_tsvector('french', description));

-- ============================================
-- TABLE : ao_analyses
-- Résultats des analyses par Lentilles
-- ============================================
CREATE TABLE IF NOT EXISTS ao_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Liaisons
    candidature_id UUID NOT NULL REFERENCES ao_candidatures(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Type d'analyse
    lens_type ao_lens_type NOT NULL,
    prompt_version TEXT,                  -- Version du prompt système utilisé
    
    -- Contexte de l'analyse
    contexte JSONB DEFAULT '{}',          -- Paramètres/contexte de l'analyse
    documents_analyses UUID[],            -- IDs des documents analysés
    
    -- Résultat
    resultat JSONB NOT NULL,              -- Résultat structuré de l'analyse
    score_confiance FLOAT CHECK (score_confiance >= 0 AND score_confiance <= 1),
    
    -- Validation humaine
    validation_humain ao_validation_status DEFAULT 'pending',
    valide_par UUID REFERENCES users(id) ON DELETE SET NULL,
    date_validation TIMESTAMP,
    commentaire_validation TEXT,
    
    -- Coût et performance
    tokens_input INTEGER,
    tokens_output INTEGER,
    duree_ms INTEGER,                     -- Durée de l'analyse en ms
    model_utilise TEXT,                   -- Modèle IA utilisé
    
    -- Métadonnées
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour ao_analyses
CREATE INDEX IF NOT EXISTS idx_ao_analyses_candidature ON ao_analyses(candidature_id);
CREATE INDEX IF NOT EXISTS idx_ao_analyses_org ON ao_analyses(org_id);
CREATE INDEX IF NOT EXISTS idx_ao_analyses_lens ON ao_analyses(lens_type);
CREATE INDEX IF NOT EXISTS idx_ao_analyses_validation ON ao_analyses(validation_humain);
CREATE INDEX IF NOT EXISTS idx_ao_analyses_created ON ao_analyses(created_at DESC);

-- ============================================
-- FONCTIONS ET TRIGGERS
-- ============================================

-- Fonction: Mettre à jour les compteurs d'une candidature
CREATE OR REPLACE FUNCTION update_ao_counters(p_candidature_id UUID)
RETURNS VOID AS $$
DECLARE
    v_document_count INTEGER;
    v_poste_count INTEGER;
BEGIN
    -- Compter les documents
    SELECT COUNT(*) INTO v_document_count
    FROM ao_documents
    WHERE candidature_id = p_candidature_id;
    
    -- Compter les postes
    SELECT COUNT(*) INTO v_poste_count
    FROM ao_postes_pricing
    WHERE candidature_id = p_candidature_id;
    
    -- Mettre à jour la candidature
    UPDATE ao_candidatures
    SET document_count = v_document_count,
        poste_count = v_poste_count,
        updated_at = NOW()
    WHERE id = p_candidature_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Mise à jour auto des compteurs quand un document est ajouté/supprimé
CREATE OR REPLACE FUNCTION trigger_update_ao_counters()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.candidature_id IS NOT NULL THEN
            PERFORM update_ao_counters(OLD.candidature_id);
        END IF;
        RETURN OLD;
    ELSIF TG_OP = 'INSERT' THEN
        PERFORM update_ao_counters(NEW.candidature_id);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' AND OLD.candidature_id IS DISTINCT FROM NEW.candidature_id THEN
        IF OLD.candidature_id IS NOT NULL THEN
            PERFORM update_ao_counters(OLD.candidature_id);
        END IF;
        PERFORM update_ao_counters(NEW.candidature_id);
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_ao_documents_counter ON ao_documents;
CREATE TRIGGER trigger_ao_documents_counter
    AFTER INSERT OR UPDATE OF candidature_id OR DELETE ON ao_documents
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_ao_counters();

-- Trigger pour postes_pricing
DROP TRIGGER IF EXISTS trigger_ao_postes_counter ON ao_postes_pricing;
CREATE TRIGGER trigger_ao_postes_counter
    AFTER INSERT OR UPDATE OF candidature_id OR DELETE ON ao_postes_pricing
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_ao_counters();

-- Fonction: Mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers updated_at
DROP TRIGGER IF EXISTS update_ao_candidatures_updated_at ON ao_candidatures;
CREATE TRIGGER update_ao_candidatures_updated_at
    BEFORE UPDATE ON ao_candidatures
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ao_documents_updated_at ON ao_documents;
CREATE TRIGGER update_ao_documents_updated_at
    BEFORE UPDATE ON ao_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ao_postes_pricing_updated_at ON ao_postes_pricing;
CREATE TRIGGER update_ao_postes_pricing_updated_at
    BEFORE UPDATE ON ao_postes_pricing
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ao_analyses_updated_at ON ao_analyses;
CREATE TRIGGER update_ao_analyses_updated_at
    BEFORE UPDATE ON ao_analyses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- FONCTIONS UTILITAIRES RAG
-- ============================================

-- Fonction: Recherche vectorielle de similarité
CREATE OR REPLACE FUNCTION search_ao_embeddings(
    p_org_id UUID,
    p_query_embedding VECTOR(768),
    p_limit INTEGER DEFAULT 5,
    p_tags TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    doc_id UUID,
    candidature_id UUID,
    content TEXT,
    similarity FLOAT,
    tags TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.doc_id,
        e.candidature_id,
        e.content,
        1 - (e.embedding <=> p_query_embedding) AS similarity,
        e.tags
    FROM ao_embeddings e
    WHERE e.org_id = p_org_id
      AND (p_tags IS NULL OR e.tags && p_tags)
    ORDER BY e.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Fonction: Trouver les postes similaires (recherche textuelle)
CREATE OR REPLACE FUNCTION search_ao_postes(
    p_org_id UUID,
    p_search_query TEXT,
    p_categorie TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    candidature_id UUID,
    numero TEXT,
    description TEXT,
    unite TEXT,
    prix_unitaire_ht DECIMAL,
    rank FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.candidature_id,
        p.numero,
        p.description,
        p.unite,
        p.prix_unitaire_ht,
        ts_rank(to_tsvector('french', p.description), plainto_tsquery('french', p_search_query)) AS rank
    FROM ao_postes_pricing p
    JOIN ao_candidatures c ON p.candidature_id = c.id
    WHERE c.org_id = p_org_id
      AND (p_categorie IS NULL OR p.categorie = p_categorie)
      AND to_tsvector('french', p.description) @@ plainto_tsquery('french', p_search_query)
    ORDER BY rank DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Fonction: Statistiques de pricing pour une candidature
CREATE OR REPLACE FUNCTION get_ao_pricing_stats(p_candidature_id UUID)
RETURNS TABLE (
    categorie TEXT,
    nombre_postes BIGINT,
    montant_total_ht DECIMAL,
    prix_moyen DECIMAL,
    prix_min DECIMAL,
    prix_max DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.categorie,
        COUNT(*) AS nombre_postes,
        SUM(p.prix_total_ht) AS montant_total_ht,
        AVG(p.prix_unitaire_ht) AS prix_moyen,
        MIN(p.prix_unitaire_ht) AS prix_min,
        MAX(p.prix_unitaire_ht) AS prix_max
    FROM ao_postes_pricing p
    WHERE p.candidature_id = p_candidature_id
    GROUP BY p.categorie
    ORDER BY montant_total_ht DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VUES POUR ANALYSE
-- ============================================

-- Vue: Résumé des candidatures avec métriques
CREATE OR REPLACE VIEW ao_candidatures_summary AS
SELECT 
    c.*,
    d.name AS dossier_name,
    d.client_name AS dossier_client,
    COUNT(DISTINCT doc.id) AS nb_documents,
    COUNT(DISTINCT p.id) AS nb_postes,
    COALESCE(SUM(p.prix_total_ht), 0) AS total_postes_ht
FROM ao_candidatures c
LEFT JOIN dossiers d ON c.dossier_id = d.id
LEFT JOIN ao_documents doc ON c.id = doc.candidature_id AND doc.statut_traitement = 'processed'
LEFT JOIN ao_postes_pricing p ON c.id = p.candidature_id
GROUP BY c.id, d.name, d.client_name;

-- Vue: Historique des prix par catégorie (pour comparaison)
CREATE OR REPLACE VIEW ao_pricing_history AS
SELECT 
    p.categorie,
    p.description_normalisee,
    p.unite,
    c.statut,
    AVG(p.prix_unitaire_ht) AS prix_moyen,
    COUNT(*) AS occurrences,
    MIN(p.prix_unitaire_ht) AS prix_min,
    MAX(p.prix_unitaire_ht) AS prix_max
FROM ao_postes_pricing p
JOIN ao_candidatures c ON p.candidature_id = c.id
WHERE c.statut IN ('gagne', 'perdu')
GROUP BY p.categorie, p.description_normalisee, p.unite, c.statut;

-- ============================================
-- COMMENTAIRES DE DOCUMENTATION
-- ============================================

COMMENT ON TABLE ao_candidatures IS 'Candidatures aux appels d''offres BTP';
COMMENT ON TABLE ao_documents IS 'Documents associés aux candidatures (RC, BPU, etc.)';
COMMENT ON TABLE ao_embeddings IS 'Embeddings vectoriels pour RAG (pgvector)';
COMMENT ON TABLE ao_postes_pricing IS 'Postes extraits des BPU pour analyse comparative';
COMMENT ON TABLE ao_analyses IS 'Résultats des analyses par Lentilles IA';

COMMENT ON COLUMN ao_candidatures.ai_score_gagner IS 'Probabilité estimée de gagner l''AO (0-1)';
COMMENT ON COLUMN ao_postes_pricing.prix_unitaire_reference IS 'Prix historique de référence pour comparaison';
COMMENT ON COLUMN ao_analyses.resultat IS 'Résultat structuré JSON de l''analyse IA';
