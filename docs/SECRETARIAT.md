# Module Secrétariat IA - Documentation & Plan d'implémentation

## Vue d'ensemble

Module d'intelligence métier pour l'analyse et le traitement des communications (emails) d'une PME du BTP. **Ce module est purement métier** : il consomme les données structurées du module Emails et prend des décisions opérationnelles.

> **Separation of concerns** : Le module Emails (ingestion, stockage, vectorisation) est documenté séparément dans `docs/EMAILS.md`. Ce module Secrétariat ne fait que consommer les données déjà structurées.

---

## Architecture

### Positionnement dans le système

```
┌──────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  Module Emails   │────▶│  Module Secrétariat │────▶│   Actions       │
│  (Data Layer)    │     │  (Ce document)      │     │   Métiers       │
└──────────────────┘     └─────────────────────┘     └─────────────────┘
                               │                             │
                               ▼                             ▼
                        ┌──────────────┐            ┌──────────────┐
                        │  Analyse IA  │            │ Workflows    │
                        │  Contextuelle│            │ BTP          │
                        └──────────────┘            └──────────────┘
```

### Responsabilités du module Secrétariat

| Couche | Responsabilité | Hors scope |
|--------|---------------|------------|
| **Analyse** | Comprendre le contexte BTP, identifier l'intention | Connexion Gmail, stockage fichiers |
| **Décision** | Statuts de traitement, priorisation | Vectorisation, OCR |
| **Action** | Workflows métiers, alertes, création dossiers | Synchronisation emails |

---

## Flux de données

```
1. TRIGGER (après vectorisation email)
   └─▶ Nouvel email avec statut 'vectorized' détecté

2. ANALYSE CONTEXTUELLE
   ├─▶ Récupération thread complet (historique conversation)
   ├─▶ Recherche RAG (emails similaires, docs pertinents)
   ├─▶ Analyse IA (Gemini/LLM) :
   │   ├── Type de demande (devis, facture, RDV, problème...)
   │   ├── Urgence détectée (mots-clés, deadline)
   │   ├── Chantier/Projet concerné (extraction entités)
   │   └── Interlocuteur (client, fournisseur, admin...)
   └─▶ Stockage analyse dans `secretariat_analysis`

3. DÉCISION & STATUT
   ├─▶ Détermination statut :
   │   ├── 'processed' → Action automatique possible
   │   ├── 'toBeReviewed' → Intervention humaine requise
   │   └── 'pending_info' → Attente informations complémentaires
   └─▶ Stockage dans `secretariat_decisions`

4. WORKFLOWS MÉTIERS (si statut = 'processed')
   ├─▶ Création alerte conducteur de travaux
   ├─▶ Création tâche dans système de gestion
   ├─▶ Notification équipe appropriée
   └─▶ Mise à jour CRM/Planning si pertinent

5. FEEDBACK & APPRENTISSAGE
   └─▶ Si correction humaine → logging pour amélioration modèle
```

---

## Structure de base de données

### Tables créées (fichier `db/schema/025_secretariat_tables.sql`)

#### 1. `secretariat_analysis` - Analyse IA des emails
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- email_id UUID REFERENCES emails(id)
- thread_id TEXT                             -- Référence thread Gmail

-- Analyse IA
- intent_type INTENT_TYPE                    -- Enum: devis/facture/rdv/reclamation/info
- confidence_score DECIMAL(3,2)              -- 0.00 à 1.00
- urgency_level URGENCY_LEVEL                -- Enum: low/medium/high/critical
- extracted_entities JSONB                   -- {chantier, client, montant, dates...}
- context_summary TEXT                       -- Résumé généré par IA
- similar_emails UUID[]                      -- IDs emails similaires (RAG)
- related_documents UUID[]                   -- IDs docs pertinents (factures, devis...)

-- Métadonnées
- model_used TEXT                            -- Gemini-1.5-flash, etc.
- analysis_duration_ms INTEGER               -- Temps traitement
- analyzed_at TIMESTAMP

-- Versioning
- analysis_version INTEGER DEFAULT 1         -- Si ré-analyse
- parent_analysis_id UUID                    -- Analyse précédente si ré-analyse

