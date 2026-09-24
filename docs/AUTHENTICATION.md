# Authentication

## Architecture
Frontend → Python Backend → Supabase. No direct Supabase access from the frontend.

## Flow
```
User → Protected route /[org]/projects/123
                    ↓
            Middleware checks session via backend
                    ↓
            No session → redirect /[org]/login?redirect=...
                    ↓
            Login (backend API call)
                    ↓
            Backend creates httpOnly cookie + JWT
                    ↓
            Redirect to requested page
```

## Middleware (Next.js)
- Intercepts protected routes
- Calls backend `/api/v1/auth/session`
- Verifies httpOnly cookie
- Redirects to login if invalid

## Session
- **Cookie**: httpOnly, secure, SameSite=lax
- **JWT**: Signed by backend (not Supabase)
- **Claims**: user_id, email, org_id, org_slug, role
- **Duration**: 7 days

## Security
- No Supabase key exposed to the frontend
- Tokens only in httpOnly cookies
- Org validation on the backend only

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

### user_org_membership (auto-created at first login)
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
Checks whether the email is pre-authorized.
```json
// Request
{ "email": "user@company.com" }

// Response 200 - authorized
{
  "authorized": true,
  "exists": false,
  "org_id": "uuid",
  "org_slug": "my-company",
  "role": "user"
}

// Response 403 - not authorized
{ "authorized": false, "message": "Contact your administrator" }
```

### POST /api/v1/auth/signup
Creates account + membership.
```json
// Request
{
  "email": "user@company.com",
  "password": "password123",
  "org_id": "uuid"
}
```

### POST /api/v1/auth/login
Standard login.
```json
// Request
{
  "email": "user@company.com",
  "password": "password123"
}
```

## Frontend Deep Link

### Page /[org]/login
```tsx
// 1. Reads the ?redirect=... URL parameter
// 2. Validates: internal hostname only (no open redirect)
// 3. Stores in React state (not localStorage)
// 4. Post-login → router.push(redirect) if validated, otherwise /dashboard
```

### Redirect validation
```typescript
// Allows:
// - Relative URLs: /projects/123, /dashboard
// - Absolute URLs on the same hostname
// 
// Blocks:
// - External domains
// - Protocols: javascript:, data:, etc.
// - URLs with external //
```

## JWT Claims
```json
{
  "sub": "user_uuid",
  "email": "user@company.com",
  "org_id": "org_uuid",
  "org_slug": "my-company",
  "role": "user"
}
```

## Security

### Rate Limiting (memory)
- Storage in Python memory (not Redis)
- Key: hash(IP + User-Agent) + endpoint
- Login: 5 attempts/minute
- Check-email: 10 requests/minute
- Automatic cleanup of old entries

### Redirect validation
- Centralized `isValidRedirect()` function
- `ALLOWED_HOSTNAMES` list per environment
- Fallback to `/[org]/dashboard` if redirect is invalid

### Password
- Min 8 characters
- No forced complexity (NIST guidelines)
- Reset via standard Supabase

## SQL Triggers

### Membership creation at signup
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

## Admin invitations
```sql
-- Admin invites a new user
INSERT INTO pre_authorized_emails (email, org_id, role, invited_by)
VALUES ('new@company.com', 'org_uuid', 'user', 'admin_uuid');
```
