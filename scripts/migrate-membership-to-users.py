#!/usr/bin/env python3
"""
🔧 Script de migration : Transfère user_org_membership vers users

À exécuter UNE SEULE FOIS après la simplification de l'architecture.

Usage:
    python scripts/migrate-membership-to-users.py
"""

import os
import sys
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("TEST_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

def migrate():
    print("🔧 MIGRATION : user_org_membership → users")
    print("=" * 50)
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ TEST_SUPABASE_SERVICE_KEY non définie")
        sys.exit(1)
    
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # 1. Vérifier s'il y a des données à migrer
    print("\n📋 Vérification des données...")
    try:
        result = supabase.table('user_org_membership').select('*').execute()
        memberships = result.data or []
        print(f"✅ {len(memberships)} membership(s) trouvé(s) dans user_org_membership")
    except Exception as e:
        print(f"⚠️ Table user_org_membership inaccessible ou vide: {e}")
        memberships = []
    
    if not memberships:
        print("\n✅ Rien à migrer. Déjà à jour!")
        return
    
    # 2. Migrer chaque membership
    print(f"\n🔄 Migration des {len(memberships)} membership(s)...")
    migrated = 0
    errors = 0
    
    for membership in memberships:
        user_id = membership.get('user_id')
        org_id = membership.get('org_id')
        role = membership.get('role', 'user')
        
        try:
            # Mettre à jour users avec le role
            supabase.table('users').update({
                'org_id': org_id,
                'role': role
            }).eq('id', user_id).execute()
            
            print(f"✅ Migré: user {user_id} → role {role}")
            migrated += 1
            
        except Exception as e:
            print(f"❌ Erreur migration user {user_id}: {e}")
            errors += 1
    
    print(f"\n{'=' * 50}")
    print(f"✅ Migration terminée: {migrated} succès, {errors} erreurs")
    
    # 3. Vérification
    print("\n📊 Vérification finale:")
    try:
        users_with_role = supabase.table('users').select('id').not_.is_('role', 'null').execute()
        print(f"✅ {len(users_with_role.data)} utilisateur(s) avec un role défini")
    except Exception as e:
        print(f"⚠️ Erreur vérification: {e}")
    
    print("\n💡 Prochaines étapes:")
    print("   1. Exécuter 999_cleanup_user_org_membership.sql")
    print("   2. Redémarrer le backend")
    print("   3. Tester l'application")

if __name__ == "__main__":
    migrate()