- created_at / updated_at
```

#### 2. `secretariat_decisions` - Décisions métier
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- analysis_id UUID REFERENCES secretariat_analysis(id)
- email_id UUID REFERENCES emails(id)

-- Décision
- decision_status DECISION_STATUS            -- Enum: processed/toBeReviewed/pending_info
- decision_reason TEXT                       -- Justification IA
- required_action REQUIRED_ACTION            -- Enum: alert/create_task/notify/none

-- Assignation
- assigned_team TEAM_TYPE                    -- Enum: commercial/technique/comptabilite/direction
- assigned_user_id UUID REFERENCES users(id) -- Si assigné spécifiquement
- due_date TIMESTAMP                         -- Échéance si applicable

-- Traçabilité
- decided_by UUID REFERENCES users(id)       -- IA (null) ou utilisateur si override
- decided_at TIMESTAMP
- human_reviewed BOOLEAN DEFAULT false
- human_notes TEXT                           -- Commentaires correcteur

- created_at / updated_at
```

#### 3. `secretariat_workflows` - Workflows exécutés
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- decision_id UUID REFERENCES secretariat_decisions(id)
- email_id UUID REFERENCES emails(id)

-- Workflow
- workflow_type WORKFLOW_TYPE                -- Enum: alert_conducteur/create_task/update_crm
- workflow_status WORKFLOW_STATUS            -- Enum: pending/executed/failed
- workflow_payload JSONB                     -- Données spécifiques workflow

-- Exécution
- executed_at TIMESTAMP
- execution_result JSONB                     -- Résultat/réponse
- execution_error TEXT                       -- Si échec
- retry_count INTEGER DEFAULT 0

- created_at / updated_at
```

#### 4. `secretariat_learning` - Feedback pour amélioration
```sql
- id UUID PRIMARY KEY
- org_id UUID REFERENCES organizations(id)
- analysis_id UUID REFERENCES secretariat_analysis(id)

-- Feedback
- feedback_type FEEDBACK_TYPE                -- Enum: correction/validation/erreur
- original_intent INTENT_TYPE                -- Ce que l'IA a détecté
- corrected_intent INTENT_TYPE               -- Correction humaine (si applicable)
- corrected_urgency URGENCY_LEVEL            -- Correction niveau urgence
- reviewer_id UUID REFERENCES users(id)
- review_notes TEXT

- reviewed_at TIMESTAMP
- created_at
```

### Types PostgreSQL

```sql
-- Intention détectée
CREATE TYPE intent_type AS ENUM (
    'devis_request',         -- Demande de devis
    'devis_followup',        -- Relance devis
    'facture_question',      -- Question sur facture
    'facture_payment',       -- Confirmation paiement
    'rdv_scheduling',        -- Prise de RDV
    'rdv_change',            -- Modification RDV
    'chantier_update',       -- Mise à jour chantier
    'chantier_problem',      -- Problème sur chantier
    'fournisseur_order',     -- Commande fournisseur
    'fournisseur_livraison', -- Suivi livraison
    'administratif',         -- Documents admin
    'reclamation',           -- Réclamation client
    'information',           -- Info générale
    'spam',                  -- Indésirable
    'autre'                  -- Non catégorisé
);

-- Niveau d'urgence
CREATE TYPE urgency_level AS ENUM (
    'low',        -- Traitement standard
    'medium',     -- Priorité normale
    'high',       -- Urgent
    'critical'    -- Bloquant, réponse immédiate requise
);

-- Statut de décision
CREATE TYPE decision_status AS ENUM (
    'processed',      -- Action automatique effectuée
    'toBeReviewed',   -- Intervention humaine requise
    'pending_info',   -- Attente informations
    'escalated'       -- Escaladé à la direction
);

-- Actions requises
CREATE TYPE required_action AS ENUM (
    'none',               -- Aucune action
    'alert_conducteur',   -- Alerte conducteur travaux
    'alert_commercial',   -- Alerte équipe commerciale
    'alert_comptabilite', -- Alerte comptabilité
    'create_task',        -- Créer tâche dans système
    'create_event',       -- Créer événement calendrier
    'update_crm',         -- Mettre à jour CRM
    'draft_response'      -- Préparer brouillon réponse
);

-- Équipes
CREATE TYPE team_type AS ENUM (
    'commercial',
    'technique',
    'comptabilite',
    'direction',
    'administratif'
);

-- Types de workflow
CREATE TYPE workflow_type AS ENUM (
    'alert_conducteur',
    'alert_commercial',
    'alert_comptabilite',
    'create_task',
    'create_calendar_event',
    'update_crm_contact',
    'update_crm_opportunity',
    'send_notification',
    'draft_email_response'
);

-- Statut workflow
CREATE TYPE workflow_status AS ENUM (
    'pending',
    'executing',
    'executed',
    'failed',
    'cancelled'
);

