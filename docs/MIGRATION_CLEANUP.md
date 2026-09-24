# 🧹 Architecture cleanup - Simplification

## Summary of changes

### Removal of `user_org_membership`

**Before**:
- `users`: User profile
- `user_org_membership`: User-org association with `role`

**After** (simplified):
- `users`: User profile WITH `org_id` AND `role` directly

### Why?
- Single source of truth
- Less complexity
- Avoids RLS recursions
- Better performance

## Modified files

### Backend
- ✅ `app/core/capabilities.py` - Uses `users` instead of `user_org_membership`
- ✅ `app/api/admin.py` - Uses `users.role` directly
- ✅ `app/services/telegram/*.py` - Updated

### Database
- ✅ `db/schema/999_cleanup_user_org_membership.sql` - Cleanup script
- ✅ `docs/DATABASE_SIMPLIFIED.md` - Updated documentation

### Frontend
- ✅ No changes needed (already uses the API)

## Migration procedure

### 1. Backup (important!)
```bash
# Back up the database
# Via Supabase Dashboard or pg_dump
```

### 2. Run the data migration script
```bash
export TEST_SUPABASE_SERVICE_KEY="eyJ..."
python scripts/migrate-membership-to-users.py
```

### 3. Clean up the DB
Run in the Supabase SQL Editor:
```sql
-- Run the cleanup script
-- 999_cleanup_user_org_membership.sql
```

### 4. Restart the backend
```bash
cd surenSaasBack
python -m uvicorn app.main:app --reload --port 8080
```

### 5. Test
- ✅ Admin login
- ✅ Administration page accessible
- ✅ List of pre-authorized users
- ✅ Capabilities working

## Rollback (if needed)

If you need to go back:

```sql
-- Re-enable user_org_membership
ALTER TABLE public.user_org_membership ENABLE ROW LEVEL SECURITY;

-- Recreate the policies (if needed)
-- See initial backup
```

## Notes

- `user_org_membership` is now **DEPRECATED**
- Table kept temporarily but ignored by the code
- To be deleted permanently after full validation
