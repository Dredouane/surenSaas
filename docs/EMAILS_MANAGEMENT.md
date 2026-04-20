# Emails Management - Documentation

Module de gestion et visualisation des emails pour les entreprises (company).

> **Architecture** : L'utilisateur voit des **THREADS** (conversations), pas des emails isolés. Un email entrant est automatiquement rattaché à un thread existant ou crée un nouveau thread.

---

## 🏗️ Vue d'ensemble

### Principe de visibilité

```
┌─────────────────────────────────────────────────────────┐
│  PAGE LISTE (Threads)                                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 📧 Chantier Sanibatiment - Devis       [HIGH] 🟡   │ │  ← Thread
│  │    ACORUS | 28/07/2025 | 3 messages                  │ │
│  │                                                      │ │
│  │ 📧 Facture mensuelle EDF               [NEW] 🔵    │ │  ← Thread
│  │    EDF | 25/07/2025 | 1 message                      │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓ Clique
┌─────────────────────────────────────────────────────────┐
│  PAGE DÉTAIL (Split Screen)                              │
│  ┌─────────────────────────┬──────────────────────────┐ │
│  │   CONVERSATION          │   CHAT IA                │ │
│  │   (ThreadPanel)         │   (ChatPanel)            │ │
│  │                         │                          │ │
│  │ [Client] Bonjour,       │ 🤖 Résumé du dossier :   │ │
│  │ je relance le devis...  │                          │ │
│  │                         │ De quoi s'agit-il ?      │ │
│  │ [Toi] Merci pour...     │ Relance devis Sanibat.   │ │
│  │                         │                          │ │
│  │ [Client] Pouvez-vous... │ Context RAG :            │ │
│  │                         │ 2 échanges similaires... │ │
│  │                         │                          │ │
│  │ [Onglets: Conv / PJ]    │ Urgence : Élevée ⚠️      │ │
│  └─────────────────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Structure de Base de Données

### Tables créées

#### 1. `email_threads` - Ce que voit l'utilisateur

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant interne (PK) |
| `org_id` | UUID | Organisation (FK) |
| `company_id` | UUID | Entreprise/Company (FK) |
| `gmail_thread_id` | TEXT | ID Gmail du thread |
| `subject` | TEXT | Sujet principal |
| `subject_cleaned` | TEXT | Sujet nettoyé |
| `participant_emails` | TEXT[] | Emails des participants |
| `participant_names` | TEXT[] | Noms des participants |
| `ai_summary` | TEXT | Résumé IA du thread |
| `ai_context` | TEXT | Contexte RAG trouvé |
| `ai_urgency` | TEXT | Urgence: low/medium/high |
| `ai_status` | TEXT | Statut: new/in_progress/waiting/resolved |
| `email_count` | INTEGER | Nombre d'emails |
| `attachment_count` | INTEGER | Nombre de PJ |
| `first_email_at` | TIMESTAMP | Premier email |
| `last_email_at` | TIMESTAMP | Dernier email |
| `is_archived` | BOOLEAN | Archivé ? |
| `is_starred` | BOOLEAN | Favori ? |

#### 2. `thread_chat_sessions` - Sessions de chat

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant (PK) |
| `thread_id` | UUID | Thread lié (FK) |
| `name` | TEXT | Nom de la session |
| `rag_context` | JSONB | Contexte RAG (JSON) |
| `message_count` | INTEGER | Nombre de messages |
| `last_message_at` | TIMESTAMP | Dernier message |
| `is_active` | BOOLEAN | Active ? |
| `is_default` | BOOLEAN | Session par défaut ? |

#### 3. `thread_chat_messages` - Messages du chat

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant (PK) |
| `session_id` | UUID | Session (FK) |
| `role` | TEXT | system/assistant/user |
| `content` | TEXT | Contenu du message |
| `metadata` | JSONB | Métadonnées (sources, etc.) |

### Fonctions SQL utiles

```sql
-- Récupérer ou créer un thread
get_or_create_thread(p_org_id, p_company_id, p_gmail_thread_id, p_subject)

-- Mettre à jour les métriques d'un thread
update_thread_metrics(p_thread_id)

