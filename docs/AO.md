# Module AO (Appels d'Offres) - Spécifications Techniques

## Vue d'ensemble

Le module AO permet de gérer les appels d'offres et candidatures pour les projets de construction. Il intègre l'IA pour l'analyse des documents (RC, BPU, CCTP), la comparaison de pricing, et la rédaction assistée du mémoire technique.

**Intégration existante** : Les AO sont liés au système de Dossiers existant (`dossiers` table).

---

## 1. Définition des Typologies de Documents

### Documents Source (Créés par le client)
| Type | Code | Description |
|------|------|-------------|
| Règlement de Consultation | `RC` | Document définissant les modalités de l'appel d'offres |
| Cahier des Clauses Techniques Particulières | `CCTP` | Spécifications techniques du projet |
| Bordereau des Prix Unitaires | `BPU` | Liste des postes avec quantités et prix |
| Dossier d'Appel d'Offres | `DAO` | Ensemble complet de consultation |

### Documents Réponse (Créés par l'entreprise)
| Type | Code | Description |
|------|------|-------------|
| Mémoire Technique | `MEMOIRE` | Document de réponse technique |
| DQE / BPU Réponse | `DQE` | Devis quantitatif estimatif répondu |
| Garantie | `GARANTIE` | Caution, garanties, assurances |

### Documents Feedback (Post-candidature)
| Type | Code | Description |
|------|------|-------------|
| Rapport de Rejet | `REJET` | Motifs de non-attribution |
| Attribué | `ATTRIBUE` | Décision d'attribution |
| CR Négociation | `NEGociation` | Compte-rendu de négociation |

---

## 2. Flux de Données

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FLUX DE DONNÉES AO                              │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   INGESTION  │────▶│ PARSING & META-  │────▶│   VECTORISATION      │
│   BRUTE      │     │    TAGGING       │     │   (pgvector)         │
└──────────────┘     └──────────────────┘     └──────────────────────┘
       │                     │                          │
       ▼                     ▼                          ▼
 Dossier de fichiers    Gemini Flash             Embeddings
 PDF, CSV, DOCX         Classification           + Métadonnées
                       + Extraction              + Tags

                              │
                              ▼
                    ┌──────────────────┐
                    │  ANALYSE PAR     │
                    │   "LENTILLE"     │
                    └──────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │  PRICING   │    │ RÉDACTION  │    │   RISQUE   │
    │  Compare   │    │  Mémoire   │    │   Score    │
    │  historique│    │  technique │    │   analyse  │
    └────────────┘    └────────────┘    └────────────┘
