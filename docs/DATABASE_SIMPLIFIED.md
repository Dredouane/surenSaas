# Base de données (Supabase Postgres) - ARCHITECTURE SIMPLIFIÉE

## Organisation des scripts

Les scripts SQL sont dans `/home/redouane/dev/AI-ERA/surenSaas/db/` :

```
db/
├── schema/                    # Structure (à exécuter dans l'ordre)
│   ├── 001_organizations.sql  # Table organisations
│   ├── 002_users.sql          # Profils utilisateurs (AVEC role)
│   ├── 003_pre_authorized_emails.sql  # Invitations
│   ├── 004_user_org_membership.sql    # DEPRECATED - conservé pour référence
│   ├── 005_auth_triggers.sql  # Automatisation signup
│   └── 999_cleanup_user_org_membership.sql  # Nettoyage final
```

## Architecture simplifiée

### Changement majeur
**SUPPRESSION de `user_org_membership`** - Le `role` est maintenant directement dans `users`.

Avant :
- `users` → profil utilisateur
- `user_org_membership` → association user-org avec role

Après (simplifié) :
- `users` → profil utilisateur AVEC `org_id` ET `role`

### Pourquoi cette simplification ?
- ✅ Une seule source de vérité
- ✅ Moins de complexité (pas de trigger de membership)
- ✅ Plus performant (pas de jointure)
- ✅ Évite les récursions RLS

## Tables principales

### 1. organizations (001)
Table racine du multi-tenant.
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    theme_config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2. users (002) - SIMPLIFIÉ
Profil utilisateur avec org_id et role directement.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    role TEXT CHECK (role IN ('admin', 'user')),  -- NOUVEAU
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Note** : Le `role` est transféré de `pre_authorized_emails` au signup.

### 3. pre_authorized_emails (003)
Emails autorisés à créer un compte.
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
**NE PLUS UTILISER** - Conservé temporairement pour compatibilité.
Le role est maintenant dans `users.role`.

## Ordre d'exécution initial

```bash
# Exécuter dans Supabase SQL Editor dans cet ordre :

1. 001_organizations.sql
2. 002_users.sql  
3. 003_pre_authorized_emails.sql
4. 004_user_org_membership.sql (optionnel - deprecated)
5. 005_auth_triggers.sql
6. 999_cleanup_user_org_membership.sql (NETTOYAGE FINAL)
```

## Créer une organisation (exemple TEST)

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
  'uuid-org-ici',
  'user'           -- ou 'admin'
);
```

## Migration depuis l'ancienne architecture

Si vous avez des données dans `user_org_membership` :

```sql
-- Transférer les roles vers users
UPDATE users u
SET role = uom.role
FROM user_org_membership uom
WHERE u.id = uom.user_id;

-- Vérifier
SELECT email, role FROM users WHERE role IS NOT NULL;
```

## RLS Policies

### users
```sql
-- Un user voit les users de son org
CREATE POLICY "users_select_org" ON users
    FOR SELECT USING (
        org_id IN (SELECT org_id FROM users WHERE id = auth.uid())
    );

-- Un user modifie son propre profil
CREATE POLICY "users_update_own" ON users
    FOR UPDATE USING (id = auth.uid());
```

### pre_authorized_emails
```sql
-- Lecture par admins de l'org
CREATE POLICY "admin_read_pre_auth" ON pre_authorized_emails
    FOR SELECT USING (
        org_id IN (
            SELECT org_id FROM users 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );
```

## Accès

- **Backend** : Service Key (bypass RLS)
- **Frontend** : Ne communique pas directement avec la DB
- **Migrations** : Via Supabase Dashboard

## Conventions

- Toutes les tables ont `org_id` + `created_at`
- Clés étrangères avec `ON DELETE CASCADE`
- Enumérations en TEXT avec CHECK constraint
- Une seule org par utilisateur (simplifié)
