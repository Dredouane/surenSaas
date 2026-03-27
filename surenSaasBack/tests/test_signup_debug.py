#!/usr/bin/env python3
"""
Test unitaire pour le signup - Troubleshooting

Teste le signup étape par étape pour identifier où ça plante.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def test_signup_step_by_step():
    """Test le signup étape par étape."""
    print("\n" + "="*70)
    print("TEST SIGNUP - ÉTAPE PAR ÉTAPE")
    print("="*70 + "\n")
    
    from app.api.auth import get_supabase
    
    test_email = "test-debug@example.com"
    test_password = "TestPassword123!"
    test_org_id = "REDACTEDORG"
    
    try:
        supabase = get_supabase()
        
        # Étape 1: Vérifier pre_authorized_emails
        print("1️⃣  Vérification pre_authorized_emails...")
        pre_auth = supabase.table('pre_authorized_emails') \
            .select('*') \
            .eq('email', test_email) \
            .execute()
        
        if not pre_auth.data:
            print(f"   ⚠️  Email {test_email} non trouvé dans pre_authorized")
            print("   Création d'une entrée de test...")
            supabase.table('pre_authorized_emails').insert({
                'email': test_email,
                'org_id': test_org_id,
                'role': 'user',
                'is_active': True
            }).execute()
            print("   ✅ Entrée créée")
        else:
            print(f"   ✅ Email trouvé: {pre_auth.data[0]['id']}")
        
        # Étape 2: Vérifier si user existe déjà dans auth.users
        print("\n2️⃣  Vérification si user existe dans auth.users...")
        # On ne peut pas directement lire auth.users, mais on peut essayer de le créer
        
        # Étape 3: Essayer de créer l'utilisateur avec différentes méthodes
        print("\n3️⃣  Tentative création utilisateur Supabase Auth...")
        
        try:
            # Méthode 1: Sans métadonnées
            print("   Méthode 1: Sans options...")
            auth_response = supabase.auth.sign_up({
                "email": test_email,
                "password": test_password,
            })
            print(f"   ✅ Succès! User ID: {auth_response.user.id}")
            
        except Exception as e1:
            print(f"   ❌ Échec méthode 1: {e1}")
            
            # Méthode 2: Avec métadonnées
            print("\n   Méthode 2: Avec métadonnées...")
            try:
                auth_response = supabase.auth.sign_up({
                    "email": test_email,
                    "password": test_password,
                    "options": {
                        "data": {
                            "org_id": test_org_id,
                        }
                    }
                })
                print(f"   ✅ Succès! User ID: {auth_response.user.id}")
                
            except Exception as e2:
                print(f"   ❌ Échec méthode 2: {e2}")
                
                # Essayer de comprendre l'erreur
                print("\n   🔍 Analyse de l'erreur...")
                if "Database error" in str(e2):
                    print("   L'erreur vient de la base de données Supabase")
                    print("   Vérifications possibles:")
                    print("   - Le trigger on_auth_user_created plante")
                    print("   - La table users n'a pas la bonne structure")
                    print("   - Il manque l'org_id dans les métadonnées")
                    
                    # Vérifier la structure de la table users
                    print("\n   🔍 Vérification structure table users...")
                    try:
                        # Tenter une insertion manuelle
                        test_id = "00000000-0000-0000-0000-000000000001"
                        supabase.table('users').insert({
                            'id': test_id,
                            'email': 'test-structure@example.com',
                            'org_id': test_org_id,
                        }).execute()
                        print("   ✅ Insertion manuelle fonctionne")
                        
                        # Nettoyer
                        supabase.table('users').delete().eq('id', test_id).execute()
                        
                    except Exception as struct_error:
                        print(f"   ❌ Erreur structure: {struct_error}")
        
        # Étape 4: Si création réussie, vérifier le profil
        if 'auth_response' in locals() and auth_response.user:
            print("\n4️⃣  Vérification création profil...")
            user_id = auth_response.user.id
            
            profile = supabase.table('users').select('*').eq('id', user_id).execute()
            if profile.data:
                print(f"   ✅ Profil créé: {profile.data[0]}")
            else:
                print("   ❌ Profil non créé (trigger ne fonctionne pas)")
                
                # Création manuelle
                print("   Création manuelle du profil...")
                supabase.table('users').insert({
                    'id': user_id,
                    'email': test_email,
                    'org_id': test_org_id,
                }).execute()
                print("   ✅ Profil créé manuellement")
        
        print("\n" + "="*70)
        print("✅ TEST TERMINÉ")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERREUR GLOBALE: {e}")
        import traceback
        traceback.print_exc()


def test_existing_user_check():
    """Test la vérification de l'existence d'un user."""
    print("\n" + "="*70)
    print("TEST VÉRIFICATION EXISTENCE USER")
    print("="*70 + "\n")
    
    from app.api.auth import get_supabase
    
    test_email = "REDACTED_EMAIL"
    
    try:
        supabase = get_supabase()
        
        # Vérifier dans users table
        print(f"🔍 Recherche dans users table pour {test_email}...")
        result = supabase.table('users').select('*').eq('email', test_email).execute()
        
        if result.data:
            print(f"   ✅ User trouvé dans users table:")
            print(f"      ID: {result.data[0]['id']}")
            print(f"      Org: {result.data[0].get('org_id')}")
        else:
            print("   ❌ User non trouvé dans users table")
        
        # Vérifier dans pre_authorized
        print(f"\n🔍 Recherche dans pre_authorized_emails...")
        pre_auth = supabase.table('pre_authorized_emails') \
            .select('*') \
            .eq('email', test_email) \
            .execute()
        
        if pre_auth.data:
            print(f"   ✅ Trouvé dans pre_authorized:")
            print(f"      ID: {pre_auth.data[0]['id']}")
            print(f"      Org: {pre_auth.data[0]['org_id']}")
            print(f"      Used: {pre_auth.data[0].get('used_at')}")
        else:
            print("   ❌ Non trouvé dans pre_authorized")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Tests de debugging signup")
    print("="*70)
    
    # Test 1: Vérifier l'email REDACTED_EMAIL
    test_existing_user_check()
    
    # Test 2: Tester le signup complet
    # test_signup_step_by_step()
    
    print("\n✅ Tests terminés")
