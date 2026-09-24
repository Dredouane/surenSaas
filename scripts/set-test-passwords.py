#!/usr/bin/env python3
"""
🔧 Script pour définir les mots de passe des utilisateurs de test

Usage:
    python scripts/set-test-passwords.py
"""

import os
import sys
from supabase import create_client

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("TEST_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

# Utilisateurs et leurs mots de passe de test
TEST_USERS_PASSWORDS = {
    "test-e2e-admin@suren.com": "TestPassword123!",
    "test-e2e-conducteur@suren.com": "TestPassword123!",
    "test-e2e-gerant@suren.com": "TestPassword123!",
    "test-e2e-comptable@suren.com": "TestPassword123!",
}

def update_user_password(email: str, password: str, supabase) -> bool:
    """Met à jour le mot de passe d'un utilisateur."""
    try:
        # Chercher l'utilisateur
        response = supabase.auth.admin.list_users()
        users = response.users if hasattr(response, 'users') else []
        
        target_user = None
        for user in users:
            if user.email == email:
                target_user = user
                break
        
        if not target_user:
            print(f"❌ Utilisateur non trouvé: {email}")
            return False
        
        # Mettre à jour le mot de passe
        supabase.auth.admin.update_user_by_id(
            target_user.id,
            {"password": password}
        )
        print(f"✅ Mot de passe mis à jour: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur pour {email}: {e}")
        return False

def main():
    print("🔧 Mise à jour des mots de passe de test")
    print("=" * 50)
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ TEST_SUPABASE_SERVICE_KEY non définie")
        sys.exit(1)
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Connecté à Supabase")
        print()
        
        success_count = 0
        for email, password in TEST_USERS_PASSWORDS.items():
            if update_user_password(email, password, supabase):
                success_count += 1
        
        print()
        print("=" * 50)
        print(f"✅ {success_count}/{len(TEST_USERS_PASSWORDS)} mots de passe mis à jour")
        print()
        print("📝 Mots de passe pour les tests E2E:")
        for email, password in TEST_USERS_PASSWORDS.items():
            print(f"   {email}: {password}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
