# Construction Invoicing - Construction Company

## Overview

Invoicing module for the construction company within the SurenSaaS organization.

## Features

### Site supervisors (via Telegram)
- **Invoice submission**: Photo or PDF from mobile
- **Tracking**: Approval/rejection notification

### Managers (via Web App)
- **Dashboard**: Invoice list with filters
- **Validation**: Accept/reject with reason
- **History**: Full traceability

### Accountant (via Web App)
- **Export**: Validated invoices
- **Processing**: Change status to "in processing"

## Data structure

### Table `invoices`

```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(id),
    company_id UUID REFERENCES companies(id),
    
    -- Supplier
    supplier_name TEXT NOT NULL,
    supplier_address TEXT,
    supplier_siret TEXT,
    
    -- Amounts
    amount_ht DECIMAL(12, 2),
    amount_ttc DECIMAL(12, 2) NOT NULL,
    vat_amount DECIMAL(12, 2),
    vat_rate DECIMAL(5, 2),
    
    -- Dates
    invoice_date DATE,
    due_date DATE,
    
    -- Details
    description TEXT,
    items JSONB,  -- [{"label": "", "qty": 1, "unit_price": 100}]
    
    -- Media
    original_file_url TEXT,
    thumbnail_url TEXT,
    
    -- Workflow
    status invoice_status,
    
    -- Traceability
    created_by UUID REFERENCES users(id),
    created_by_telegram BOOLEAN DEFAULT false,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMP,
    rejection_reason TEXT,
    
    -- Metadata
    ocr_data JSONB,
    metadata JSONB,
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    updated_by UUID REFERENCES users(id)
);
```

### Status

| Status | French | Description |
|--------|----------|-------------|
| `brouillon` | Draft | Created via OCR, data pending validation |
| `en_attente_validation` | Pending validation | Submitted by site supervisor |
| `validee` | Validated | Approved by manager |
| `rejetee` | Rejected | Refused by manager |
| `en_traitement_comptable` | In accounting processing | Forwarded to accounting |
| `archivee` | Archived | Processing finished |

### Table `invoice_status_history`

Complete audit of all status changes:
- Who changed it
- When
- From which status to which status
- Reason (if rejected)

## API Endpoints

### List invoices
```http
GET /api/v1/{org}/companies/{company_id}/invoices
Authorization: Bearer {jwt}

Query params:
  - status: filter by status
  - limit: number of results (default: 50)
  - offset: pagination (default: 0)
```

### Create an invoice
```http
POST /api/v1/{org}/companies/{company_id}/invoices
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "supplier_name": "Supplier Corp",
  "amount_ttc": 1200.00,
  "amount_ht": 1000.00,
  "vat_rate": 20.0,
  "description": "Construction materials"
}
```

### Validate/Reject
```http
POST /api/v1/{org}/companies/{company_id}/invoices/{id}/validate
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "action": "validate"  // or "reject"
  "reason": "Rejection reason"  // if reject
}
```

### History
```http
GET /api/v1/{org}/companies/{company_id}/invoices/{id}/history
Authorization: Bearer {jwt}
```

## Required capabilities

| Action | Capability |
|--------|------------|
| View invoices | `construction:facturation:read` |
| Create invoice | `construction:facturation:write` |
| Modify invoice (draft) | `construction:facturation:write` |
| Validate/Reject | `construction:facturation:validate` |
| Delete | `construction:facturation:delete` |

**Note**: Admins bypass all restrictions.

## Complete workflow

### 1. Site supervisor submits invoice (Telegram)

```
Telegram Bot
    ↓
Webhook Handler
    ↓
Invoice Upload Service
    ↓
1. Verify user is authorized
2. OCR (stub)
3. Create invoice → status='brouillon'
4. Notify managers
```

### 2. Manager validates (Web App)

```
Invoice Dashboard
    ↓
Click "Validate"
    ↓
POST /validate
    ↓
Status → 'validee'
    ↓
Notify site supervisor
```

### 3. Rejection with reason

```
Click "Reject"
    ↓
Reason modal
    ↓
POST /validate {action: 'reject', reason: '...'}
    ↓
Status → 'rejetee'
    ↓
Notify site supervisor with reason
```

## Web Interface

### Frontend Routes

```
/{org}/construction/invoices
  → List with filters

/{org}/construction/invoices/{id}
  → Detail with validate/reject actions

/{org}/construction/invoices/{id}/edit
  → Editing (if draft)
```

### Suggested components

```typescript
// InvoiceList.tsx
// - Table with sorting/filters
// - Colored status badges
// - Quick actions

// InvoiceDetail.tsx  
// - Invoice display
// - Validate/reject buttons
// - History timeline

// InvoiceForm.tsx
// - Edit form
// - Data validation
```

## Database - Initialization

```sql
-- Create the construction company
INSERT INTO companies (org_id, slug, name, description)
VALUES (
    'your-org-uuid',
    'construction',
    'Construction',
    'Construction site and invoice management'
);

-- Create the capabilities
INSERT INTO organization_capabilities (org_id, capability_code, description, resource, action)
VALUES 
    ('your-org-uuid', 'construction:facturation:read', 'View invoices', 'construction', 'read'),
    ('your-org-uuid', 'construction:facturation:write', 'Create/modify invoices', 'construction', 'write'),
    ('your-org-uuid', 'construction:facturation:validate', 'Validate/reject invoices', 'construction', 'validate'),
    ('your-org-uuid', 'construction:facturation:delete', 'Delete invoices', 'construction', 'delete');

-- Assign capabilities to users (example)
INSERT INTO user_capabilities (user_id, org_id, capability_code, granted_by)
VALUES 
    ('user-uuid-supervisor', 'your-org-uuid', 'construction:facturation:write', 'admin-uuid'),
    ('user-uuid-manager', 'your-org-uuid', 'construction:facturation:validate', 'admin-uuid');
```

## Security

### RLS Policies

All tables have RLS policies:
- Users only see their own org
- Capabilities checked for modifications
- Admins can do everything

### Business validation

- Invoice in `validee` or `archivee` → not modifiable
- Only the creator can modify a draft
- Validation requires a capability or the admin role

## Monitoring

### Suggested KPIs

```sql
-- Number of invoices by status
SELECT status, COUNT(*) 
FROM invoices 
WHERE org_id = 'uuid'
GROUP BY status;

-- Average validation time
SELECT AVG(validated_at - created_at)
FROM invoices
WHERE status = 'validee';

-- Rejection rate
SELECT 
    COUNT(*) FILTER (WHERE status = 'rejetee') * 100.0 / COUNT(*) as reject_rate
FROM invoices;
```

## Future development

### Planned features

1. **Accounting export**: PDF/Excel of validated invoices
2. **Dashboard**: Stats, graphs
3. **Due date reminders**: Notifications for invoices to pay
4. **Bank integration**: Automatic statement

### Agentic OCR

Structure ready in `app/agents/invoice_ocr/`.
To implement:
- Text extraction (Tesseract/API)
- Intelligent parsing
- Confidence validation

## References

- API Contract: `/openapi/api.yaml`
- Telegram Bot: `docs/TELEGRAM_BOT.md`
- Capabilities: `docs/CAPABILITIES.md`