-- Types de feedback
CREATE TYPE feedback_type AS ENUM (
    'validation',    -- IA correcte
    'correction',    -- Correction mineure
    'erreur',        -- Erreur majeure
    'faux_positif'   -- Fausse alerte
);
```

---

## API Endpoints (à ajouter dans OpenAPI - Phase 2)

### Analyse
```
POST /api/v1/{org}/secretariat/analyze
├── Body: { "email_id": "uuid" }
└── Response: { "analysis_id": "uuid", "status": "analyzed", ... }

GET /api/v1/{org}/secretariat/analysis/{id}
└── Response: Détail complet analyse + décision + workflows
```

### Décisions à revoir
```
GET /api/v1/{org}/secretariat/decisions/to-review
├── Query: team, urgency, date_from, date_to
└── Response: Liste décisions 'toBeReviewed' paginée

PUT /api/v1/{org}/secretariat/decisions/{id}/review
├── Body: { "status": "processed", "notes": "...", "assigned_user_id": "..." }
└── Response: Décision mise à jour
```

### Dashboard & métriques
```
GET /api/v1/{org}/secretariat/dashboard
└── Response: {
    "to_review_count": 12,
    "processed_today": 45,
    "accuracy_rate": 0.92,
    "urgent_items": [...]
}

GET /api/v1/{org}/secretariat/metrics
└── Response: Statistiques détaillées (temps traitement, taux erreur...)
```

### Feedback & apprentissage
```
POST /api/v1/{org}/secretariat/feedback
├── Body: { "analysis_id": "uuid", "type": "correction", "corrected_intent": "..." }
└── Response: Feedback enregistré
```

---

## TÂCHES À FAIRE (Phase 2: Secrétariat - Future)

> **⚠️ Prérequis** : Le module Emails doit être complètement fonctionnel (vectorisation opérationnelle).

### S1: Moteur d'analyse contextuelle
**Objectif** : Comprendre le contenu et le contexte métier
- [ ] Créer `app/services/secretariat/analysis_engine.py`
- [ ] Intégration RAG (recherche emails/docs similaires via pgvector)
- [ ] Prompt engineering pour extraction entités BTP (chantiers, clients, matériaux)
- [ ] Classification intention (intent_type) avec confidence score
- [ ] Détection urgence (mots-clés, deadline, contexte)
- [ ] Génération résumé contextuel
- [ ] Tests sur corpus d'exemples BTP

### S2: Service de décision
**Objectif** : Déterminer le statut et les actions requises
- [ ] Créer `app/services/secretariat/decision_service.py`
- [ ] Règles métier de routage (intent → team/action)
- [ ] Scoring priorité (urgence × importance client × contexte projet)
- [ ] Détection cas ambigus (flag 'toBeReviewed')
- [ ] Apprentissage depuis feedback historique
- [ ] Override possible par règles métier explicites

### S3: Workflows métiers
**Objectif** : Exécuter les actions automatisées
- [ ] Créer `app/services/secretariat/workflow_engine.py`
- [ ] Workflow "Alerte conducteur" (notification push/email)
- [ ] Workflow "Création tâche" (intégration système de gestion)
- [ ] Workflow "Mise à jour CRM" (API externe ou table interne)
- [ ] Gestion erreurs workflows (retry, alerte admin)
- [ ] Logging complet des exécutions

### S4: Structure base de données
**Objectif** : Créer les tables métier
- [ ] Créer fichier `db/schema/025_secretariat_tables.sql`
- [ ] Table `secretariat_analysis` (résultats IA)
- [ ] Table `secretariat_decisions` (statuts et assignations)
- [ ] Table `secretariat_workflows` (exécutions actions)
- [ ] Table `secretariat_learning` (feedback amélioration)
- [ ] Types ENUM métier (intent, urgence, statuts)
- [ ] RLS policies
- [ ] Indexes performance
- [ ] Triggers updated_at

### S5: Interface d'approbation (Frontend)
**Objectif** : Permettre la validation humaine
- [ ] Page "À traiter" (liste décisions 'toBeReviewed')
- [ ] Vue détail email + analyse IA + actions suggérées
- [ ] Boutons rapides ("Valider", "Corriger", "Escalader")
- [ ] Saisie feedback (correction intention, notes)
- [ ] Dashboard métriques (taux automatisation, accuracy)

### S6: API Endpoints
**Objectif** : Exposer la logique métier
- [ ] Routes OpenAPI pour analyse et décisions
- [ ] Endpoints dashboard et métriques
- [ ] Endpoints feedback et correction
- [ ] Génération code et implémentation contrôleurs
- [ ] Documentation API

### S7: Intégration RAG avancée
**Objectif** : Enrichir l'analyse avec contexte historique
- [ ] Recherche similarité sur embeddings emails
- [ ] Recherche dans documents structurés (factures, devis)
- [ ] Contextualisation thread conversation
- [ ] Mémoire "client" (historique interactions)

### S8: Apprentissage et amélioration
**Objectif** : Améliorer la qualité des décisions
- [ ] Collecte feedback utilisateurs
- [ ] Dataset d'entraînement (emails annotés)
- [ ] Fine-tuning ou few-shot prompting
- [ ] Métriques de performance (precision, recall par intent)
- [ ] Alertes drift (quand accuracy baisse)

### S9: Règles métier personnalisables
**Objectif** : Adapter à chaque PME
- [ ] Interface admin pour règles de routage
- [ ] Configuration seuils urgence
- [ ] Mapping clients importants → priorité
- [ ] Blacklist/Whitelist expéditeurs

### S10: Tests & Validation métier
**Objectif** : Garantir la fiabilité
- [ ] Tests scénarios BTP réels
- [ ] Validation avec utilisateurs (beta test)
- [ ] Mesure taux de bonnes décisions
- [ ] Optimisation prompts selon retours

---

## Modèle de données analysées

### Exemple d'analyse stockée

```json
{
  "analysis": {
    "intent_type": "devis_request",
    "confidence_score": 0.94,
    "urgency_level": "high",
    "extracted_entities": {
      "client": {
        "name": "Construction Dupont SA",
        "email": "contact@dupont-construction.fr",
        "siret": "12345678901234"
      },
      "chantier": {
        "address": "15 Rue de la Paix, 75002 Paris",
        "type": "Rénovation bureaux"
      },
      "demande": {
        "description": "Devis pour peinture 500m²",
        "deadline": "2024-02-15",
        "budget_mentionne": "15-20k€"
      }
    },
    "context_summary": "Client existant demande devis urgent pour rénovation bureaux. Budget aligné avec nos prestations. Deadline courte (2 semaines).",
    "similar_emails": ["uuid-1", "uuid-2"],
    "related_documents": ["devis-2023-045"]
  },
  "decision": {
    "status": "processed",
    "required_action": "alert_commercial",
    "assigned_team": "commercial",
    "due_date": "2024-01-20T17:00:00Z"
  }
}
```

---

## Dépendances avec module Emails

### Contrat d'interface

Le module Secrétariat consomme uniquement via cette interface :

```sql
-- Emails prêts pour analyse
SELECT e.*, 
       array_agg(DISTINCT ea.id) as attachment_ids,
       array_agg(DISTINCT ee.embedding) as embeddings
