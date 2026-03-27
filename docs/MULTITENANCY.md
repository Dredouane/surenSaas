# Multi-tenancy

## Principe
Chaque organisation (PME) a son propre espace isolé via le slug dans l'URL.

## Routing

### Frontend
```
/[org]/                    # Org slug (ex: /construction-dupont/)
  ├── (dashboard)/         # Layout avec auth
  │   ├── projets/
  │   ├── clients/
  │   └── parametres/
  ├── login/               # Page auth
  └── page.tsx            # Landing
```

### Backend
```
/api/v1/{org}/            # Mirror du front
  ├── users/me
  ├── projects
  └── clients
```

## Isolation des données

### RLS Policy pattern
```sql
-- Toutes les tables multi-tenant
CREATE POLICY "tenant_isolation" ON table_name
    FOR ALL
    USING (org_id = current_setting('app.current_org_id')::UUID);
```

### Backend - Set context
```python
@app.middleware("http")
async def set_org_context(request: Request, call_next):
    org_id = request.path_params.get("org_id")
    if org_id:
        # Set dans Supabase via RLS
        await db.execute("SET app.current_org_id = %s", org_id)
    return await call_next(request)
```

## Validation org

### Middleware Frontend
```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const org = request.nextUrl.pathname.split('/')[1]
  
  // Vérifier org existe dans Supabase
  // Rediriger vers /login si org invalide
  // Vérifier user.org_id match org dans session
}
```

### Dépendance Backend
```python
async def get_org_from_path(org: str = Path(...)) -> Organization:
    org_data = await db.get_org_by_slug(org)
    if not org_data:
        raise HTTPException(404, "Organisation inconnue")
    return org_data
```

## Limites
- Pas de données partagées entre orgs
- Pas de compte multi-org (1 user = 1 org)
- Org slug immutable après création
