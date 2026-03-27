# Authentification

## Architecture
Frontend → Backend Python → Supabase. Pas d'accès direct Supabase depuis le frontend.

## Flow
```
Utilisateur → Route protégée /[org]/projects/123
                    ↓
            Middleware check session via backend
                    ↓
            Pas de session → redirect /[org]/login?redirect=...
                    ↓
            Login (appel backend API)
                    ↓
            Backend crée cookie httpOnly + JWT
                    ↓
            Redirect vers page demandée
```

## Middleware (Next.js)
- Intercepte routes protégées
- Appelle `/api/v1/auth/session` backend
- Vérifie cookie httpOnly
- Redirect vers login si invalide

## Session
- **Cookie** : httpOnly, secure, SameSite=lax
- **JWT** : Signé par backend (pas Supabase)
- **Claims** : user_id, email, org_id, org_slug, role
- **Durée** : 7 jours

## Sécurité
- Pas de clé Supabase exposée au frontend
- Tokens uniquement en cookies httpOnly
- Validation org côté backend uniquement

## Tables

### pre_authorized_emails
```sql
CREATE TABLE pre_authorized_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMP DEFAULT NOW(),
    used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

### user_org_membership (auto-créée au premier login)
```sql
CREATE TABLE user_org_membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'user',
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);
```

## API Endpoints

### POST /api/v1/auth/check-email
Vérifie si l'email est pré-autorisé.
```json
// Request
{ "email": "user@entreprise.com" }

// Response 200 - autorisé
{
  "authorized": true,
  "exists": false,
  "org_id": "uuid",
  "org_slug": "ma-societe",
  "role": "user"
}

// Response 403 - non autorisé
{ "authorized": false, "message": "Contactez votre administrateur" }
```

### POST /api/v1/auth/signup
Crée compte + membership.
```json
// Request
{
  "email": "user@entreprise.com",
  "password": "password123",
  "org_id": "uuid"
}
```

### POST /api/v1/auth/login
Login standard.
```json
// Request
{
  "email": "user@entreprise.com",
  "password": "password123"
}
```

## Frontend Deep Link

### Page /[org]/login
```tsx
// 1. Lit paramètre ?redirect=... de l'URL
// 2. Valide : hostname interne uniquement (pas d'open redirect)
// 3. Stocke en state React (pas localStorage)
// 4. Post-login → router.push(redirect) si validé, sinon /dashboard
```

### Validation redirect
```typescript
// Autorise :
// - URLs relatives : /projects/123, /dashboard
// - URLs absolues même hostname
// 
// Bloque :
// - Domaines externes
// - Protocoles : javascript:, data:, etc.
// - URLs avec // externe
```

## JWT Claims
```json
{
  "sub": "user_uuid",
  "email": "user@entreprise.com",
  "org_id": "org_uuid",
  "org_slug": "ma-societe",
  "role": "user"
}
```

## Sécurité

### Rate Limiting (mémoire)
- Stockage en mémoire Python (pas Redis)
- Clé : hash(IP + User-Agent) + endpoint
- Login : 5 tentatives/minute
- Check-email : 10 requêtes/minute
- Cleanup automatique des entrées anciennes

### Validation redirect
- Fonction `isValidRedirect()` centralisée
- Liste `ALLOWED_HOSTNAMES` par environnement
- Fallback sur `/[org]/dashboard` si redirect invalide

### Password
- Min 8 caractères
- Pas de complexité forcée (NIST guidelines)
- Reset via Supabase standard

## Triggers SQL

### Création membership au signup
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_user_membership();
```

## Invitations admin
```sql
-- Admin invite un nouvel utilisateur
INSERT INTO pre_authorized_emails (email, org_id, role, invited_by)
VALUES ('nouveau@entreprise.com', 'org_uuid', 'user', 'admin_uuid');
```