```

---

## 3. Nomenclature des Métadonnées

### Métadonnées Pricing (BPU)
```json
{
  "postes": [
    {
      "numero": "01.01.001",
      "description": "Béton armé - Fondations",
      "unite": "m3",
      "quantite": 150.5,
      "prix_unitaire_ht": 850.00,
      "prix_total_ht": 127925.00,
      "categorie": "GROS_OEUVRE"
    }
  ],
  "montant_total_ht": 1250000.00,
  "monnaie": "EUR",
  "taux_tva": 0.20
}
```

### Métadonnées Techniques (RC/CCTP)
```json
{
  "critere_score": {
    "experience": 30,
    "methodologie": 40,
    "prix": 30
  },
  "argument_cles": [
    "Expérience similaire",
    "Moyens humains dédiés",
    "Délai respecté"
  ],
  "exigences_marque": ["NF", "CE", "ISO 9001"],
  "delai_execution": 180,
  "date_limite": "2024-06-15"
}
```

### Métadonnées Document (Générique)
```json
{
  "type_doc": "RC",
  "confidence": 0.97,
  "pages": 12,
  "date_document": "2024-01-15",
  "client_nom": "ACORUS",
  "projet_nom": "Résidence Les Lilas"
}
```

---

## 4. Structure des Tables

### 4.1 ao_candidatures
Regroupe toutes les candidatures pour un même projet AO.

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `dossier_id` | UUID | FK vers `dossiers` |
| `org_id` | UUID | FK vers `organizations` |
| `nom_projet` | TEXT | Nom du projet |
| `client_nom` | TEXT | Nom du maître d'ouvrage |
| `reference_ao` | TEXT | Référence de l'appel d'offres |
| `statut` | ENUM | `en_cours` / `gagne` / `perdu` / `abandonne` |
| `montant_total` | DECIMAL | Montant total de notre candidature |
| `date_depot` | DATE | Date de dépôt des plis |
| `date_ouverture` | DATE | Date d'ouverture des plis |
| `date_notification` | DATE | Date de notification du résultat |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

### 4.2 ao_documents
Documents associés à une candidature.

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `candidature_id` | UUID | FK |
| `type_doc` | ENUM | `RC` / `CCTP` / `BPU` / `MEMOIRE` / `DQE` / `REJET` / `ATTRIBUE` |
| `sous_type` | TEXT | Précision (ex: "BPU_Initial", "BPU_Modifie") |
| `url_stockage` | TEXT | Chemin S3/Stockage |
| `metadata` | JSONB | Métadonnées extraites |
| `statut_traitement` | ENUM | `pending` / `processed` / `error` |
| `date_extraction` | TIMESTAMP | Date du parsing IA |
| `created_at` | TIMESTAMP | |

### 4.3 ao_embeddings (pgvector)
Stockage vectoriel pour RAG.

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `doc_id` | UUID | FK vers `ao_documents` |
| `content` | TEXT | Contenu textuel chunk |
| `embedding` | VECTOR(768) | Embedding Gemini |
| `tags` | TEXT[] | Tags pour filtrage (pricing, technique, etc.) |
| `chunk_index` | INTEGER | Index du chunk dans le doc |
| `created_at` | TIMESTAMP | |

### 4.4 ao_postes_pricing
Postes extraits des BPU pour analyse comparative.

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `candidature_id` | UUID | FK |
| `document_id` | UUID | FK vers BPU source |
| `numero` | TEXT | Numéro de poste (01.01.001) |
| `description` | TEXT | Libellé du poste |
| `unite` | TEXT | m2, m3, forfait, etc. |
| `quantite` | DECIMAL | Quantité |
| `prix_unitaire_ht` | DECIMAL | Prix unitaire |
| `prix_total_ht` | DECIMAL | Total HT |
| `categorie` | TEXT | GROS_OEUVRE, SECOND_OEUVRE, etc. |

### 4.5 ao_analyses
Résultats des analyses par Lentilles.

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `candidature_id` | UUID | FK |
| `lens_type` | ENUM | `pricing` / `redaction` / `risque` / `comparaison` |
| `prompt_version` | TEXT | Version du prompt utilisé |
| `resultat` | JSONB | Résultat structuré de l'analyse |
| `score_confiance` | FLOAT | Confiance IA (0-1) |
| `validation_humain` | ENUM | `pending` / `valide` / `rejete` |
| `created_at` | TIMESTAMP | |

---

## 5. Architecture Services

### 5.1 ao_service.py
Fonctions principales :
- `ingest_ao_folder(folder_path: str, candidature_id: UUID)` → Parse et injecte tous les fichiers d'un dossier
- `classify_document(file_content: bytes, filename: str)` → Détecte le type (RC, BPU, etc.) via Gemini Flash
- `extract_pricing_data(document_id: UUID)` → Extrait les postes du BPU
- `link_to_dossier(candidature_id: UUID, dossier_id: UUID)` → Lie à un dossier existant

### 5.2 ao_lens_engine.py
Système de prompts interchangeables :
- `analyze_with_lens(lens_type: str, candidature_id: UUID, context: dict)` → Route vers la bonne lentille
- `_lens_pricing()` → Analyse comparative de pricing
- `_lens_redaction()` → Génération mémoire technique
- `_lens_risque()` → Scoring des risques

### 5.3 ao_rag_service.py
Recherche et contexte RAG (Retrieval Augmented Generation) :
- `get_pricing_context(poste_description: str, limit: int = 5)` → Postes similaires historiques
- `find_similar_successful_ao(candidature_id: UUID, limit: int = 3)` → AO gagnés similaires
- `get_memoire_template(chapitre: str)` → Extraits de mémoires gagnants
- **Intégration avec Lentilles** : Utilisé par `ao_lens_engine` pour enrichir les analyses
- **Pricing** : Recherche de postes similaires gagnés pour comparaison
- **Rédaction** : Extraction de templates de mémoires gagnants

### 5.4 Traitement des Documents (OCR + Vectorisation + Stockage S3)

Le module AO réutilise les services existants pour le traitement des documents :

**Stockage - FileStorageService** (`app/services/file_storage_service.py`)
- Utilise Cloudflare R2 (S3-compatible) pour le stockage persistant
- Structure: `{environment}/org/{org_id}/ao/{timestamp}_{filename}`
- Sécurité: Accès contrôlé par organisation via préfixe
- Méthode : `store_file()` dans `ao_service.py`

**OCR - GenericDocumentExtractor** (`app/agents/generic_extractor.py`)
- Utilise Gemini Flash pour extraire le texte des PDF, images
- Fonctionne comme pour les pièces jointes emails
- Méthode : `extract_document_text()` dans `ao_service.py`

**Vectorisation - EmbeddingService** (`app/services/emails/embedding_service.py`)
- Réutilise le service d'embedding des emails
- Génère des embeddings 768 dimensions via Vertex AI
- Chunking configurable (défaut: 500 caractères, overlap 50)
- Méthode : `vectorize_document()` dans `ao_service.py`

**Pipeline complet :**
```
Upload fichier → Stockage S3/R2 → OCR (Gemini) → 
contenu_texte → Chunking → Embeddings → ao_embeddings
```

### 5.5 Création Automatique depuis Dossier ZIP

**Upload de dossier complet avec analyse automatique :**

Méthodes dans `ao_service.py`:
- `upload_and_create_from_zip(zip_data, filename)` → Décompresse, analyse et crée candidature
- `analyze_and_create_from_folder(folder_path)` → Analyse dossier décompressé
- `_analyze_folder_metadata()` → Extrait métadonnées clés (client, projet, montant, dates)

**Workflow automatique :**
```
Upload ZIP → Décompression → Analyse métadonnées (RC/BPU) →
Création candidature → Upload documents → OCR → Vectorisation →
Extraction postes pricing (BPU)
```

**Métadonnées extraites automatiquement :**
- Nom du projet (depuis RC/DAO)
- Client / Maître d'ouvrage
- Référence de l'AO
- Dates limites
- Montant total (depuis BPU)
- Durée des travaux

**Endpoints API :**
- `POST /ao/upload-folder` → Upload ZIP + création auto
- `POST /ao/candidatures/from-folder` → Création depuis dossier existant

**Frontend :**
- Page `/dashboard/ao/import` avec composant `FolderUploader`
- Drag & drop de ZIP
- Analyse en temps réel avec progression
- Affichage des métadonnées extraites avant confirmation

**Endpoints API Upload :**
- `POST /candidatures/{id}/documents/upload` - Upload fichier individuel avec OCR/vectorisation auto
- `POST /documents/{id}/process` - Re-traiter un document existant
- `POST /documents/{id}/ocr` - Lancer OCR uniquement
- `POST /documents/{id}/vectorize` - Vectoriser uniquement

**Endpoints API Dossier ZIP :**
- `POST /ao/upload-folder` - Upload ZIP + création auto candidature + analyse
- `POST /ao/candidatures/from-folder` - Création depuis dossier déjà sur serveur

**Endpoints API Consultation :**
- `GET /ao/documents/{id}/download` - Téléchargement direct vers S3 (redirection URL signée)
- `GET /ao/documents/{id}/preview` - Métadonnées + URL pour prévisualisation
- Sécurité: Vérification du préfixe `{environment}/org/{org_id}/` dans storage_key

**Frontend :**
- Composant `DocumentUploader` - Upload individuel avec drag & drop
- Composant `FolderUploader` - Upload ZIP avec création auto
- Composant `AOExplorer` - Visualisation + téléchargement des documents
- Page `/dashboard/ao/import` - Interface complète d'import de dossier
- Bouton "Importer dossier" - Dans la liste des AO
- Visualisation progression temps réel (Upload → Analyse → OCR → Vectorisation)

---

## 6. Sécurité et Accès aux Fichiers

### 6.1 Stockage S3/R2
- **Structure**: `{environment}/org/{org_id}/ao/{timestamp}_{filename}`
- **Isolation**: Chaque organisation a son propre préfixe
- **URLs signées**: Génération d'URLs temporaires pour téléchargement (1-2h)
- **Validation**: Vérification que le `storage_key` commence par le préfixe attendu

### 6.2 Contrôle d'Accès
- **Niveau API**: Vérification de l'appartenance à l'organisation
- **Niveau stockage**: Isolation par préfixe S3
- **Frontend**: Accès contrôlé par les permissions d'écran
- **Audit**: Logs de tous les téléchargements et accès

### 6.3 Migration depuis stockage local
- **Ancien**: `/tmp/ao/{org_id}/{candidature_id}/{filename}` (non persistant)
- **Nouveau**: Cloudflare R2 (S3-compatible) avec persistance complète
- **Compatibilité**: Les nouveaux uploads utilisent S3, fichiers existants à migrer

### 6.4 Fallback pour développement
- **S3 échoue** → **Stockage local** automatique
- **Configuration**: Variables d'environnement R2 requises pour S3
- **Dépendances**: `boto3` package nécessaire pour S3
- **Logs**: Messages d'avertissement en cas de fallback
- **Téléchargement**: Endpoints API gèrent les deux types de stockage

---

## 7. Les "Lentilles" (Prompts Systèmes)

### Lentille Pricing
**Modèle** : Gemini 2.5 Pro
**Usage** : Analyse approfondie du BPU

```
Tu es un expert en chiffrage BTP. Analyse ce BPU candidature et compare-le 
à notre historique de victoires.

