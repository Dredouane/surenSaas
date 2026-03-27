# Conventions

## Nommage

### Fichiers
- **Composants** : PascalCase (`UserCard.tsx`)
- **Utils** : camelCase (`formatDate.ts`)
- **API** : kebab-case (`user-controller.ts`)
- **SQL** : snake_case (`001_add_users.sql`)

### Variables
- **Constantes** : UPPER_SNAKE_CASE
- **Fonctions** : camelCase
- **Classes** : PascalCase
- **Privées** : préfixe `_`

## Code

### TypeScript
```typescript
// Toujours typer les props
interface Props {
  user: User;
  onUpdate: (id: string) => void;
}

// Pas de any
// Pas d'assertions non null (!)
// Préférer nullish coalescing (??)
```

### Python
```python
# Type hints obligatoires
def get_user(user_id: UUID) -> User | None:
    pass

# Docstrings Google style
"""Récupère un utilisateur.

Args:
    user_id: UUID de l'utilisateur

Returns:
    User ou None si non trouvé
"""
```

## Git
```bash
# Branches
feature/ajout-projets
fix/correction-auth
hotfix/urgent-db

# Commits
feat: ajoute gestion des projets
fix: corrige validation email
docs: met à jour README
```

## Base de données
- UUID v4 pour les IDs
- Timestamps en UTC
- Pas de ON DELETE CASCADE (soft delete)
- Index sur chaque clé étrangère

## API
- RESTful strict
- Version dans URL : `/api/v1/`
- HTTP codes standards
- Erreurs format JSON : `{ "error": "message", "code": "XXX" }`
