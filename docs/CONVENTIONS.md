# Conventions

## Naming

### Files
- **Components**: PascalCase (`UserCard.tsx`)
- **Utils**: camelCase (`formatDate.ts`)
- **API**: kebab-case (`user-controller.ts`)
- **SQL**: snake_case (`001_add_users.sql`)

### Variables
- **Constants**: UPPER_SNAKE_CASE
- **Functions**: camelCase
- **Classes**: PascalCase
- **Private**: `_` prefix

## Code

### TypeScript
```typescript
// Always type the props
interface Props {
  user: User;
  onUpdate: (id: string) => void;
}

// No any
// No non-null assertions (!)
// Prefer nullish coalescing (??)
```

### Python
```python
# Mandatory type hints
def get_user(user_id: UUID) -> User | None:
    pass

# Google-style docstrings
"""Fetches a user.

Args:
    user_id: UUID of the user

Returns:
    User or None if not found
"""
```

## Git
```bash
# Branches
feature/add-projects
fix/fix-auth
hotfix/urgent-db

# Commits
feat: add project management
fix: fix email validation
docs: update README
```

## Database
- UUID v4 for IDs
- Timestamps in UTC
- No ON DELETE CASCADE (soft delete)
- Index on every foreign key

## API
- Strict RESTful
- Version in URL: `/api/v1/`
- Standard HTTP codes
- JSON error format: `{ "error": "message", "code": "XXX" }`
