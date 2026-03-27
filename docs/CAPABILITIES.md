# Système de Capabilities (Permissions)

## Vue d'ensemble

Système de permissions granulaires basé sur des capabilities au format `resource:action`.

Les **admins** bypassent automatiquement toutes les vérifications.

## Format

```
{resource}:{subresource}:{action}
```

Exemples:
- `construction:facturation:read`
- `construction:facturation:write`
- `construction:planning:read`

## Architecture

### Tables

#### `organization_capabilities`
Définit les capabilities disponibles pour une organisation.

```sql
org_id UUID
resource TEXT      -- 'construction', 'planning'
action TEXT        -- 'read', 'write', 'validate', 'delete'
capability_code TEXT  -- 'construction:facturation:read'
```

#### `user_capabilities`
Assigne des capabilities aux users.

```sql
user_id UUID
org_id UUID
capability_code TEXT
granted_by UUID
is_active BOOLEAN
```

#### Vue `user_active_capabilities`
Vue facilitant la récupération des capabilities actives.

### Vérification

```python
from app.core.capabilities import CapabilityChecker

checker = CapabilityChecker(supabase)

# Vérifier une capability
has_access = await checker.has_capability(
    user_id='uuid',
    org_id='uuid',
    capability='construction:facturation:read'
)

# Récupérer toutes les capabilities
capabilities = await checker.get_user_capabilities(
    user_id='uuid',
    org_id='uuid'
)
```

## Capabilities Construction

| Code | Description |
|------|-------------|
| `construction:facturation:read` | Voir les factures |
| `construction:facturation:write` | Créer/modifier factures |
| `construction:facturation:validate` | Valider/rejeter factures |
| `construction:facturation:delete` | Supprimer factures |

## Utilisation dans les routes FastAPI

### Méthode 1: Vérification manuelle

```python
@router.get("/invoices")
async def list_invoices(
    request: Request,
    org: str,
    user: dict = Depends(get_current_user),
    checker: CapabilityChecker = Depends(get_capability_checker)
):
    if not await checker.has_capability(user['id'], org, 'construction:facturation:read'):
        raise HTTPException(403, "Capability requise")
    
    # Suite...
```

### Méthode 2: Dépendance

```python
@router.get("/invoices", dependencies=[
    Depends(require_capability('construction:facturation:read'))
])
async def list_invoices(request: Request, org: str):
    # Capability déjà vérifiée
    pass
```

### Méthode 3: Décorateur

```python
from app.core.capabilities import CONSTRUCTION_CAPABILITIES

@router.get("/invoices")
@require_capability(CONSTRUCTION_CAPABILITIES['FACTURATION_READ'])
async def list_invoices(request: Request, org: str):
    pass
```

## Comportement Admin

Les users avec `users.role = 'admin'`:
- ✅ Ont automatiquement TOUTES les capabilities
- ✅ Ne nécessitent pas d'entrée dans `user_capabilities`
- ✅ Sont détectés avant vérification capability

## SQL Helper

```sql
-- Vérifier si user a une capability (ou est admin)
SELECT check_user_capability('user-uuid', 'org-uuid', 'construction:facturation:read');

-- Liste capabilities d'un user
SELECT * FROM user_active_capabilities 
WHERE user_id = 'uuid' AND org_id = 'uuid';

-- Assigner capability (admin uniquement)
INSERT INTO user_capabilities (user_id, org_id, capability_code, granted_by)
VALUES ('user-uuid', 'org-uuid', 'construction:facturation:write', 'admin-uuid');

-- Révoquer capability
UPDATE user_capabilities 
SET is_active = false, revoked_at = NOW()
WHERE user_id = 'uuid' AND capability_code = 'construction:facturation:write';
```

## Comparaison avec Rôles

| Aspect | Rôles (admin/user) | Capabilities |
|--------|-------------------|--------------|
| Granularité | Grossière (2 rôles) | Fine (illimité) |
| Flexibilité | Limitée | Haute |
| Complexité | Simple | Modérée |
| Usage | Authentification | Autorisation |

## Migration depuis rôles binaires

Existant: `role IN ('admin', 'user')`

Nouveau:
1. Garder `admin` pour accès complet
2. Créer capabilities pour les users
3. Users standards n'ont pas de rôle spécial mais des capabilities

## Bonnes pratiques

### Nommage
- **Resource**: Singulier, minuscule (`construction`, `planning`)
- **Action**: Verbe CRUD (`read`, `write`, `update`, `delete`, `validate`)

### Héritage implicite
Pas d'héritage automatique (ex: `write` n'implique pas `read`).
Chaque capability doit être assignée explicitement.

### Documentation
Documenter chaque capability dans:
- `docs/CAPABILITIES.md` (ce fichier)
- Code avec constantes
- OpenAPI `security` descriptions

## Références

- Implémentation: `app/core/capabilities.py`
- Schéma SQL: `db/schema/006_capabilities.sql`
- Utilisation: `docs/CONSTRUCTION_INVOICES.md`