FROM emails e
LEFT JOIN email_attachments ea ON ea.email_id = e.id
LEFT JOIN email_embeddings ee ON ee.email_id = e.id
WHERE e.processing_status = 'vectorized'
AND e.id NOT IN (SELECT email_id FROM secretariat_analysis)
GROUP BY e.id;
```

### Trigger de démarrage

L'analyse secrétariat est déclenchée :
1. **Manuellement** : Endpoint dédié
2. **Automatiquement** : Quand `emails.processing_status` passe à `'vectorized'`

---

## Workflows métiers BTP détaillés

### W1: Demande de devis
```
Intent: devis_request
├── Urgence: high si deadline < 2 semaines
├── Équipe: commercial
├── Action: Créer opportunité CRM + Alerte commercial
└── Due date: +24h ouvrées
```

### W2: Problème sur chantier
```
Intent: chantier_problem
├── Urgence: critical si "arrêt", "danger", "accident"
├── Équipe: technique + direction
├── Action: Alerte conducteur + SMS responsable
└── Due date: Immédiat
```

### W3: Relance facture impayée
```
Intent: facture_question
├── Urgence: medium
├── Équipe: comptabilite
├── Action: Créer tâche suivi + Notification compta
└── Due date: +48h
```

### W4: Modification RDV
```
Intent: rdv_change
├── Urgence: high si < 24h avant RDV
├── Équipe: commercial/technique selon type RDV
├── Action: Mettre à jour planning + Notifier concernés
└── Due date: +4h
```

---

## Conventions & Patterns

### Nommage
- Tables : `secretariat_analysis`, `secretariat_decisions`, `secretariat_workflows`, `secretariat_learning`
- Services : `analysis_engine.py`, `decision_service.py`, `workflow_engine.py`
- Types ENUM : `intent_type`, `urgency_level`, `decision_status`

### Gestion des erreurs
- Erreur analyse IA → `decision_status = 'toBeReviewed'` + log
- Erreur workflow → Retry 3x puis `workflow_status = 'failed'` + alerte admin
- Feedback utilisateur → Logging immédiat pour amélioration

### Métriques clés à tracker
- **Automation rate** : % emails traités sans intervention
- **Accuracy** : % décisions correctes (vs feedback)
- **Response time** : Temps moyen traitement
- **Escalation rate** : % cas escaladés à humain

---

## Notes de conception

### Pourquoi séparer décision et workflow ?

1. **Rejeu** : On peut refaire les workflows sans ré-analyser
2. **Audit** : Traçabilité complète décision → exécution
3. **Correction** : Si workflow échoue, on peut le relancer

### Pourquoi table `secretariat_learning` ?

L'amélioration continue est critique pour un système IA. Cette table permet :
- Mesurer la qualité (accuracy)
- Identifier les cas problématiques
- Créer dataset pour fine-tuning
- Détecter le drift (baisse de performance)

### Pourquoi versioning des analyses ?

Si on améliore le modèle IA, on peut ré-analyser les emails historiques pour comparer les performances.

---

## Tests

### Tests end-to-end (`tests/test_secretariat_scenarios.py`)

Les tests valident le flux complet : Email → Vectorisation → Analyse Secrétaire → Chat.

⚠️ **Coût** : Ces tests utilisent de vrais appels Vertex AI
- Coût estimé : ~0.01-0.03€ par test
- Durée : 15-30 secondes par test

#### Exécution

```bash
# Tous les tests (y compris les tests lents avec appels Gemini)
pytest tests/test_secretariat_scenarios.py -v

