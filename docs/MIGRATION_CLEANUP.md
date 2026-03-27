# 🧹 Nettoyage de l'architecture - Simplification

## Résumé des changements

### Suppression de `user_org_membership`

**Avant** :
- `users` : Profil utilisateur
- `user_org_membership` : Association user-org avec `role`

**Après** (simplifié) :
- `users` : Profil utilisateur AVEC `org_id` ET `role` directement

### Pourquoi ?
- Une seule source de vérité
- Moins de complexité
- Évite les récursions RLS
- Plus performant

## Fichiers modifiés

### Backend
- ✅ `app/core/capabilities.py` - Utilise `users` au lieu de `user_org_membership`
- ✅ `app/api/admin.py` - Utilise `users.role` directement
- ✅ `app/services/telegram/*.py` - Mis à jour

### Database
- ✅ `db/schema/999_cleanup_user_org_membership.sql` - Script de nettoyage
- ✅ `docs/DATABASE_SIMPLIFIED.md` - Documentation mise à jour

### Frontend
- ✅ Aucun changement nécessaire (utilise déjà l'API)

## Procédure de migration

### 1. Backup (important !)
```bash
# Faire un backup de la base de données
# Via Supabase Dashboard ou pg_dump
```

### 2. Exécuter le script de migration des données
```bash
export TEST_SUPABASE_SERVICE_KEY="eyJ..."
python scripts/migrate-membership-to-users.py
```

### 3. Nettoyer la DB
Exécuter dans Supabase SQL Editor :
```sql
-- Exécuter le script de nettoyage
-- 999_cleanup_user_org_membership.sql
```

### 4. Redémarrer le backend
```bash
cd surenSaasBack
python -m uvicorn app.main:app --reload --port 8080
```

### 5. Tester
- ✅ Connexion d'un admin
- ✅ Page Administration accessible
- ✅ Liste des utilisateurs pré-autorisés
- ✅ Capabilities fonctionnent

## Rollback (si nécessaire)

Si vous devez revenir en arrière :

```sql
-- Réactiver user_org_membership
ALTER TABLE public.user_org_membership ENABLE ROW LEVEL SECURITY;

-- Recréer les policies (si nécessaire)
-- Voir backup initial
```

## Notes

- `user_org_membership` est maintenant **DEPRECATED**
- Table conservée temporairement mais ignorée par le code
- À supprimer définitivement après validation complète
