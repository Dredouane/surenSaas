# Multi-tenancy

## Principle
Each organization (SME) has its own isolated space via the slug in the URL.

## Routing

### Frontend
```
/[org]/                    # Org slug (ex: /construction-dupont/)
  ├── (dashboard)/         # Layout with auth
  │   ├── projets/
  │   ├── clients/
  │   └── parametres/
  ├── login/               # Auth page
  └── page.tsx            # Landing
```

### Backend
```
/api/v1/{org}/            # Mirror of the front
  ├── users/me
  ├── projects
  └── clients
```

## Data isolation

### RLS Policy pattern
```sql
-- All multi-tenant tables
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
        # Set in Supabase via RLS
        await db.execute("SET app.current_org_id = %s", org_id)
    return await call_next(request)
```

## Org validation

### Frontend middleware
```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const org = request.nextUrl.pathname.split('/')[1]
  
  // Check org exists in Supabase
  // Redirect to /login if org is invalid
  // Check user.org_id matches org in session
}
```

### Backend dependency
```python
async def get_org_from_path(org: str = Path(...)) -> Organization:
    org_data = await db.get_org_by_slug(org)
    if not org_data:
        raise HTTPException(404, "Unknown organization")
    return org_data
```

## Limitations
- No data shared between orgs
- No multi-org account (1 user = 1 org)
- Org slug immutable after creation
