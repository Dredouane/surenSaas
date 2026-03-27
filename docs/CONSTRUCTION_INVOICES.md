# Facturation Chantiers - Entreprise Construction

## Vue d'ensemble

Module de facturation pour l'entreprise de construction au sein de l'organisation SurenSaaS.

## Fonctionnalités

### Conducteurs de travaux (via Telegram)
- **Envoi facture**: Photo ou PDF depuis mobile
- **Suivi**: Notification validation/rejet

### Gérants (via Web App)
- **Dashboard**: Liste des factures avec filtres
- **Validation**: Accepter/rejeter avec raison
- **Historique**: Traçabilité complète

### Comptable (via Web App)
- **Export**: Factures validées
- **Traitement**: Changement status "en traitement"

## Structure des données

### Table `invoices`

```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id),
    company_id UUID REFERENCES companies(id),
    
    -- Fournisseur
    supplier_name TEXT NOT NULL,
    supplier_address TEXT,
    supplier_siret TEXT,
    
    -- Montants
    amount_ht DECIMAL(12, 2),
    amount_ttc DECIMAL(12, 2) NOT NULL,
    vat_amount DECIMAL(12, 2),
    vat_rate DECIMAL(5, 2),
    
    -- Dates
    invoice_date DATE,
    due_date DATE,
    
    -- Détails
    description TEXT,
    items JSONB,  -- [{"label": "", "qty": 1, "unit_price": 100}]
    
    -- Médias
    original_file_url TEXT,
    thumbnail_url TEXT,
    
    -- Workflow
    status invoice_status,
    
    -- Traçabilité
    created_by UUID REFERENCES users(id),
    created_by_telegram BOOLEAN DEFAULT false,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMP,
    rejection_reason TEXT,
    
    -- Métadonnées
    ocr_data JSONB,
    metadata JSONB,
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    updated_by UUID REFERENCES users(id)
);
```

### Status

| Status | Français | Description |
|--------|----------|-------------|
| `brouillon` | Brouillon | Créée via OCR, données à valider |
| `en_attente_validation` | En attente de validation | Soumise par conducteur |
| `validee` | Validée | Approuvée par gérant |
| `rejetee` | Rejetée | Refusée par gérant |
| `en_traitement_comptable` | En traitement comptable | Transmise compta |
| `archivee` | Archivée | Traitement terminé |

### Table `invoice_status_history`

Audit complet de tous les changements de status:
- Qui a changé
- Quand
- De quel status vers quel status
- Raison (si rejet)

## API Endpoints

### Lister les factures
```http
GET /api/v1/{org}/companies/{company_id}/invoices
Authorization: Bearer {jwt}

Query params:
  - status: filtre par status
  - limit: nombre de résultats (default: 50)
  - offset: pagination (default: 0)
```

### Créer une facture
```http
POST /api/v1/{org}/companies/{company_id}/invoices
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "supplier_name": "Fournisseur SA",
  "amount_ttc": 1200.00,
  "amount_ht": 1000.00,
  "vat_rate": 20.0,
  "description": "Matériaux de construction"
}
```

### Valider/Rejeter
```http
POST /api/v1/{org}/companies/{company_id}/invoices/{id}/validate
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "action": "validate"  // ou "reject"
  "reason": "Raison du rejet"  // si reject
}
```

### Historique
```http
GET /api/v1/{org}/companies/{company_id}/invoices/{id}/history
Authorization: Bearer {jwt}
```

## Capabilities requises

| Action | Capability |
|--------|------------|
| Voir factures | `construction:facturation:read` |
| Créer facture | `construction:facturation:write` |
| Modifier facture (brouillon) | `construction:facturation:write` |
| Valider/Rejeter | `construction:facturation:validate` |
| Supprimer | `construction:facturation:delete` |

**Note**: Les admins bypassent toutes les restrictions.

## Workflow complet

### 1. Conducteur envoie facture (Telegram)

