# Database (Supabase Postgres) - SIMPLIFIED ARCHITECTURE

## Script organization

The SQL scripts are in `/home/redouane/dev/AI-ERA/surenSaas/db/`:

```
db/
├── schema/                    # Structure (to run in order)
│   ├── 001_organizations.sql  # Organizations table
│   ├── 002_users.sql          # User profiles (WITH role)
│   ├── 003_pre_authorized_emails.sql  # Invitations
│   ├── 004_user_org_membership.sql    # DEPRECATED - kept for reference
│   ├── 005_auth_triggers.sql  # Signup automation
│   └── 999_cleanup_user_org_membership.sql  # Final cleanup
```

## Simplified architecture

### Major change
**REMOVAL of `user_org_membership`** - The `role` is now directly in `users`.

Before:
- `users` → user profile
- `user_org_membership` → user-org association with role

After (simplified):
- `users` → user profile WITH `org_id` AND `role`

### Why this simplification?
- ✅ Single source of truth
- ✅ Less complexity (no membership trigger)
- ✅ Better performance (no join)
- ✅ Avoids RLS recursions

## Main tables

### 1. organizations (001)
Root table of the multi-tenant setup.
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    theme_config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2. users (002) - SIMPLIFIED
User profile with org_id and role directly.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    role TEXT CHECK (role IN ('admin', 'user')),  -- NEW
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Note**: The `role` is transferred from `pre_authorized_emails` at signup.

### 3. pre_authorized_emails (003)
Emails authorized to create an account.
```sql
CREATE TABLE pre_authorized_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    invited_by UUID REFERENCES auth.users(id),
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);
```

### 4. user_org_membership (004) - DEPRECATED
**DO NOT USE ANYMORE** - Kept temporarily for compatibility.
The role is now in `users.role`.

## Initial execution order

```bash
# Run in the Supabase SQL Editor in this order:

1. 001_organizations.sql
2. 002_users.sql  
3. 003_pre_authorized_emails.sql
4. 004_user_org_membership.sql (optional - deprecated)
5. 005_auth_triggers.sql
6. 999_cleanup_user_org_membership.sql (FINAL CLEANUP)
```

## Create an organization (TEST example)

```sql
-- Create the test org
INSERT INTO organizations (slug, name) 
VALUES ('test-my-company', 'My Company - TEST')
RETURNING id;

-- Grab the displayed UUID and put it in .env.test: TEST_ORG_ID
```

## Invite a user

```sql
-- Admin invites an email
INSERT INTO pre_authorized_emails (email, org_id, role)
VALUES (
  'new@company.com', 
  'org-uuid-here',
  'user'           -- or 'admin'
);
```

## Migration from the old architecture

If you have data in `user_org_membership`:

```sql
-- Transfer the roles to users
UPDATE users u
SET role = uom.role
FROM user_org_membership uom
WHERE u.id = uom.user_id;

-- Verify
SELECT email, role FROM users WHERE role IS NOT NULL;
```

## RLS Policies

### users
```sql
-- A user sees the users of their org
CREATE POLICY "users_select_org" ON users
    FOR SELECT USING (
        org_id IN (SELECT org_id FROM users WHERE id = auth.uid())
    );

-- A user edits their own profile
CREATE POLICY "users_update_own" ON users
    FOR UPDATE USING (id = auth.uid());
```

### pre_authorized_emails
```sql
-- Read by the org's admins
CREATE POLICY "admin_read_pre_auth" ON pre_authorized_emails
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM users 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );
```

## Access

- **Backend**: Service Key (bypasses RLS)
- **Frontend**: Does not communicate directly with the DB
- **Migrations**: Via Supabase Dashboard

## Conventions

- All tables have `org_id` + `created_at`
- Foreign keys with `ON DELETE CASCADE`
- Enumerations as TEXT with CHECK constraints
- One org per user (simplified)
