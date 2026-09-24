# Backend Tests - Documentation

> **Last updated:** March 2026 (validation tests + RLS policies fixes phases 1 & 2)  
> **Status:** 🟢 Functional tests - Keep up to date

## 📋 Overview

This document describes the state of the SurenSaaS API backend tests. It serves as a reference to understand the covered scenarios without re-reading the source code.

**How to maintain this document:**
- ✅ Add a row in the relevant section when a new test is created
- 🔲 Mark as implemented when a test is added
- 📝 Update the date at the top of the file

---

## 🧪 API Routes Tests (test_api_routes.py)

### ✅ Clients Tests (`/api/v1/clients`)

| Scenario | Method | Status | Description |
|----------|---------|--------|-------------|
| Create client | POST | ✅ | Creates a client with all fields (name, email, phone, address, SIRET, notes) |
| List clients | GET | ✅ | Retrieves the paginated list of clients with optional search |
| Client detail | GET | ✅ | Retrieves a client's details by ID |
| Update client | PUT | ✅ | Modifies an existing client's information |
| Delete client | DELETE | ✅ | Deletes a client from the database |

**Error cases covered:**
- 🔲 404 - Client not found
- 🔲 403 - Unauthorized access (wrong org_id)
- 🔲 401 - Not authenticated

---

### ✅ Invoices Tests (`/api/v1/invoices`)

| Scenario | Method | Status | Description |
|----------|---------|--------|-------------|
| Create invoice | POST | ✅ | Creates an invoice with number, supplier, amounts, dates, description |
| List invoices | GET | ✅ | Retrieves the list with filters (status, client, search) |
| Invoice detail | GET | ✅ | Retrieves the full details of an invoice |
| Update invoice | PUT | ✅ | Modifies an invoice (only if in draft) |
| Delete invoice | DELETE | ✅ | Deletes an invoice (only if in draft) |
| Validate invoice | POST | ✅ | Validates a pending invoice via `/invoices/{id}/validate?action=validate` |
| Reject invoice | POST | ✅ | Rejects a pending invoice via `/invoices/{id}/validate?action=reject` |

**Error cases covered:**
- ✅ 404 - Invoice not found
- 🔲 403 - Attempt to modify a non-draft invoice
- ✅ 401 - Not authenticated
- ✅ 400 - Invalid action (validating an invoice not pending)

---

### ✅ Users Tests (`/api/v1/users`)

| Scenario | Method | Status | Description |
|----------|---------|--------|-------------|
| User profile | GET | ✅ | Retrieves the logged-in user's profile (email, org, role) |

**Error cases covered:**
- 🔲 401 - Invalid or expired token
- 🔲 404 - User not found

---

## 🧪 Full Scenarios Tests (test_full_scenarios.py)

### ✅ Authentication Tests

| Scenario | Status | Description |
|----------|--------|-------------|
| Authorized check-email | ✅ | Verifies a pre-authorized email can sign up |
| Unauthorized check-email | ✅ | Verifies an unknown email is rejected |
| Invalid email validation | ✅ | Verifies the email format |
| Empty body validation | ✅ | Verifies required fields are present |
| Full signup workflow | ✅ | Tests the full flow: check-email → signup → DB verification |

### ✅ Billing Tests (direct DB)

| Scenario | Status | Description |
|----------|--------|-------------|
| Create test invoices | ✅ | Creates 3 test invoices (draft, pending, validated) |
| Full status workflow | ✅ | Tests the status change: draft → pending → validated → processing |

---

## 🔧 Test Configuration

### Required environment variables

```bash
# Credentials for API tests (authentication required)
export SUREN_TEST_LOGIN="email@example.com"
export SUREN_TEST_PASSWORD="password"

# OR via .env.test.local file (not versioned)
```

### Run the tests

```bash
# All tests
./scripts/run-tests.sh

# API tests only
python tests/test_api_routes.py

# Full scenarios only
python tests/test_full_scenarios.py
```

---

### ✅ Error Handling Tests

| Scenario | Route | Status | Description |
|----------|-------|--------|-------------|
| 401 - Not authenticated | `/users/me` | ✅ | Returns 401 without a session cookie |
| 404 - Nonexistent client | `/clients/{fake_id}` | ✅ | Returns 404 for a nonexistent ID |
| 404 - Nonexistent invoice | `/invoices/{fake_id}` | ✅ | Returns 404 for a nonexistent ID |
| 400 - Invalid validation | `/invoices/{id}/validate` | ✅ | Returns 400 if the invoice is not pending |