CONTEXTE:
- BPU candidature: [JSON des postes]
- Historique gagnant: [Postes similaires extraits via RAG]

TÂCHES:
1. Identifie les postes où nous sommes >20% plus chers que notre moyenne historique
2. Détecte les postes mal dimensionnés (quantité suspecte)
3. Suggère des ajustements avec justification

FORMAT DE SORTIE (JSON):
{
  "anomalies": [
    {
      "poste_numero": "01.01.001",
      "poste_description": "...",
      "notre_prix": 850.00,
      "prix_marche_estime": 720.00,
      "ecart_pct": 18.1,
      "recommandation": "Réduire de 15% en optimisant le ferraillage"
    }
  ],
  "opportunites": ["Postes où nous sommes compétitifs"],
  "risque_global": "moyen"
}
```

### Lentille Rédaction
**Modèle** : Gemini 2.5 Pro
**Usage** : Génération de chapitres mémoire

```
Tu es un rédacteur de mémoires techniques pour le BTP. Rédige un chapitre 
du mémoire en t'inspirant de nos dossiers gagnants.

CONTEXTE:
- Chapitre demandé: [X - Ex: "Moyens humains"]
- Exigences RC: [Extraits du RC concernant ce chapitre]
- Arguments gagnants similaires: [Extraits de mémoires gagnants via RAG]
- Projet actuel: [Description du projet en cours]