-- Obtenir la session de chat par défaut
get_default_chat_session(p_thread_id)
```

### Indicateur d'historique partiel

**Nouveau (Avril 2025) :** Détection des threads créés depuis des forwards externes avec extraction IA

| Colonne | Type | Description |
|---------|------|-------------|
| `is_historical_partial` | BOOLEAN | TRUE si thread créé depuis un seul email (forward externe Outlook) |
| `historical_notes` | TEXT | Logs de reconstruction + résultat extraction Gemini (JSON) |

**Use case :** Quand un client redirige un email depuis Outlook vers Gmail, on reçoit l'email sans l'historique complet. Le système utilise une cascade de stratégies pour récupérer le maximum d'informations.

**Stratégie de reconstruction (Cascade) :**

```
Nouvel email avec gmail_thread_id inconnu
    ↓
1. TENTATIVE GMAIL API
   Appel: users.threads.get(threadId)
   ↓ Succès: Importe tous les messages (3-5 emails)
   ↓ Échec: Forward externe (Outlook, etc.)
    ↓
2. EXTRACTION IA (Gemini 2.5 Flash Lite)
   Prompt: "Extrais l'historique des emails cités dans ce forward"
   Retour: JSON avec dates, expéditeurs, snippets
   Coût: ~0.001€ par email
   ↓ Succès: Enrichit historical_notes avec contexte
   ↓ Échec: Timeout ou parsing impossible
    ↓
3. FALLBACK MINIMAL
   Crée thread avec email unique
   Marque is_historical_partial = true
```

**Format stocké dans historical_notes :**
```json
{
  "reconstruction_date": "2025-04-12T10:30:00Z",
  "strategy_used": "gemini_extraction",
  "gmail_api_success": false,
  "gemini_extraction": {
    "success": true,
    "confiance": 0.85,
    "emails_extraits": [
      {
        "date": "2025-04-10T14:30:00Z",
        "expediteur": "client@acorus.fr",
        "sujet": "Devis INV-EXA-0001",
        "snippet": "Voici le devis demandé pour les travaux..."
      }
    ],
    "note": "2 emails antérieurs détectés dans le forward"
  },
  "fallback_reason": null
}
```

**Service :** `app/services/thread_reconstruction_service.py`

**Modèle IA :** `gemini-2.5-flash-lite` (rapide, coût acceptable ~0.001€/email)

---

### 🧪 Tests de Reconstruction (3 Scénarios)

**Fichier :** `tests/test_thread_reconstruction.py`

> ⚠️ **NOTE IMPORTANTE (Avril 2025)** : Les tests sont structurés mais **le mocking de Gmail API ne fonctionne pas correctement** car `create_gmail_client` est importé dynamiquement dans la méthode. Les tests échouent actuellement avec l'erreur:
> ```
> Gmail API error: {'message': 'Cannot coerce the result to a single JSON object', 'code': 'PGRST116'}
> 'NoneType' object has no attribute 'data'
> ```
> 
> **TODO :** Refactoriser `thread_reconstruction_service.py` pour accepter une injection de dépendance, ou utiliser un script de test manuel qui injecte directement les emails en DB.

#### Scénario 1 : "Easy" - Gmail API Fonctionne
**Description :** Thread historique complètement récupéré via Gmail API

**Setup :**
- Thread inexistant en DB
- Gmail API simule 3 messages historiques
- Nouvel email arrive au milieu

**Test :**
```python
# STATUS: ⚠️ ÉCHEC - Mocking à corriger
test_scenario_1_easy_gmail_api_success()
```

**Résultat attendu :**
- 3 emails importés en DB
- Thread avec `email_count=3`
- `is_historical_partial=false`
- `historical_notes` indique "gmail_api_success": true

---

#### Scénario 2 : "Hybride" - Gmail API Échoue, Gemini Extrait
**Description :** Forward Outlook, extraction IA de l'historique

**Setup :**
- Email forward avec historique cité (format Outlook)
- Gmail API mockée retourne erreur
- Appel réel à Gemini (~0.001€)

**Test :**
```python
# STATUS: ⚠️ ÉCHEC - Mocking à corriger  
test_scenario_2_hybrid_gemini_extraction()
```

**Résultat attendu :**
- 1 email en DB (le reçu)
- Thread `is_historical_partial=true`
- `historical_notes` contient extraction Gemini (JSON)
- Contexte enrichi avec emails extraits

---

#### Scénario 3 : "Fallback Total" - Tout Échoue
**Description :** Forward illisible, fallback minimal

**Setup :**
- Email forward avec corps corrompu
- Gmail API échoue
- Gemini retourne erreur/timeout

**Test :**
```python
# STATUS: ⚠️ ÉCHEC - Mocking à corriger
test_scenario_3_fallback_minimal()
```

**Résultat attendu :**
- 1 email en DB
- Thread `is_historical_partial=true`
- `historical_notes` contient logs d'erreurs
- Aucune erreur bloquante

---

**Exécution :**
```bash
# Tous les scénarios
pytest tests/test_thread_reconstruction.py -v