```
Telegram Bot
    ↓
Webhook Handler
    ↓
Invoice Upload Service
    ↓
1. Vérifier user autorisé
2. OCR (coquille)
3. Créer facture → status='brouillon'
4. Notifier gérants
```

### 2. Gérant valide (Web App)

```
Dashboard Factures
    ↓
Click "Valider"
    ↓
POST /validate
    ↓
Status → 'validee'
    ↓
Notif conducteur
```

### 3. Rejet avec raison

```
Click "Rejeter"
    ↓
Modal raison
    ↓
POST /validate {action: 'reject', reason: '...'}
    ↓
Status → 'rejetee'
    ↓
Notif conducteur avec raison
```

## Interface Web

### Routes Frontend

```
/{org}/construction/invoices
  → Liste avec filtres

/{org}/construction/invoices/{id}
  → Détail avec actions validate/reject

/{org}/construction/invoices/{id}/edit
  → Édition (si brouillon)
```

### Composants suggérés

```typescript
// InvoiceList.tsx
// - Tableau avec tri/filtres
// - Badges status colorés
// - Actions rapides

// InvoiceDetail.tsx  
// - Visualisation facture
// - Boutons validate/reject
// - Historique timeline

// InvoiceForm.tsx
// - Formulaire édition
// - Validation données
```

## Base de données - Initialisation

```sql
-- Créer l'entreprise construction
INSERT INTO companies (org_id, slug, name, description)
VALUES (
    'votre-org-uuid',
    'construction',
    'Construction',
    'Gestion des chantiers et factures'
);

-- Créer les capabilities
INSERT INTO organization_capabilities (org_id, capability_code, description, resource, action)
VALUES 
    ('votre-org-uuid', 'construction:facturation:read', 'Voir les factures', 'construction', 'read'),
    ('votre-org-uuid', 'construction:facturation:write', 'Créer/modifier factures', 'construction', 'write'),
    ('votre-org-uuid', 'construction:facturation:validate', 'Valider/rejeter factures', 'construction', 'validate'),
    ('votre-org-uuid', 'construction:facturation:delete', 'Supprimer factures', 'construction', 'delete');

-- Assigner capabilities aux users (exemple)
INSERT INTO user_capabilities (user_id, org_id, capability_code, granted_by)
VALUES 
    ('user-uuid-conducteur', 'votre-org-uuid', 'construction:facturation:write', 'admin-uuid'),
    ('user-uuid-gerant', 'votre-org-uuid', 'construction:facturation:validate', 'admin-uuid');
```

## Sécurité

### RLS Policies

Toutes les tables ont des RLS policies:
- Users ne voient que leur org
- Capabilities vérifiées pour modifications
- Admins peuvent tout faire

### Validation métier

- Facture en `validee` ou `archivee` → non modifiable
- Seul créateur peut modifier brouillon
- Validation nécessite capability ou rôle admin

## Monitoring

### KPIs suggérés

```sql
-- Nombre de factures par status
SELECT status, COUNT(*) 
FROM invoices 
WHERE org_id = 'uuid'
GROUP BY status;

-- Temps moyen validation
SELECT AVG(validated_at - created_at)
FROM invoices
WHERE status = 'validee';

-- Taux rejet
SELECT 
    COUNT(*) FILTER (WHERE status = 'rejetee') * 100.0 / COUNT(*) as reject_rate
FROM invoices;
```

## Développement futur

### Fonctionnalités planifiées

1. **Export comptable**: PDF/Excel des factures validées
2. **Tableau de bord**: Stats, graphs
3. **Rappels échéances**: Notifications factures à payer
4. **Intégration banque**: Relevé automatique

### OCR Agentic

Structure prête dans `app/agents/invoice_ocr/`.
À implémenter:
- Extraction texte (Tesseract/API)
- Parsing intelligent
- Validation confiance

## Références

- API Contract: `/openapi/api.yaml`
- Bot Telegram: `docs/TELEGRAM_BOT.md`
- Capabilities: `docs/CAPABILITIES.md`
