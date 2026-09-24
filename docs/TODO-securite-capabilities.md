# TODO-Security-Capabilities.md

## 📊 Analysis of the current state of the security and capabilities system

**Date**: 2026-03-27  
**Context**: Invoice access problem (401 Unauthorized) and lack of capabilities management

---

## 🔴 Identified problems

### 1. 401 access problem - Missing session cookie

**Observed error**:
```
WARNING | auth:92 | Missing session cookie
Request GET /api/v1/invoices/{id} - 401
```

**File affected**: `surenSaasBack/app/api/invoices.py:69`

**Current code**:
```python
def check_user_org_access(request: Request, org_id: str):
    user = get_current_user_from_cookie(request)
    if user["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Access not authorized")
    return user
```

**Analysis**:
- The function only verifies that the user belongs to the org
- It does NOT check the capabilities (e.g.: `facture:read`)
- The cookie may be absent or expired
- The problem probably comes from cross-domain cookie handling (frontend vs backend)

---

### 2. Capabilities System - Detailed state

#### ✅ What is implemented

**Database tables** (Migration 006):
- `organization_capabilities`: List of capabilities available per organization
- `user_capabilities`: Capability → user assignment
- View `user_active_capabilities`: Aggregated view of active capabilities

**Backend - Services** (`app/services/admin_service.py`):
- `get_organization_capabilities()` - List of org capabilities
- `get_user_capabilities()` - List of user capabilities
- `assign_capability_to_user()` - Assign a capability
- `revoke_user_capability()` - Revoke a capability

**Backend - API** (`app/api/admin.py`):
```python
GET  /organization-capabilities      # List of org capabilities
POST /organization-capabilities      # Create a capability
GET  /users/{id}/capabilities        # List of user capabilities
POST /users/{id}/capabilities        # Assign a capability
PUT  /users/{id}/capabilities        # Batch update
DELETE /users/{id}/capabilities/{code}  # Revoke
```

#### ❌ What is missing

**1. Middleware/Decorator for capability verification**

Currently no mechanism to protect API routes with capabilities.

**2. Capabilities management page (Frontend)**

Link exists in `page.tsx:420` but the page is not implemented.

**3. Frontend menu driven by capabilities**

Currently the menu is static, no capability check.

---

### 3. Supabase RLS - Problems

The RLS policies use `auth.uid()` which does not work with the service key (backend).

**Temporary solution**: Disable RLS for prototyping
**Production solution**: Replace RLS with capability checks on the backend

---

### 4. Missing line_items

**Problem**: Invoice items extracted by Gemini are not stored

**Cause**: `ExtractedInvoiceData` does not retrieve the line_items (service.py lines 270-296)

**Table invoices**: `items` field = `'[]'` (empty array)

**Solution**:
1. Modify `ExtractedInvoiceData` to include `line_items`
2. Modify `_perform_ocr` to extract the line_items
3. Modify `_create_draft_invoice` to store the items

---

## 🛠️ Recommended immediate actions

### 1. Disable RLS (Prototyping)

**File**: `db/scripts/disable_rls_prototyping.sql`

```sql
-- Script to disable RLS temporarily (PROTOTYPING ONLY)
ALTER TABLE invoices DISABLE ROW LEVEL SECURITY;
ALTER TABLE clients DISABLE ROW LEVEL SECURITY;
ALTER TABLE companies DISABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_users DISABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_bots DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_capabilities DISABLE ROW LEVEL SECURITY;
ALTER TABLE organization_capabilities DISABLE ROW LEVEL SECURITY;
```

### 2. Fix the invoices.py line 176 bug

Replace `return result.data[0] if result.data and len(result.data) > 0 else update_data` 
with `return result.data[0]`

### 3. Add line_items to the extraction

Modify `_perform_ocr` to retrieve and store the line_items extracted by Gemini.

---

## 📋 Full implementation plan

### Phase 1: Immediate fixes (1-2 days)

- [ ] Fix the line 176 bug in `invoices.py`
- [ ] Add line_items to the OCR extraction
- [ ] Temporarily disable RLS
- [ ] Investigate the 401 cookie problem

### Phase 2: Capabilities implementation (3-5 days)

- [ ] Create the `require_capability` decorator
- [ ] Apply it to the existing API routes
- [ ] Create the frontend capabilities management page
- [ ] Implement the `useCapabilities` hook
- [ ] Drive the menu by capabilities

### Phase 3: Hardening (2-3 days)

- [ ] Audit of all routes
- [ ] Permission tests
- [ ] Documentation for admins

---

**Recommended next action**: Run the `disable_rls_prototyping.sql` script to unblock immediate access.

