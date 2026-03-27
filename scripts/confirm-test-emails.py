#!/usr/bin/env python3
"""
🔧 Script de confirmation d'emails pour tests E2E

Utilise la clé service_role de Supabase pour confirmer les emails
sans avoir besoin de cliquer sur un lien de confirmation.

Usage:
    python scripts/confirm-test-emails.py
"""

import os
import sys
import secrets
from supabase import create_client

# Configuration
SUPABASE_URL = "https://REDACTED.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("TEST_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

# Utilisateurs de test avec mots de passe fixes
TEST_USERS = {
    "test-e2e-admin@suren.com": "TestPassword123!",
    "test-e2e-conducteur@suren.com": "TestPassword123!",
    "test-e2e-gerant@suren.com": "TestPassword123!",
    "test-e2e-comptable@suren.com": "TestPassword123!",
}

def create_or_confirm_user(email: str, password: str, supabase) -> bool:
    """Crée un utilisateur avec email confirmé ou confirme un existant."""
    try:
        # Essayer de créer l'utilisateur directement
        # Si l'utilisateur existe déjà, une erreur sera levée
        print(f"📝 Création/mise à jour: {email}")
        try:
            # Créer avec email confirmé via l'API admin
            user = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "first_name": "Test",
                    "last_name": email.split('@')[0].replace('test-e2e-', '').replace('-', ' ').title(),
                    "role": email.split('@')[0].replace('test-e2e-', '')
                }
            })
            
            print(f"✅ Utilisateur créé: {email}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower() or "already exists" in error_msg.lower() or "has already been registered" in error_msg:
                # L'utilisateur existe, essayer de le mettre à jour
                print(f"ℹ️  Utilisateur existe déjà: {email}")
                try:
                    # Chercher l'ID de l'utilisateur
                    response = supabase.auth.admin.list_users()
                    users = response.users if hasattr(response, 'users') else []
                    
                    for user in users:
                        if user.email == email:
                            # Mettre à jour le mot de passe et confirmer l'email
                            supabase.auth.admin.update_user_by_id(
                                user.id,
                                {
                                    "password": password,
                                    "email_confirm": True
                                }
                            )
                            print(f"✅ Utilisateur mis à jour: {email}")
                            return True
                    
                    print(f"⚠️  Utilisateur trouvé mais impossible à mettre à jour: {email}")
                    return False
                    
                except Exception as e2:
                    print(f"⚠️  Erreur mise à jour {email}: {e2}")
                    return False
            elif "rate limit" in error_msg:
                print(f"⏱️  Rate limit atteint pour {email}")
                print("   Attendez quelques minutes et réessayez")
                return False
            else:
                print(f"❌ Erreur création {email}: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Erreur pour {email}: {e}")
        return False

def main():
    print("🔧 Confirmation des emails de test")
    print("=" * 50)
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ TEST_SUPABASE_SERVICE_KEY non définie")
        print("Exportez-la depuis ~/.bashrc:")
        print("  export TEST_SUPABASE_SERVICE_KEY='eyJ...'")
        sys.exit(1)
    
    try:
        # Connexion à Supabase avec service_role
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Connecté à Supabase")
        print()
        
        # Créer ou confirmer chaque utilisateur
        success_count = 0
        for email, password in TEST_USERS.items():
            if create_or_confirm_user(email, password, supabase):
                success_count += 1
            print()
        
        print("=" * 50)
        print(f"✅ {success_count}/{len(TEST_USERS)} utilisateurs créés/mis à jour")
        print()
        print("📝 Mots de passe pour les tests E2E:")
        for email, password in TEST_USERS.items():
            print(f"   {email}: {password}")
        
        if success_count < len(TEST_USERS):
            print("\n💡 Alternative: Désactivez la confirmation d'email dans Supabase:")
            print("   1. Allez dans Supabase Dashboard > Authentication > Providers")
            print("   2. Décochez 'Confirm email' dans Email settings")
            
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