RÈGLES:
- Respecter strictement les exigences du RC
- Réutiliser les arguments des dossiers gagnants pertinents
- Adapter au contexte spécifique du projet
- Ton professionnel, factuel, percutant

FORMAT: Texte structuré avec titres et sous-parties
```

### Lentille Risque (Flash-Lite)
**Modèle** : Gemini 2.5 Flash-Lite
**Usage** : Scoring rapide

```
Analyse ce RC et identifie les risques contractuels majeurs.

Retourne un JSON avec:
- score_global (0-100)
- risques_identifies []
- clauses_dangereuses []
- recommandations []
```

---

## 8. Frontend - Interface Utilisateur

### Vue "Explorateur AO" (Split-Screen)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📁 AO: Résidence Les Lilas                    [Pricing] [Rédaction] [Risque] │
├──────────────────────────────────────────────────┬──────────────────────┤
│                                                  │                      │
│  📄 Gestion Documents                           │   🔍 ANALYSE         │
│  ┌─────────────────────────────────────────┐    │   ┌────────────────┐ │
│  │ • Liste documents (RC, BPU, CCTP)       │    │   │ Lentille Active│ │
│  │ • Boutons: [👁️ Prévisualiser] [📥 Télécharger] │   │  • Pricing     │ │
│  │ • Métadonnées extraites par IA          │    │   │  • Rédaction   │ │
│  │ • Statut traitement (✓/⏳/❌)            │    │   │  • Risque      │ │
│  │                                         │    │   └────────────────┘ │
│  │  [📄 RC_Projet.pdf] ✓ Traité            │    │                      │
│  │  [📊 BPU_Chiffrage.csv] ✓ Traité        │    │   📊 RÉSULTATS       │
│  │  [📋 CCTP_Technique.pdf] ⏳ En cours    │    │   ┌────────────────┐ │
│  │                                         │    │   │ Ecart prix: -5%│ │
│  └─────────────────────────────────────────┘    │   │ Risque: Moyen  │ │
│                                                  │   │ ...            │ │
│  💬 Drafting Sandbox (Bulle flottante)          │   └────────────────┘ │
│  ┌─────────────────────────────────────────┐    │                      │
│  │ 📝 Chapitre 3: Méthodologie             │    │   ✅ VALIDATION      │
│  │ [Éditeur riche avec toolbar]            │    │   [Lier ouvrage?]   │
│  │                                         │    │   [OUI] [NON]       │
│  │ "Nous mettons en œuvre..."              │    │                      │
│  │                                         │    │                      │
│  │ [💡 Améliorer] [📋 Copier]              │    │                      │
│  └─────────────────────────────────────────┘    │                      │
│                                                  │                      │
└──────────────────────────────────────────────────┴──────────────────────┘
```

