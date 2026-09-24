# Database (Supabase Postgres)

## Script organization

The SQL scripts are in `/home/redouane/dev/AI-ERA/surenSaas/db/`:

```
db/
├── schema/                    # Initial structure (to run in order)
│   ├── 001_organizations.sql  # Organizations table (multi-tenant root)
│   ├── 002_users.sql          # User profiles
│   ├── 003_pre_authorized_emails.sql  # Invitations
│   ├── 004_user_org_membership.sql    # User-org link
│   └── 005_auth_triggers.sql  # Signup automation
│
├── migrations/               # Versioned changes (not created)
│   └── (future evolutions)
│
└── policies/                 # RLS policies
    └── auth_rls.sql          # Row-level security
```

## Initial execution order

**IMPORTANT**: Run the scripts in this order:

```bash
# 1. Log in to Supabase -> SQL Editor -> New query

# 2. Run each file in order:
#    001_organizations.sql
#    002_users.sql  
#    003_pre_authorized_emails.sql
#    004_user_org_membership.sql
#    005_auth_triggers.sql
#    auth_rls.sql (policies)

# OR use the script (if psql is available)
./scripts/migrate.sh
```

## Main tables

### 1. organizations (001)
Root table of the multi-tenant setup.
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,           # For [org] routing
    name TEXT NOT NULL,
    theme_config JSONB DEFAULT '{}',     # CSS variables
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2. users (002)
User profiles, linked to Supabase's auth.users.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. pre_authorized_emails (003)
Emails authorized to create an account in an org.
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

### 4. user_org_membership (004)
User-organization association with role.
```sql
CREATE TABLE user_org_membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);
```

### 5. Auth trigger (005)
Automatically creates the membership when a user signs up.
```sql
CREATE OR REPLACE FUNCTION create_user_membership()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_org_membership (user_id, org_id, role)
    SELECT NEW.id, pae.org_id, pae.role
    FROM pre_authorized_emails pae
    WHERE pae.email = NEW.email AND pae.is_active = true;
    
    UPDATE pre_authorized_emails SET used_at = NOW() WHERE email = NEW.email;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_user_membership();
```

## RLS Policies (db/policies/auth_rls.sql)

```sql
-- pre_authorized_emails: read by org admins
CREATE POLICY "admin_read_pre_auth" ON pre_authorized_emails
    FOR SELECT USING (org_id IN (
        SELECT org_id FROM user_org_membership 
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- user_org_membership: user sees their own memberships
CREATE POLICY "user_read_own_memberships" ON user_org_membership
    FOR SELECT USING (user_id = auth.uid());
```

## Create an organization (TEST example)

In the Supabase SQL Editor after running all the scripts:

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
  'org-uuid-here',  -- TEST_ORG_ID or PROD_ORG_ID
  'user'            -- or 'admin'
);
```

## Access

- **Backend**: Service Key (bypasses RLS, code's responsibility)
- **Frontend**: Does not communicate directly with the DB
- **Migrations**: Via Supabase Dashboard or psql

## Conventions

- All tables have `org_id` + `created_at`
- Foreign keys with `ON DELETE CASCADE`
- Index on every foreign key
- Enumerations as TEXT with CHECK constraints