# Ignorer les tests lents (sans appels Gemini)
pytest tests/test_secretariat_scenarios.py -v -m 'not slow'

# Un seul scénario
pytest tests/test_secretariat_scenarios.py::TestSecretariatScenarios::test_scenario_1_first_email_analysis_and_chat -v -s
```

#### Scénarios de test

##### Scénario 1 : Premier email + Analyse + Chat

**Objectif** : Valider l'analyse automatique et le chat de base

**Données** : Email forward de demande de devis ACORUS (basé sur INV-EXA-0001)

**Validations** :
- Résumé contient : `["devis", "bf2507022328", "acorus", "salle de bain"]`
- Statut dans `['new', 'awaiting_user']`
- Message system existe dans chat
- Réponse à question cite le numéro de devis
- Sources et confidence présentes

**Coût** : ~0.01€ (1 pré-analyse + 1 chat)

##### Scénario 2 : Thread de 2 emails (relance)

**Objectif** : Valider la mise à jour du contexte avec nouvel email

**Données** : 
- Email 1 : Devis initial
- Email 2 : Relance avec mentions "urgent", "échéance", "handicapé"

**Validations** :
- Résumé mis à jour mentionne : `["relance", "urgent", "échéance", "handicapé"]`
- Statut = `'urgent'` (détection automatique)
- Urgence = `'high'`
- Message system mis à jour (pas de doublon)

**Coût** : ~0.01€ (1 pré-analyse)

##### Scénario 3 : Contexte complet + Question

**Objectif** : Valider que la réponse utilise les 2 emails (contexte complet)

**Données** : Même thread que Scénario 2

**Question** : `"Quel est le montant du devis et pourquoi c'est urgent ?"`

**Validations** :
- Réponse mentionne montant (de Email 1/PJ)
- Réponse explique urgence (de Email 2)
- Sources citées ≥ 1
- Confidence > 0.6

**Coût** : ~0.02€ (2 pré-analyses + 1 chat)

#### Stratégie de validation

Comme les réponses Gemini ne sont pas déterministes, les tests utilisent une **validation par mots-clés** :

```python
def assert_contains_any(text: str, keywords: list):
    """Valide que text contient au moins un des keywords."""
    text_check = text.lower()
    found = [kw for kw in keywords if kw.lower() in text_check]
    assert len(found) > 0, f"Aucun mot trouvé dans: {text[:200]}"
```

**Exemple** :
```python
# Validation résumé
self.assert_contains_any(summary, [
    "devis", "bf2507022328", "acorus", "salle de bain"
])

