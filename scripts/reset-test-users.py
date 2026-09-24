#!/usr/bin/env python3
"""
🔧 Script pour supprimer et recréer les utilisateurs de test

⚠️  ATTENTION: Ceci supprime les utilisateurs et leurs données!

Usage:
    python scripts/reset-test-users.py
"""

import os
import sys
from supabase import create_client

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("TEST_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

# Utilisateurs de test
TEST_USERS = {
    "test-e2e-admin@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Admin",
        "role": "admin"
    },
    "test-e2e-conducteur@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Conducteur",
        "role": "conducteur"
    },
    "test-e2e-gerant@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Gerant",
        "role": "gerant"
    },
    "test-e2e-comptable@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Comptable",
        "role": "comptable"
    },
}

def delete_user_by_email(email: str, supabase) -> bool:
    """Supprime un utilisateur par email."""
    try:
        response = supabase.auth.admin.list_users()
        users = response.users if hasattr(response, 'users') else []
        
        for user in users:
            if user.email == email:
                supabase.auth.admin.delete_user(user.id)
                print(f"🗑️  Utilisateur supprimé: {email}")
                return True
        
        return False
    except Exception as e:
        print(f"⚠️  Erreur suppression {email}: {e}")
        return False

def create_user(email: str, user_data: dict, supabase) -> bool:
    """Crée un utilisateur avec email confirmé."""
    try:
        user = supabase.auth.admin.create_user({
            "email": email,
            "password": user_data["password"],
            "email_confirm": True,
            "user_metadata": {
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "role": user_data["role"]
            }
        })
        print(f"✅ Utilisateur créé: {email}")
        return True
    except Exception as e:
        print(f"❌ Erreur création {email}: {e}")
        return False

def main():
    print("🔧 RÉINITIALISATION DES UTILISATEURS DE TEST")
    print("=" * 50)
    print("⚠️  ATTENTION: Les utilisateurs existants seront supprimés!")
    print()
    
    confirm = input("Êtes-vous sûr? (tapez 'reset' pour confirmer): ")
    if confirm != "reset":
        print("❌ Opération annulée")
        return
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ TEST_SUPABASE_SERVICE_KEY non définie")
        sys.exit(1)
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Connecté à Supabase")
        print()
        
        success_count = 0
        for email, user_data in TEST_USERS.items():
            # Supprimer l'utilisateur existant
            delete_user_by_email(email, supabase)
            
            # Créer le nouvel utilisateur
            if create_user(email, user_data, supabase):
                success_count += 1
            print()
        
        print("=" * 50)
        print(f"✅ {success_count}/{len(TEST_USERS)} utilisateurs créés")
        print()
        print("📝 Identifiants pour les tests E2E:")
        for email, user_data in TEST_USERS.items():
            print(f"   Email: {email}")
            print(f"   Mot de passe: {user_data['password']}")
            print()
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
