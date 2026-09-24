# SQL Migrations - Documentation

## Migration execution order

Migrations must be executed in numerical order. Here is the full sequence:

### Phase 1 : Base structure (001-007)
1. `001_organizations.sql` - Organizations table
2. `002_users.sql` - Users table with org_id and role
3. `003_pre_authorized_emails.sql` - Pre-authorized emails
4. `004_user_org_membership.sql` - Link table (DEPRECATED after 999)
5. `005_auth_triggers.sql` - Triggers for auth.users
6. `006_companies.sql` - Companies table
7. `007_pre_authorized_emails_unique.sql` - Unique constraint on emails

### Phase 2 : Business (008-014)
8. `008_invoices.sql` - Invoices table + initial RLS
9. `009_invoices_amount_precision.sql` - Amount precision
10. `010_invoices_add_metadata.sql` - Metadata columns
11. `011_telegram_bots.sql` - Telegram configuration
12. `012_invoice_status_history.sql` - Status history
13. `013_invoices_add_company_id.sql` - Link to companies
14. `014_add_clients_and_update_invoices.sql` - Clients table + client_id column

### Phase 3 : Critical fixes (015-016)
15. **`015_fix_rls_policies.sql`** - ⚠️ **IMPORTANT** - RLS policies fix (v1)
    - Fixes the policies for `invoices`, `clients`, `invoice_status_history`
    - Updates them to use `users.org_id` directly
    - **Run this if invoices/clients do not appear in the dashboard**

16. **`016_fix_all_remaining_rls_policies.sql`** - ⚠️ **IMPORTANT** - Complete RLS fix
    - Fixes ALL remaining tables: `telegram_bots`, `telegram_users`, `telegram_audit`
    - Also fixes: `companies`, `organization_capabilities`, `user_capabilities`
    - Updates them to use `users.org_id` directly
    - **Run after 015 if other tables do not work (Telegram bots, companies, etc.)**

### Phase 4 : Cleanup (999)
999. `999_cleanup_user_org_membership.sql` - Cleanup of the deprecated table
    - Disables RLS on user_org_membership
    - Migrates data to users.role
    - **Must be run AFTER 015**

## ⚠️ Special case : Data visibility problem

**Symptoms:**
- Empty invoices dashboard
- Empty clients dashboard
- But the data exists in the database

**Cause:** RLS (Row Level Security) policies use an obsolete table

**Quick fix:**
```bash
# Run only the fix migration
psql "$DATABASE_URL" -f db/schema/015_fix_rls_policies.sql
```

## Useful commands

### Run all migrations
```bash
cd /home/redouane/dev/AI-ERA/surenSaas
./scripts/migrate.sh
```

### Run a specific migration
```bash
psql "$DATABASE_URL" -f db/schema/015_fix_rls_policies.sql
```

### Check current RLS policies
```sql
-- View all policies on a table
SELECT * FROM pg_policies WHERE tablename = 'invoices';

-- Check whether RLS is enabled
SELECT relname, relrowsecurity FROM pg_class WHERE relname IN ('invoices', 'clients');
```

## Structure of future migrations

To add a new migration:
1. Name it according to the schema: `XXX_short_description.sql`
2. Update this README
3. Document in TESTS.md if it impacts the tests