# Validation réponse chat  
self.assert_contains_any(response_text, [
    "3280.78", "euro", "montant"
])
```

---

## Implémentation Actuelle (Phase 1)

### Vue d'ensemble

La Secrétaire IA est maintenant **opérationnelle** avec deux fonctionnalités principales:

1. **Pré-analyse automatique** des nouveaux emails (asynchrone, déclenchée après vectorisation)
2. **Réponses interactives** dans le chat des threads

### Architecture Implémentée

```
┌─────────────────────────────────────────────────────────────┐
│                    SECRÉTAIRE IA                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐      ┌──────────────────────────────┐ │
│  │  PRÉ-ANALYSE     │      │  RÉPONSE CHAT                │ │
│  │  (Async)         │      │  (On-demand)                 │ │
│  └────────┬─────────┘      └──────────────┬───────────────┘ │
│           │                               │                  │
│           ▼                               ▼                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              CONTEXT BUILDER                         │   │
│  │  - Thread (emails, participants)                    │   │
│  │  - Attachments (OCR text)                           │   │
│  │  - RAG (emails similaires via embeddings)          │   │
│  │  - Chat history                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│           │                               │                  │
│           ▼                               ▼                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              GEMINI CLIENT                           │   │
│  │  Model: VERTEX_AI_SECRETARIAT_MODEL                 │   │
│  │  Default: gemini-1.5-flash-001                      │   │
│  │  Temperature: 0.3 (formel/concis)                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Fichiers créés

```
app/
├── models/
│   └── secretariat.py              # Modèles Pydantic (EmailStatus, AnalysisResult, ChatResponse)
├── services/
│   ├── secretariat_service.py      # Service principal (analyze_new_email, respond_to_chat)
│   ├── secretariat_context.py      # Context Builder (prompts, RAG, formatage)
│   └── emails/
│       └── embedding_service.py    # Déclenchement après vectorisation
├── agents/
│   └── prompts/
│       └── secretariat/
│           ├── system_preanalysis.txt   # Style: formel/concis
│           ├── user_preanalysis.txt     # Template avec placeholders
│           ├── system_chat.txt          # Style: formel/concis
│           └── user_chat.txt            # Template avec placeholders
└── core/
    └── config.py                   # VERTEX_AI_SECRETARIAT_MODEL
```

### Configuration

**Variable d'environnement:**
```bash
VERTEX_AI_SECRETARIAT_MODEL=gemini-1.5-flash-001
```

**Dépendances:**
- `GOOGLE_GEMINI_CREDENTIALS_B64` (déjà existant)
- `GCP_PROJECT_ID` (déjà existant)
- `GEMINI_LOCATION` (déjà existant, default: europe-west1)

### Fonctionnalités

#### 1. Pré-analyse des emails

**Déclencheur:** Après vectorisation (`processing_status` → "vectorized")

**Processus:**
```python
# Dans embedding_service.py
async def vectorize_email_async(self, email_id: str):
    # ... vectorisation ...
    await email_db.update_email_status(email_id, "vectorized")
    
    # Déclencher l'analyse Secrétaire (asynchrone)
    asyncio.create_task(
        secretariat_service.analyze_new_email(email_id)
    )
```

**Réponse JSON attendue:**
```json
{
  "status": "new|awaiting_response|awaiting_user|resolved|urgent|escalated",
  "summary": "Résumé concis (2-3 phrases)",
  "context": "Contexte important",
  "key_points": ["Point clé 1", "Point clé 2"],
  "suggested_actions": ["Action 1", "Action 2"],
  "urgency_reason": "Raison si urgent",
  "attachments_analysis": "Analyse des PJ"
}
```

#### 2. Réponses dans le chat

**Déclencheur:** Message utilisateur dans le chat du thread

**Réponse JSON attendue:**
```json
{
  "response": "Réponse textuelle",
  "sources": ["Email du 28/07/2025", "Facture.pdf"],
  "confidence": 0.95,
  "suggested_follow_up": "Question de suivi suggérée"
}
```

### Statuts des emails

| Statut | Description |
|--------|-------------|
| `new` | Nouveau, pas encore analysé |
| `in_analysis` | En cours d'analyse par IA |
| `awaiting_response` | Attente réponse du client |
| `awaiting_user` | Attente action utilisateur |
| `resolved` | Traité/Résolu |
| `urgent` | Marqué urgent par IA |
| `escalated` | À escalader (niveau 2) |

### Prompts templates