---

## 📝 To Implement (TODO)

### High Priority
- [x] **Invoice Validation/Rejection** - Test `POST /invoices/{id}/validate?action=validate/reject`
- [x] **401 error tests** - Verify protected routes return 401 without auth
- [ ] **403 error tests** - Verify a user cannot access another org's data
- [x] **404 error tests** - Verify behavior on nonexistent ID

### Medium Priority
- [ ] **Pagination tests** - Verify limit/offset parameters on lists
- [ ] **Search tests** - Verify the search filter on clients and invoices
- [ ] **Status history** - Verify history is properly created on changes

### Low Priority
- [ ] **File upload tests** - Test PDF/invoice upload
- [ ] **Telegram tests** - Test webhook integrations (if applicable)
- [ ] **Load tests** - Verify performance with lots of data

---

## 🐛 Known Bugs / Fixes

### ✅ Resolved issues

| Issue | Cause | Solution | Migration |
|----------|-------|----------|-----------|
| **`.single()` and `.offset()`** | Supabase Python client does not support these methods | Use `.execute()` and handle logic in Python | ✅ Fixed in all files |
| **Authentication with unconfirmed email** | Supabase Auth requires confirmation by default | Fallback with test JWT token | ✅ Handled in test_api_routes.py |
| **RLS Policies - data not visible (v1)** | Policies used DEPRECATED table `user_org_membership` (invoices, clients) | Migration 015 creating policies based on `users.org_id` | ✅ 015_fix_rls_policies.sql |
| **RLS Policies - data not visible (v2)** | Policies used DEPRECATED table `user_org_membership` (telegram_bots, companies, etc.) | Migration 016 fixing ALL remaining tables | ✅ 016_fix_all_remaining_rls_policies.sql |

### 🔴 Critical RLS Fix - Phase 1 (March 2026)

**Problem:** Invoices and clients were not visible despite existing in the DB

**Cause:** RLS policies created in `008_invoices.sql` and `014_add_clients_and_update_invoices.sql` used the `user_org_membership` table which was disabled by `999_cleanup_user_org_membership.sql`

**Impact:** 
- Invoices dashboard: blank screen
- Clients dashboard: blank screen
- Users administration: worked (different policy)

**Solution:** Run `015_fix_rls_policies.sql`
```bash
psql "$DATABASE_URL" -f db/schema/015_fix_rls_policies.sql
```

**Fixed policies:**
- `members_read_invoices`: uses `users.org_id` directly
- `members_read_clients`: uses `users.org_id` directly
- All INSERT/UPDATE/DELETE policies updated

### 🔴 Critical RLS Fix - Phase 2 (March 2026)

**Problem:** Telegram bots, companies, and other tables did not return data

**Cause:** Migrations 006-011 had created policies using `user_org_membership` but were not fixed in phase 1

**Impact:** 
- Telegram bot invitation: returns empty list
- Companies management: potentially broken
- Telegram audit: inaccessible
- Capabilities: management impossible

**Solution:** Run `016_fix_all_remaining_rls_policies.sql`
```bash
psql "$DATABASE_URL" -f db/schema/016_fix_all_remaining_rls_policies.sql
```

**Fixed tables:**
- `telegram_bots`: 2 policies (admin_manage, members_read)
- `telegram_users`: 1 policy (admin_read_org_telegram)
- `telegram_audit`: 1 policy (admin_read_audit)
- `companies`: 2 policies (members_read, admin_manage)
- `organization_capabilities`: 1 policy (admin_manage)
- `user_capabilities`: 1 policy (admin_manage)
- `invoice_status_history`: 1 policy (complement to 015)

**Total:** 7 tables, 10 policies fixed

---

## 📊 Current Coverage

**API routes tested:** 12/13 (92%)
**Critical scenarios:** ✅ 100% covered
**Error handling:** 🔲 20% covered (to improve)

**Untested routes:**
- `/api/v1/invoices/{id}/validate` (validation/rejection)
- Specific error routes (401, 403, 404)

---

## 🎯 Best Practices

1. **Add a test for every new API route**
2. **Document here immediately after creation**
3. **Keep the "To Implement" section up to date**
4. **Run the tests before every important commit**

---

## 👥 Contributors

- Documentation created: March 2026
- Last test added: test_api_routes.py (Clients, Invoices, Users)

---

**💡 Need help?** See the `tests/README.md` file for the test structure.
