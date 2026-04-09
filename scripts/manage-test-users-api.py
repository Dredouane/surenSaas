#!/usr/bin/env python3
"""
🔧 Script pour gérer les utilisateurs de test via API REST

Usage:
    python scripts/manage-test-users-api.py
"""

import os
import sys
import requests

# Configuration
SUPABASE_URL = "https://REDACTED.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("TEST_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

# Utilisateurs de test
# ⚠️  Supabase Auth rejette les emails avec tirets ou underscores dans certains cas
# Format valide: lettres, chiffres, points uniquement
TEST_USERS = {
    "test.admin@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Admin",
        "role": "admin"
    },
    "test.conducteur@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Conducteur",
        "role": "conducteur"
    },
    "test.gerant@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Gerant",
        "role": "gerant"
    },
    "test.comptable@suren.com": {
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "Comptable",
        "role": "comptable"
    },
}

def list_users():
    """Liste tous les utilisateurs via l'API REST."""
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY
    }
    
    response = requests.get(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json().get("users", [])
    else:
        print(f"❌ Erreur list_users: {response.status_code} - {response.text}")
        return []

def delete_user(user_id: str) -> bool:
    """Supprime un utilisateur via l'API REST."""
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY
    }
    
    response = requests.delete(
        f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
        headers=headers
    )
    
    return response.status_code in [200, 204]

def create_user(email: str, user_data: dict) -> bool:
    """Crée un utilisateur avec email confirmé via l'API REST."""
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "email": email,
        "password": user_data["password"],
        "email_confirm": True,
        "user_metadata": {
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "role": user_data["role"]
        }
    }
    
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=headers,
        json=payload
    )
    
    if response.status_code in [200, 201]:
        return True
    else:
        print(f"❌ Erreur création {email}: {response.status_code} - {response.text}")
        return False

def main():
    print("🔧 GESTION DES UTILISATEURS DE TEST (API REST)")
    print("=" * 50)
    print()
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ TEST_SUPABASE_SERVICE_KEY non définie")
        sys.exit(1)
    
    print("📋 Liste des utilisateurs existants...")
    existing_users = list_users()
    print(f"✅ {len(existing_users)} utilisateurs trouvés")
    print()
    
    # Supprimer les utilisateurs de test existants
    deleted_count = 0
    for user in existing_users:
        if user.get("email") in TEST_USERS:
            print(f"🗑️  Suppression: {user['email']}")
            if delete_user(user["id"]):
                deleted_count += 1
            else:
                print(f"⚠️  Échec suppression: {user['email']}")
    
    if deleted_count > 0:
        print(f"✅ {deleted_count} utilisateurs supprimés")
        print()
    
    # Créer les nouveaux utilisateurs
    print("📝 Création des nouveaux utilisateurs...")
    created_count = 0
    for email, user_data in TEST_USERS.items():
        print(f"📝 Création: {email}")
        if create_user(email, user_data):
            print(f"✅ Créé: {email}")
            created_count += 1
        print()
    
    print("=" * 50)
    print(f"✅ {created_count}/{len(TEST_USERS)} utilisateurs créés")
    print()
    print("📝 Identifiants pour les tests E2E:")
    for email, user_data in TEST_USERS.items():
        print(f"   {email}")
        print(f"   Mot de passe: {user_data['password']}")
        print()

if __name__ == "__main__":
    main()