Les prompts sont stockés dans des fichiers `.txt` modifiables:

**Placeholders pré-analyse:**
- `{{THREAD_CONTEXT}}` - Informations du thread
- `{{CURRENT_EMAIL}}` - Email à analyser
- `{{ATTACHMENTS_CONTEXT}}` - Texte OCR des pièces jointes
- `{{RAG_CONTEXT}}` - Emails similaires trouvés

**Placeholders chat:**
- `{{THREAD_SUMMARY}}` - Résumé du thread
- `{{CHAT_HISTORY}}` - Historique des messages
- `{{EMAILS_CONTEXT}}` - Emails du thread
- `{{ATTACHMENTS_CONTEXT}}` - Pièces jointes
- `{{RAG_CONTEXT}}` - Context similaire
- `{{USER_QUESTION}}` - Question de l'utilisateur

### Utilisation

#### Analyse manuelle (pour tests)

```python
from app.services.secretariat_service import secretariat_service

# Analyser un email spécifique
result = await secretariat_service.analyze_new_email("email-uuid")
print(result.summary)
print(result.status)
```

#### Réponse dans le chat

```python
from app.services.secretariat_service import secretariat_service
from uuid import UUID

# Obtenir une réponse
response = await secretariat_service.respond_to_chat(
    thread_id=UUID("thread-uuid"),
    session_id=UUID("session-uuid"),
    user_message="Quel est le montant du devis ?"
)

print(response.response)
print(response.sources)
```

### Personnalisation

#### Modifier le style (formel/concis)

Éditer les fichiers:
- `app/agents/prompts/secretariat/system_preanalysis.txt`
- `app/agents/prompts/secretariat/system_chat.txt`

#### Changer le modèle

```bash
# .env.test ou .env.prod
VERTEX_AI_SECRETARIAT_MODEL=gemini-1.5-pro-001
```

#### Ajuster la température

Modifier dans `secretariat_service.py`:
```python
gemini = GeminiClient(
    ...
    temperature=0.3,  # Plus bas = plus déterministe
    ...
)
```

### Coûts et optimisations

**Modèle:** `gemini-1.5-flash-001`
- Rapide et économique
- Contexte: jusqu'à 1M tokens
- Tarif: ~$0.35/million tokens (input)

**Optimisations:**
- Chunking des emails (limité à 1500-2000 caractères)
- Limitation historique (5 derniers emails)
- Limitation RAG (3 résultats max)

---

## 🧪 Tests

### Exécution des tests

```bash
# Tous les tests de la Secrétaire (incluent des appels réels à Gemini)
pytest tests/test_secretariat_scenarios.py -v

# Un scénario spécifique
pytest tests/test_secretariat_scenarios.py::TestSecretariatScenarios::test_scenario_1_first_email_analysis_and_chat -v

# Ignorer les tests lents (sans appels Gemini)
pytest tests/test_secretariat_scenarios.py -v -m 'not slow'
```

### ⚠️ Coût des tests

**Important:** Ces tests utilisent de vrais appels Vertex AI.

| Scénario | Coût estimé | Durée |
|----------|-------------|-------|
| Test 1: Premier email + Chat | ~0.01€ | ~10s |
| Test 2: 2 emails + Relance | ~0.01€ | ~10s |
| Test 3: Contexte + Question | ~0.02€ | ~15s |
| **TOTAL** | **~0.04€** | **~35s** |

### État des tests (Avril 2025)

| Scénario | Status | Description |
|----------|--------|-------------|
| **Test 1** | ✅ PASS | Premier email → Analyse → Chat |
| **Test 2** | ✅ PASS | Thread de 2 emails avec relance urgente |
| **Test 3** | ✅ PASS | Contexte complet + Question utilisateur |
| **TOTAL** | **3/3** | **100%** |

#### Scénario 1: Premier email + Analyse + Chat

**Validations:**
- Résumé contient: `["devis", "bf2507022328", "acorus", "salle de bain"]`
- Statut dans `['new', 'waiting', 'in_progress']`
- Message system existe dans chat
- Réponse à question cite le numéro de devis
- Sources et confidence présentes

#### Scénario 2: Thread de 2 emails (relance)

**Données:**
- Email 1: Devis initial (INV-EXA-0001)
- Email 2: Relance avec mentions "urgent", "échéance", "handicapé"

**Validations:**
- Résumé mis à jour mentionne: `["relance", "urgent", "échéance", "handicapé"]`
- Statut = `waiting` (urgent mappé pour la DB)
- Urgence = `high`
- Message system mis à jour (pas de doublon)