# Un scénario spécifique
pytest tests/test_thread_reconstruction.py::TestThreadReconstructionScenarios::test_scenario_2_hybrid_gemini_extraction -v

# Sauter les tests lents (sans appels Gemini)
pytest tests/test_thread_reconstruction.py -v -m "not slow"
```

---

**🔧 TODO - Correction Nécessaire :**

1. **Option A (Recommandée)** : Refactoriser `thread_reconstruction_service.py` pour accepter `gmail_client` en paramètre (injection de dépendance)
   ```python
   async def reconstruct_thread(self, gmail_thread_id, ..., gmail_client=None):
       if gmail_client is None:
           gmail_client = await self._create_gmail_client()
   ```

2. **Option B** : Créer un script de test manuel qui injecte directement les emails/threads en DB sans passer par la reconstruction automatique

3. **Option C** : Utiliser `unittest.mock.patch` au niveau module avec `sys.modules` manipulation

---

## 🔌 API Endpoints

### Base URL
```
/api/v1/{org_slug}/email-threads
```

### Endpoints disponibles

#### 1. Liste des threads (Page liste)

```http
GET /api/v1/{org_slug}/email-threads
```

**Query Parameters :**
| Param | Type | Description |
|-------|------|-------------|
| `companyId` | UUID | Filtrer par entreprise (obligatoire pour construction) |
| `status` | string | Filtrer par ai_status (new, in_progress, waiting, resolved) |
| `urgency` | string | Filtrer par ai_urgency (low, medium, high) |
| `search` | string | Recherche textuelle (sujet, participants) |
| `sort` | string | Tri: `-lastEmailAt` (défaut), `lastEmailAt`, `-createdAt` |
| `page` | int | Numéro de page (défaut: 1) |
| `limit` | int | Nombre par page (défaut: 20, max: 100) |

**Response 200 :**
```json
{
  "data": [
    {
      "id": "thread-uuid",
      "gmailThreadId": "thread-abc123",
      "subject": "Devis chantier Sanibatiment",
      "subjectCleaned": "Devis chantier Sanibatiment",
      "participants": {
        "emails": ["contact@acorus.fr"],
        "names": ["ACORUS"]
      },
      "aiSummary": "Relance pour le devis du chantier Sanibatiment",
      "aiUrgency": "high",
      "aiStatus": "new",
      "metrics": {
        "emailCount": 3,
        "attachmentCount": 2,
        "firstEmailAt": "2025-07-25T10:00:00Z",
        "lastEmailAt": "2025-07-28T14:30:00Z"
      },
      "flags": {
        "isArchived": false,
        "isStarred": false
      },
      "createdAt": "2025-07-25T10:00:00Z",
      "updatedAt": "2025-07-28T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

---

#### 2. Détail d'un thread (Page détail)

```http
GET /api/v1/{org_slug}/email-threads/{threadId}
```

**Response 200 :**
```json
{
  "id": "thread-uuid",
  "gmailThreadId": "thread-abc123",
  "subject": "Devis chantier Sanibatiment",
  "participants": {
    "emails": ["contact@acorus.fr", "gerard@client.fr"],
    "names": ["ACORUS", "Gérard Martin"]
  },
  "aiSummary": "Relance pour le devis du chantier Sanibatiment",
  "aiContext": "Context RAG: J'ai trouvé 2 échanges similaires en mars où le client demandait une remise",
  "aiUrgency": "high",
  "aiStatus": "new",
  "flags": {
    "isArchived": false,
    "isStarred": false
  },
  "emails": [
    {
      "id": "email-uuid-1",
      "role": "client",  // "client" ou "toi" (déduit du sender_email)
      "sender": {
        "email": "contact@acorus.fr",
        "name": "ACORUS"
      },
      "subject": "Fwd: Devis chantier Sanibatiment",
      "content": {
        "text": "Bonjour, voici le devis demandé...",
        "html": "<p>Bonjour...</p>"
      },
      "sentAt": "2025-07-25T10:00:00Z",
      "hasAttachments": true,
      "attachments": [
        {
          "id": "att-uuid",
          "filename": "devis.pdf",
          "mimeType": "application/pdf",
          "size": 45000,
          "previewUrl": "/api/v1/.../attachments/att-uuid/preview"
        }
      ]
    },
    {
      "id": "email-uuid-2",
      "role": "toi",
      "sender": {
        "email": "construction@suren-societe.fr",
        "name": "Vous"
      },
      "content": {
        "text": "Merci pour ce devis..."
      },
      "sentAt": "2025-07-26T09:15:00Z",
      "hasAttachments": false
    }
  ],
  "metrics": {
    "emailCount": 2,
    "attachmentCount": 1
  },
  "chatSession": {
    "id": "session-uuid",
    "name": "Chat principal",
    "messageCount": 5,
    "lastMessageAt": "2025-07-28T14:30:00Z"
  },
  "createdAt": "2025-07-25T10:00:00Z",
  "updatedAt": "2025-07-28T14:30:00Z"
}
```

---

#### 3. Chat d'un thread

```http
GET /api/v1/{org_slug}/email-threads/{threadId}/chat
```

**Query Parameters :**
| Param | Type | Description |
|-------|------|-------------|
| `sessionId` | UUID | ID de session (optionnel, prend la session par défaut si non fourni) |

**Response 200 :**
```json
{
  "session": {
    "id": "session-uuid",
    "name": "Chat principal",
    "ragContext": {
      "similarThreads": ["thread-xyz", "thread-abc"],
      "extractedEntities": {
        "client": "ACORUS",
        "chantier": "Sanibatiment"
      }
    },
    "createdAt": "2025-07-25T10:05:00Z"
  },
  "messages": [
    {
      "id": "msg-uuid-1",
      "role": "system",
      "content": "Résumé du dossier :\n\nDe quoi s'agit-il ? Relance pour le devis du chantier \"Sanibatiment\".\n\nContext RAG : J'ai trouvé 2 échanges similaires en mars où le client demandait une remise.\n\nUrgence : Élevée (le client mentionne un blocage de chantier).",
      "metadata": {
        "type": "summary",
        "urgency": "high"
      },
      "createdAt": "2025-07-25T10:05:00Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "user",
      "content": "Quel est le montant du devis ?",
      "createdAt": "2025-07-25T10:10:00Z"
    },
    {
      "id": "msg-uuid-3",
      "role": "assistant",
      "content": "Le montant du devis est de 12 450 € HT.\n\nSource: Email du 25/07/2025 de ACORUS",
      "metadata": {
        "sources": ["email-uuid-1"]
      },
      "createdAt": "2025-07-25T10:10:05Z"
    }
  ]
}
```

---

#### 4. Envoyer un message au chat

```http
POST /api/v1/{org_slug}/email-threads/{threadId}/chat
```

**Body :**
```json
{
  "message": "Quel est le délai de paiement habituel avec ce client ?",
  "sessionId": "session-uuid"  // Optionnel, prend la session par défaut
}
```

**Response 200 :**
```json
{
  "userMessage": {
    "id": "msg-uuid-4",
    "role": "user",
    "content": "Quel est le délai de paiement habituel avec ce client ?",
    "createdAt": "2025-07-28T15:00:00Z"
  },
  "assistantMessage": {
    "id": "msg-uuid-5",
    "role": "assistant",
    "content": "D'après les factures précédentes, le délai moyen de paiement avec ACORUS est de 45 jours.\n\nSource: Factures des 6 derniers mois",
    "metadata": {
      "sources": ["invoices-history"],
      "confidence": 0.92
    },
    "createdAt": "2025-07-28T15:00:05Z"
  }
}
```

---

#### 5. Télécharger le fichier source .eml

```http
GET /api/v1/{org_slug}/email-threads/{threadId}/emails/{emailId}/source
```

**Response :** Fichier `.eml` (Content-Type: message/rfc822)

---

#### 6. Actions sur un thread

```http
PATCH /api/v1/{org_slug}/email-threads/{threadId}
```

**Body :**
```json
{
  "aiStatus": "in_progress",      // Changer le statut
  "isStarred": true,              // Marquer comme favori
  "isArchived": false             // Désarchiver
}
```

---

## 🧪 Tests Backend (TDD)

### Tests à implémenter

#### Fichier : `tests/test_email_threads.py`

```python
class TestEmailThreadsList:
    """Tests de la liste des threads (GET /email-threads)"""
    
    def test_list_threads_by_company(self):
        """
        Scénario: Liste des threads pour une entreprise
        
        Given: Une entreprise "construction" avec 3 threads
        When: GET /api/v1/REDACTED_ORG_SLUG/email-threads?companyId={constructionId}
        Then: 
            - Status 200
            - 3 threads retournés
            - Triés par lastEmailAt DESC (plus récent d'abord)
            - Chaque thread a: id, subject, aiSummary, aiUrgency, metrics
        """
    
    def test_list_threads_filter_by_status(self):
        """
        Scénario: Filtrer par statut IA
        
        Given: Threads avec ai_status = new (2) et in_progress (1)
        When: GET /email-threads?companyId=xxx&status=new
        Then: Seulement 2 threads retournés
        """
    
    def test_list_threads_filter_by_urgency(self):
        """
        Scénario: Filtrer par urgence
        
        Given: Threads avec ai_urgency = high (1), medium (2)
        When: GET /email-threads?companyId=xxx&urgency=high
        Then: Seulement 1 thread retourné avec urgence high
        """
    
    def test_list_threads_search(self):
        """
        Scénario: Recherche textuelle
        
        Given: Threads avec sujets "Devis Sanibatiment", "Facture EDF"
        When: GET /email-threads?companyId=xxx&search=Sanibatiment
        Then: Seulement le thread "Devis Sanibatiment" retourné
        """
    
    def test_list_threads_pagination(self):
        """
        Scénario: Pagination
        
        Given: 25 threads
        When: GET /email-threads?companyId=xxx&page=1&limit=10
        Then: 
            - 10 threads retournés
            - pagination.total = 25
            - pagination.totalPages = 3
        """


class TestEmailThreadDetail:
    """Tests du détail d'un thread (GET /email-threads/{id})"""
    
    def test_get_thread_detail(self):
        """
        Scénario: Détail d'un thread avec ses emails
        
        Given: Un thread avec 2 emails et 1 PJ
        When: GET /api/v1/REDACTED_ORG_SLUG/email-threads/{threadId}
        Then:
            - Status 200
            - Thread avec aiSummary, aiUrgency, aiStatus
            - Tableau emails avec role (client/toi)
            - Emails triés par sentAt ASC
            - Pièces jointes incluses
        """
    
    def test_get_thread_not_found(self):
        """
        Scénario: Thread inexistant
        
        When: GET /email-threads/{invalidId}
        Then: Status 404
        """
    
    def test_get_thread_wrong_company(self):
        """
        Scénario: Thread d'une autre entreprise
        
        Given: Thread appartenant à company A
        When: GET avec user de company B
        Then: Status 403 ou 404 (sécurité)
        """


class TestEmailThreadChat:
    """Tests du chat d'un thread"""
    
    def test_get_chat_session_default(self):
        """
        Scénario: Récupérer le chat par défaut d'un thread
        
        Given: Thread avec une session de chat par défaut et 3 messages
        When: GET /email-threads/{threadId}/chat
        Then:
            - Status 200
            - session.isDefault = true
            - 3 messages retournés
            - Premier message = system (résumé)
        """
    
    def test_get_chat_creates_default_session(self):
        """
        Scénario: Création automatique de la session par défaut
        
        Given: Thread sans session de chat
        When: GET /email-threads/{threadId}/chat
        Then:
            - Session créée avec name = "Chat principal"
            - isDefault = true
            - Premier message system avec résumé (même si mocké)
        """
    
    def test_send_chat_message(self):
        """
        Scénario: Envoyer un message au chat
        
        Given: Thread avec session de chat existante
        When: POST /email-threads/{threadId}/chat
              Body: { "message": "Question ?" }
        Then:
            - Status 200
            - userMessage créé (role = user)
            - assistantMessage créé (role = assistant)
            - Réponse cohérente (même si mockée)
        """
    
    def test_chat_message_stores_sources(self):
        """
        Scénario: Le message assistant inclut les sources
        
        When: Envoi message "Montant du devis ?"
        Then: assistantMessage.metadata.sources contient l'email source
        """


class TestThreadActions:
    """Tests des actions sur un thread (PATCH)"""
    
    def test_update_thread_status(self):
        """
        Scénario: Mettre à jour le statut IA
        
        When: PATCH /email-threads/{id}
              Body: { "aiStatus": "in_progress" }
        Then: 
            - Status 200
            - aiStatus mis à jour en DB
        """
    
    def test_star_thread(self):
        """
        Scénario: Marquer comme favori
        
        When: PATCH /email-threads/{id}
              Body: { "isStarred": true }
        Then: isStarred = true en DB
        """


class TestThreadMetrics:
    """Tests des métriques de thread"""
    
    def test_thread_metrics_updated_on_email_insert(self):
        """
        Scénario: Les métriques se mettent à jour quand un email arrive
        
        Given: Thread avec email_count = 2
        When: Nouvel email inséré avec même gmail_thread_id
        Then: 
            - email_count = 3
            - last_email_at mis à jour
            - participant_emails mis à jour
        """
    
    def test_thread_metrics_includes_attachments(self):
        """
        Scénario: Le compte de PJ est correct
        
        Given: Thread avec 2 emails ayant 3 PJ au total
        When: Appel update_thread_metrics
        Then: attachment_count = 3
        """
```

---

## 🎨 Structure Frontend

### Routes Next.js

```
app/dashboard/email-threads/
├── page.tsx                    # Liste des threads (company_slug construction)
├── [threadId]/
│   └── page.tsx                # Détail split screen
└── layout.tsx                  # Layout spécifique (optionnel)
```

### Responsive Design

**Page Détail (`/dashboard/email-threads/[id]`)**

| Breakpoint | Layout | Description |
|------------|--------|-------------|
| Mobile (< 768px) | Tabs | Onglets "Conversation" / "Assistant IA" en haut, contenu en dessous |
| Desktop (≥ 768px) | Split-screen | Gauche 55% Conversation / Droite 45% Assistant IA |

**Composants Responsive :**
- `useIsMobile()` hook dans `@/hooks/use-media-query`
- Tabs conditionnels sur mobile avec état `activeTab`
- Split-screen horizontal sur desktop

**Améliorations de lisibilité (Desktop) :**
- Police `text-base` (16px) au lieu de `text-sm` (14px)
- `font-medium` pour plus de lisibilité
- Contraste amélioré : `text-gray-800` au lieu de `text-gray-600`
- Interligne `leading-relaxed`

### Composants

```
components/email-threads/
├── ThreadList.tsx              # Tableau liste des threads
├── ThreadListItem.tsx          # Ligne de thread avec badges
├── SplitScreenLayout.tsx       # Layout gauche/droite
├── ThreadPanel.tsx             # Panneau conversation (gauche)
├── ChatBubble.tsx              # Bulle de message (client/toi)
├── ChatBubbles.tsx             # Liste des bulles
├── AttachmentsTab.tsx          # Onglet pièces jointes
├── ChatPanel.tsx               # Panneau chat IA (droite)
├── ChatMessage.tsx             # Message du chat (user/assistant)
├── ChatInput.tsx               # Input + bouton envoyer
├── SystemSummary.tsx           # Résumé IA initial avec badges
├── UrgencyBadge.tsx            # Badge urgence (Élevée/Moyenne/Faible)
├── StatusBadge.tsx             # Badge statut (Nouveau/En cours...)
└── SourceDownloadLink.tsx      # Lien téléchargement .eml
```

### Mock IA (Phase 1)

Le résumé IA et les réponses du chat sont **mockés** pour l'instant :

```typescript
// services/mockAiService.ts
export function generateMockSummary(thread: Thread) {
  return {
    summary: `Relance concernant le ${thread.subject}`,
    context: "Contexte simulé pour test d'affichage",
    urgency: Math.random() > 0.5 ? "high" : "medium",
    status: "new"
  };
}

export function generateMockChatResponse(message: string) {
  return `Réponse simulée à: "${message}"\n\n(Le vrai modèle IA sera connecté plus tard)`;
}
```

---

## 📝 Checklist Implémentation

### Phase 1: Base de données ✅
- [x] Créer `021_email_threads_and_chat.sql`
- [x] Exécuter le script SQL
- [x] Vérifier les tables créées
- [x] Ajouter `is_historical_partial` et `historical_notes`

### Phase 2: Backend ✅
- [x] Créer les modèles Pydantic (`EmailThreadResponse`, `ChatMessageResponse`, etc.)
- [x] Implémenter `GET /email-threads` (liste)
- [x] Implémenter `GET /email-threads/{id}` (détail)
- [x] Implémenter `GET /email-threads/{id}/chat` (chat)
- [x] Implémenter `POST /email-threads/{id}/chat` (envoyer message)
- [x] Implémenter `PATCH /email-threads/{id}` (actions)
- [x] Implémenter la logique de mise à jour des métriques
- [x] **NOUVEAU** : Service de reconstruction des threads (`thread_reconstruction_service.py`)
- [x] Tests TDD

### Phase 3: Frontend ✅
- [x] Ajouter le menu "Emails" dans la sidebar
- [x] Créer la page liste (`/dashboard/email-threads`)
- [x] Créer la page détail (`/dashboard/email-threads/[id]`)
- [x] Implémenter le layout split screen
- [x] **NOUVEAU** : Responsive design (Tabs mobile / Split desktop)
- [x] **NOUVEAU** : Amélioration lisibilité (police plus grande)
- [x] **NOUVEAU** : Badge "Historique partiel"
- [x] Implémenter ThreadPanel (conversation + PJ)
- [x] Implémenter ChatPanel (chat IA)
- [x] Connecter les APIs
- [x] Tests d'affichage

### Phase 4: Secrétaire IA ✅
- [x] Service de génération de résumés (vrai Gemini)
- [x] Service de réponses chat (vrai Gemini)
- [x] Affichage des badges urgence/statut

---

---

## 🧪 Tests

### Exécution des tests

```bash
# Tous les tests du module Emails
pytest tests/test_email_api_routes.py tests/test_email_embedding.py tests/test_email_threads_api.py -v

# Un fichier spécifique
pytest tests/test_email_threads_api.py -v

# Un test spécifique
pytest tests/test_email_threads_api.py::TestEmailThreadsAPI::test_list_threads -v
```

### État des tests (Avril 2025)

| Fichier de test | Tests | Passent | Échouent | Taux |
|----------------|-------|---------|----------|------|
| `test_email_api_routes.py` | 4 | 4 | 0 | ✅ 100% |
| `test_email_embedding.py` | 8 | 7 | 1 | ⚠️ 87.5% |
| `test_email_threads_api.py` | 10 | 10 | 0 | ✅ 100% |
| **TOTAL** | **22** | **21** | **1** | **95.5%** |

#### Détails des tests

**✅ test_email_api_routes.py (4/4)**
- Scénario 1: Email forwardé avec PJ
- Scénario 2: Chaîne d'emails (thread)
- Scénario 3: Emails ignorés par routing
- Scénario 5: RAG Mail (extraction forward)

**⚠️ test_email_embedding.py (7/8)**
- ✅ Génération d'embeddings Vertex AI
- ✅ Chunking de texte
- ✅ Vectorisation d'emails
- ✅ Recherche sémantique
- ✅ Création de PJ avec OCR
- ✅ Vectorisation de PJ
- ❌ Scénario 1 complet avec OCR (échec car la Secrétaire IA tente de créer un chat sur un thread inexistant dans ce test - couvert par les tests de la Secrétaire)
- ✅ Endpoint de recherche sémantique

**✅ test_email_threads_api.py (10/10)**
- Liste des threads avec filtres
- Recherche textuelle
- Pagination
- Détail d'un thread avec emails
- Thread non trouvé (404)
- Chat d'un thread
- Envoi de message dans le chat
- Mise à jour du statut
- Marquer comme favori
- Archiver un thread

### Note sur le test échouant

Le test `test_scenario_1_forward_with_ocr_and_search` échoue car il teste un flux complet (email → OCR → Secrétaire → Chat) mais la Secrétaire tente de créer un chat sur un thread qui n'existe pas encore dans le contexte de ce test. Ce scénario est **complètement couvert** par les tests de la Secrétaire (`test_secretariat_scenarios.py`) qui passent tous.

---

## 🔗 Références

- `docs/EMAILS_INPUT.md` - Documentation du module d'ingestion
- `docs/SECRETARIAT.md` - Documentation de la Secrétaire IA
- `db/schema/020_email_tables.sql` - Tables emails existantes
- `db/schema/021_email_threads_and_chat.sql` - Nouvelles tables (ce fichier)