### Fonctionnalités documentaires
- **Prévisualisation**: Ouverture dans nouvel onglet via URL signée S3
- **Téléchargement**: Redirection vers URL signée pour téléchargement direct
- **Métadonnées**: Affichage des données extraites par IA (client, projet, montant, etc.)
- **Statut**: Indicateur visuel du traitement (OCR, vectorisation)
- **Stockage**: Tous les documents stockés sur S3/R2 avec persistance complète

### Vue "Analyse Comparative" (Tableau de bord)

- **Graphique Gap de Pricing** : Comparaison visuelle gagnés vs perdus
- **Distribution des écarts** : Histogramme des écarts de prix
- **Badges de validation** : OUI/NON pour chaque suggestion IA

---

## 9. Tests End-to-End (Critères de Robustesse)

### Test E2E-001 : Ingestion Complète
**Objectif** : Vérifier l'ingestion d'un dossier AO complet
**Données** : Dossier avec RC.pdf, CCTP.pdf, BPU.csv, MEMOIRE.docx
**Étapes** :
1. Créer une candidature test
2. Appeler `ingest_ao_folder()`
3. Vérifier création des 4 documents en DB
4. Vérifier classification automatique (type_doc correct)
5. Vérifier extraction des métadonnées (client_nom, projet_nom)
**Critère de succès** : 4 documents créés, types corrects, metadata non vide

### Test E2E-002 : Classification IA
**Objectif** : Vérifier la précision de classification automatique
**Données** : 20 documents de types variés
**Étapes** :
1. Pour chaque document, appeler `classify_document()`
2. Comparer résultat IA vs type réel
**Critère de succès** : Taux de classification correct > 90%

### Test E2E-003 : Extraction Pricing BPU
**Objectif** : Vérifier l'extraction des postes BPU
**Données** : BPU CSV avec 50 postes
**Étapes** :
1. Uploader BPU
2. Appeler `extract_pricing_data()`
3. Vérifier création des postes dans `ao_postes_pricing`
**Critère de succès** : >95% des postes extraits avec prix et quantités corrects

