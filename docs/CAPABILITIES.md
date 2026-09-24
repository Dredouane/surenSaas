# Capabilities System (Permissions)

## Overview

Granular permissions system based on capabilities in the `resource:action` format.

**Admins** automatically bypass all checks.

## Format

```
{resource}:{subresource}:{action}
```

Examples:
- `construction:facturation:read`
- `construction:facturation:write`
- `construction:planning:read`

## Architecture

### Tables

#### `organization_capabilities`
Defines the capabilities available for an organization.

```sql
org_id UUID
resource TEXT      -- 'construction', 'planning'
action TEXT        -- 'read', 'write', 'validate', 'delete'
capability_code TEXT  -- 'construction:facturation:read'
```

#### `user_capabilities`
Assigns capabilities to users.

```sql
user_id UUID
org_id UUID
capability_code TEXT
granted_by UUID
is_active BOOLEAN
```

#### View `user_active_capabilities`
View making it easy to retrieve active capabilities.

### Checking

```python
from app.core.capabilities import CapabilityChecker

checker = CapabilityChecker(supabase)

# Check a capability
has_access = await checker.has_capability(
    user_id='uuid',
    org_id='uuid',
    capability='construction:facturation:read'
)

# Retrieve all capabilities
capabilities = await checker.get_user_capabilities(
    user_id='uuid',
    org_id='uuid'
)
```

## Construction Capabilities

| Code | Description |
|------|-------------|
| `construction:facturation:read` | View invoices |
| `construction:facturation:write` | Create/modify invoices |
| `construction:facturation:validate` | Validate/reject invoices |
| `construction:facturation:delete` | Delete invoices |

## Usage in FastAPI routes

### Method 1: Manual check

```python
@router.get("/invoices")
async def list_invoices(
    request: Request,
    org: str,
    user: dict = Depends(get_current_user),
    checker: CapabilityChecker = Depends(get_capability_checker)
):
    if not await checker.has_capability(user['id'], org, 'construction:facturation:read'):
        raise HTTPException(403, "Capability required")
    
    # Continued...
```

### Method 2: Dependency

```python
@router.get("/invoices", dependencies=[
    Depends(require_capability('construction:facturation:read'))
])
async def list_invoices(request: Request, org: str):
    # Capability already checked
    pass
```

### Method 3: Decorator

```python
from app.core.capabilities import CONSTRUCTION_CAPABILITIES

@router.get("/invoices")
@require_capability(CONSTRUCTION_CAPABILITIES['FACTURATION_READ'])
async def list_invoices(request: Request, org: str):
    pass
```

## Admin Behavior

Users with `users.role = 'admin'`:
- ✅ Automatically have ALL capabilities
- ✅ Do not require an entry in `user_capabilities`
- ✅ Are detected before the capability check

## SQL Helper

```sql
-- Check whether a user has a capability (or is an admin)
SELECT check_user_capability('user-uuid', 'org-uuid', 'construction:facturation:read');

-- List a user's capabilities
SELECT * FROM user_active_capabilities 
WHERE user_id = 'uuid' AND org_id = 'uuid';

-- Assign a capability (admin only)
INSERT INTO user_capabilities (user_id, org_id, capability_code, granted_by)
VALUES ('user-uuid', 'org-uuid', 'construction:facturation:write', 'admin-uuid');

-- Revoke a capability
UPDATE user_capabilities 
SET is_active = false, revoked_at = NOW()
WHERE user_id = 'uuid' AND capability_code = 'construction:facturation:write';
```

## Comparison with Roles

| Aspect | Roles (admin/user) | Capabilities |
|--------|-------------------|--------------|
| Granularity | Coarse (2 roles) | Fine (unlimited) |
| Flexibility | Limited | High |
| Complexity | Simple | Moderate |
| Usage | Authentication | Authorization |

## Migration from binary roles

Existing: `role IN ('admin', 'user')`

New:
1. Keep `admin` for full access
2. Create capabilities for users
3. Standard users have no special role but capabilities

## Best practices

### Naming
- **Resource**: Singular, lowercase (`construction`, `planning`)
- **Action**: CRUD verb (`read`, `write`, `update`, `delete`, `validate`)

### Implicit inheritance
No automatic inheritance (e.g. `write` does not imply `read`).
Each capability must be assigned explicitly.

### Documentation
Document each capability in:
- `docs/CAPABILITIES.md` (this file)
- Code with constants
- OpenAPI `security` descriptions

## References

- Implementation: `app/core/capabilities.py`
- SQL schema: `db/schema/006_capabilities.sql`
- Usage: `docs/CONSTRUCTION_INVOICES.md`