---

## ✅ Fixes applied on 2026-03-27

### 1. Expired cookie handling - Auto redirect to login

**Problem**: When the session cookie expires, the user stays on the page and gets 401 errors

**Solution**:
- Creation of `AuthenticationError` in `auth.py` with a `redirect_to_login` flag
- Addition of specific headers (`X-Auth-Redirect`, `X-Auth-Error`) in 401 responses
- Modification of the API proxy (`route.ts`) to detect these headers and redirect
- Creation of the `useApiErrorHandler.ts` hook to handle errors on the client side
- Creation of the Next.js middleware (`middleware.ts`) to check the cookie before accessing protected routes

**Modified files**:
- `surenSaasBack/app/api/auth.py` - Custom exception and error handling
- `surenSaasBack/app/api/invoices.py` - Handling of AuthenticationErrors
- `surenSaasFront/app/api/v1/[[...path]]/route.ts` - Detection of auth errors
- `surenSaasFront/middleware.ts` - Cookie check (NEW)
- `surenSaasFront/hooks/useApiErrorHandler.ts` - Error handling hook (NEW)

### 2. Creation of the invoice_items table

**SQL Migration**: `db/schema/018_create_invoice_items_table.sql`

**Structure**:
```sql
CREATE TABLE invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity DECIMAL(10, 2),
    unit_price DECIMAL(10, 2),
    total_ht DECIMAL(10, 2),
    vat_rate DECIMAL(5, 2),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Modified files**:
- `surenSaasBack/app/services/telegram/upload_invoice/service.py`:
  - Addition of the `line_items` field in `ExtractedInvoiceData`
  - Extraction of line_items from the Gemini response
  - Insertion of items in `invoice_items` during invoice creation
- `surenSaasBack/app/api/invoices.py`:
  - Addition of the `InvoiceItem` model in the Pydantic schemas
  - Modification of `InvoiceCreate` and `InvoiceUpdate` to accept items
  - Modification of `InvoiceResponse` to return the items
  - Modification of `create_invoice` to create the items
  - Modification of `get_invoice` to retrieve the items
  - Modification of `update_invoice` to update the items
  - Fix of the line 174 and 197 bug (`else update_data` → correct code)

### 3. OCR service modifications

**Changes in `_perform_ocr`**:
```python
# Extraction of line_items from Gemini
line_items = extracted.get("line_items", [])
if line_items:
    logger.info(f"📋 {len(line_items)} detail line(s) extracted")

extracted_data = ExtractedInvoiceData(
    # ... existing fields ...
    line_items=line_items,  # NEW
    raw_data={...}
)
```

**Changes in `_create_draft_invoice`**:
```python
# Insert the detail lines (items) if present
if extracted_data.line_items and len(extracted_data.line_items) > 0:
    items_data = []
    for idx, item in enumerate(extracted_data.line_items):
        item_data = {
            'invoice_id': invoice_id,
            'org_id': org_id,
            'description': item.get('description', ''),
            'quantity': item.get('quantity'),
            'unit_price': item.get('unit_price'),
            'total_ht': item.get('total_ht'),
            'vat_rate': item.get('vat_rate'),
            'sort_order': idx
        }
        items_data.append(item_data)
    
    self.supabase.table('invoice_items').insert(items_data).execute()
```

---

## 🧪 Recommended tests

### Test 1: Expired cookie
1. Log in
2. Wait for the cookie to expire (or delete it manually)
3. Click on an invoice
4. Verify the redirect to `/login?error=session_expired`

### Test 2: OCR extraction with items
1. Send a PDF invoice via Telegram
2. Verify the items are extracted (backend log)
3. Verify the items are stored in the DB:
   ```sql
   SELECT * FROM invoice_items WHERE invoice_id = '...';
   ```
4. Verify the items appear in the API:
   ```bash
   curl /api/v1/invoices/{id}?org_id=...
   ```

### Test 3: Items CRUD
1. Create an invoice with items via the API
2. Verify the created items
3. Modify the invoice with new items
4. Verify the old items are replaced

---

## 📋 SQL scripts to run

### 1. Create the invoice_items table
```bash
# Run in the Supabase Dashboard → SQL Editor
cat db/schema/018_create_invoice_items_table.sql
```

### 2. Temporarily disable RLS (if blocking)
```bash
# Run in case of access problems
cat db/scripts/disable_rls_prototyping.sql
```

---

## 🎯 Suggested next steps

1. **Testing**: Verify everything works correctly
2. **Deployment**: Deploy backend and frontend
3. **Documentation**: Update the user documentation
4. **Future**: Implement capability checks in the API routes