#### Scénario 3: Contexte complet + Question

**Question:** `"Quel est le montant du devis et pourquoi c'est urgent ?"`

**Validations:**
- Réponse mentionne montant (de Email 1/PJ)
- Réponse explique urgence (de Email 2)
- Sources citées ≥ 1
- Confidence > 0.6

### Stratégie de validation

Comme les réponses Gemini ne sont pas déterministes, les tests utilisent une **validation par mots-clés** :

```python
def assert_contains_any(text: str, keywords: list):
    """Valide que text contient au moins un des keywords."""
    text_check = text.lower()
    found = [kw for kw in keywords if kw.lower() in text_check]
    assert len(found) > 0
```

**Exemple:**
```python
# Validation résumé
self.assert_contains_any(summary, [
    "devis", "bf2507022328", "acorus", "salle de bain"
])

# Validation réponse chat  
self.assert_contains_any(response_text, [
    "3280.78", "euro", "montant"
])
```

---

## ✅ Implémentation - Modules Drafting & Dossiers (Avril 2025)

### Status: Backend + Frontend Complets

#### ✅ Module: Drafting Sandbox (Rédacteur)

**Fonctionnalités implémentées:**
- ✅ Bouton "Préparer une réponse" dans le panneau Assistant IA
- ✅ Modal flottant avec Rich Text Editor
- ✅ Génération V1 via Gemini (ou fallback local)
- ✅ Smart Chips: Plus court, Plus poli, Ajouter signature, Plus technique
- ✅ Petit Prompt: Zone d'instruction pour itérer
- ✅ Copie dans le clipboard

**Fichiers créés:**
- Backend: `app/services/drafting_service.py`
- API: Endpoints dans `app/api/email_threads.py`
- Frontend: `components/secretary/DraftSandbox.tsx`
- Intégration: Bouton dans `[id]/page.tsx` (email thread detail)

**Routes API:**
```
POST /api/v1/{org}/email-threads/{id}/draft
PUT  /api/v1/{org}/email-threads/{id}/draft/{draft_id}
POST /api/v1/{org}/email-threads/{id}/draft/{draft_id}/smart-chip
```

#### ✅ Module: Le Classeur (Dossiers)

**Fonctionnalités implémentées:**
- ✅ CRUD complet des dossiers
- ✅ Table `dossiers` avec contraintes et indexes
- ✅ Liaison Thread ↔ Dossier (1:N)
- ✅ Page liste: `/dashboard/dossiers`
- ✅ Page détail: `/dashboard/dossiers/[id]` avec tabs
- ✅ Onglets: Emails, Documents, Tâches
- ✅ Suggestion IA de liaison (basique)
- ✅ Menu "Dossiers" dans la sidebar

**Fichiers créés:**
- DB: `db/schema/026_dossiers.sql`
- Models: `app/models/dossiers.py`
- Backend: `app/services/dossier_service.py`
- API: `app/api/dossiers.py`
- Frontend:
  - `app/dashboard/dossiers/page.tsx`
  - `app/dashboard/dossiers/[id]/page.tsx`
  - `app/dashboard/dossiers/new/page.tsx`
- Tests: `tests/test_dossiers.py` (7/7 passent)

**Routes API:**
```
GET    /api/v1/{org}/dossiers
POST   /api/v1/{org}/dossiers
GET    /api/v1/{org}/dossiers/{id}
PATCH  /api/v1/{org}/dossiers/{id}
DELETE /api/v1/{org}/dossiers/{id}
GET    /api/v1/{org}/dossiers/{id}/emails
GET    /api/v1/{org}/dossiers/{id}/documents
GET    /api/v1/{org}/dossiers/{id}/summary
GET    /api/v1/{org}/email-threads/{id}/suggested-dossiers
POST   /api/v1/{org}/email-threads/{id}/link-to-dossier
POST   /api/v1/{org}/email-threads/{id}/unlink-from-dossier
```

**Navigation:** Menu "Dossiers" ajouté dans `app/dashboard/layout.tsx`

---

## Références

- `docs/EMAILS.md` - Module ingestion emails (prérequis)
- `docs/EMAILS_MANAGEMENT.md` - Gestion des threads et chat
- `docs/CAPABILITIES.md` - Permissions (`secretariat:read`, `secretariat:review`)
- `docs/gemini-extraction-agent.md` - Agent IA existant
- `docs/BACKEND.md` - Architecture backend
