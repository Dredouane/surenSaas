# Base de données (Supabase Postgres)

## Organisation des scripts

Les scripts SQL sont dans `/home/redouane/dev/AI-ERA/surenSaas/db/` :

```
db/
├── schema/                    # Structure initiale (à exécuter dans l'ordre)
│   ├── 001_organizations.sql  # Table organisations (racine multi-tenant)
│   ├── 002_users.sql          # Profils utilisateurs
│   ├── 003_pre_authorized_emails.sql  # Invitations
│   ├── 004_user_org_membership.sql    # Liaison user-org
│   └── 005_auth_triggers.sql  # Automatisation signup
│
├── migrations/               # Modifications versionnées (non créé)
│   └── (futures évolutions)
│
└── policies/                 # RLS policies
    └── auth_rls.sql          # Sécurité row-level
```

## Ordre d'exécution initial

**IMPORTANT** : Exécuter les scripts dans cet ordre :

```bash
# 1. Se connecter à Supabase -> SQL Editor -> New query

# 2. Exécuter chaque fichier dans l'ordre :
#    001_organizations.sql
#    002_users.sql  
#    003_pre_authorized_emails.sql
#    004_user_org_membership.sql
#    005_auth_triggers.sql
#    auth_rls.sql (policies)

# OU utiliser le script (si psql disponible)
./scripts/migrate.sh
```

## Tables principales

### 1. organizations (001)
Table racine du multi-tenant.
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,           -- Pour routing [org]
    name TEXT NOT NULL,
    theme_config JSONB DEFAULT '{}',     -- CSS variables
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2. users (002)
Profils utilisateurs, liés à auth.users de Supabase.
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
Emails autorisés à créer un compte dans une org.
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
Association user-organisation avec rôle.
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

### 5. Trigger auth (005)
Crée automatiquement le membership quand un user s'inscrit.
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
-- pre_authorized_emails : lecture par admins org
CREATE POLICY "admin_read_pre_auth" ON pre_authorized_emails
    FOR SELECT USING (org_id IN (
        SELECT org_id FROM user_org_membership 
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- user_org_membership : user voit ses propres memberships
CREATE POLICY "user_read_own_memberships" ON user_org_membership
    FOR SELECT USING (user_id = auth.uid());
```

## Créer une organisation (exemple TEST)

Dans Supabase SQL Editor après avoir exécuté tous les scripts :

```sql
-- Créer org de test
INSERT INTO organizations (slug, name) 
VALUES ('test-ma-societe', 'Ma Société - TEST')
RETURNING id;

-- Récupérer l'UUID affiché et le mettre dans .env.test : TEST_ORG_ID
```

## Inviter un utilisateur

```sql
-- Admin invite un email
INSERT INTO pre_authorized_emails (email, org_id, role)
VALUES (
  'nouveau@entreprise.com', 
  'uuid-org-ici',  -- TEST_ORG_ID ou PROD_ORG_ID
  'user'           -- ou 'admin'
);
```

## Accès

- **Backend** : Service Key (bypass RLS, responsabilité du code)
- **Frontend** : Ne communique pas directement avec la DB
- **Migrations** : Via Supabase Dashboard ou psql

## Conventions

- Toutes les tables ont `org_id` + `created_at`
- Clés étrangères avec `ON DELETE CASCADE`
- Index sur chaque clé étrangère
- Enumérations en TEXT avec CHECK constraint