### Test E2E-004 : RAG Pricing Context
**Objectif** : Vérifier la récupération de contexte historique
**Prérequis** : Base avec >10 AO gagnants historiques
**Étapes** :
1. Créer candidature avec BPU "Béton armé fondations"
2. Appeler `get_pricing_context("béton fondation")`
3. Vérifier retour des postes similaires historiques
**Critère de succès** : Postes pertinents retournés (vérification manuelle de la cohérence)

### Test E2E-005 : Lentille Pricing
**Objectif** : Vérifier l'analyse comparative de pricing
**Données** : BPU candidature + historique de victoires
**Étapes** :
1. Lancer analyse via `analyze_with_lens("pricing", candidature_id)`
2. Vérifier détection des écarts >20%
3. Vérifier format JSON de sortie
**Critère de succès** : Anomalies détectées, JSON valide, recommandations pertinentes

### Test E2E-006 : Lentille Rédaction
**Objectif** : Vérifier la génération de chapitre mémoire
**Données** : RC + candidature + mémoires gagnants historiques
**Étapes** :
1. Lancer génération chapitre "Moyens humains"
2. Vérifier prise en compte exigences RC
3. Vérifier cohérence avec historique
**Critère de succès** : Chapitre généré >500 mots, contient références RC

### Test E2E-007 : Workflow Complet
**Objectif** : Vérifier le flux end-to-end
**Données** : Dossier AO complet simulé
**Étapes** :
1. Créer candidature
2. Ingestion dossier
3. Extraction pricing
4. Analyse Lentille Pricing
5. Génération chapitre mémoire
6. Validation humaine des suggestions
**Critère de succès** : Flux sans erreur, données cohérentes à chaque étape

### Test E2E-008 : Intégration Dossiers
**Objectif** : Vérifier liaison candidature ↔ dossier
**Étapes** :
1. Créer un dossier existant
2. Créer candidature liée à ce dossier
3. Vérifier remontée candidatures dans vue dossier
**Critère de succès** : Liaison correcte, données visibles dans les deux sens

### Test E2E-009 : Performance Ingestion
**Objectif** : Vérifier les temps de réponse
**Données** : Dossier avec 10 documents (total 50MB)
**Étapes** :
1. Mesurer temps ingestion complète
2. Mesurer temps extraction BPU (100 postes)
**Critères** : Ingestion <30s, extraction BPU <10s

### Test E2E-010 : Résilience Erreurs
**Objectif** : Vérifier comportement sur fichiers corrompus
**Données** : PDF corrompu, CSV malformé
**Étapes** :
1. Tenter ingestion fichier corrompu
2. Vérifier gestion d'erreur gracieuse
3. Vérifier statut `error` en DB
**Critère de succès** : Pas de crash, statut error enregistré, message d'erreur clair

---

## 10. Intégration Continue

### Pipeline de vérification
```bash
# 1. Tests unitaires
pytest tests/test_ao_service.py -v

# 2. Tests E2E
pytest tests/ao_test_flow.py -v --e2e

# 3. Vérification migrations
supabase db lint

# 4. Tests frontend
npm run test:ao
```

### Métriques de qualité à suivre
- Taux de classification correct (objectif: >90%)
- Taux d'extraction pricing (objectif: >95%)
- Temps moyen ingestion (objectif: <30s/dossier)
- Score satisfaction utilisateurs (validation suggestions)

---

## 11. Roadmap

### Phase 1 (MVP)
- [x] Documentation et spécifications
- [x] Migrations SQL
- [x] Services backend core
- [x] Lentilles Pricing & Rédaction
- [ ] Tests E2E de base

### Phase 2
- [ ] Interface Explorateur AO
- [ ] Drafting Sandbox
- [ ] Dashboard Analyse Comparative
- [ ] Système de badges validation

### Phase 3
- [ ] Lentille Risque avancée
- [ ] Analyse prédictive (probabilité de gain)
- [ ] Templates mémoire personnalisables
- [ ] Import/export formats variés

---

## Références

- [Architecture SurenSaaS](./ARCHITECTURE.md)
- [Base de données](./DATABASE.md)
- [API Backend](./BACKEND.md)
