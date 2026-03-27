"""
Test de connexion Supabase

Ce test vérifie que le backend peut se connecter à Supabase
avec différentes méthodes de chargement des variables d'environnement.
"""

import os
import sys
from pathlib import Path

# Ajouter le parent au path pour pouvoir importer app
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_env_variables():
    """Test 1: Vérifier que les variables d'environnement sont accessibles."""
    print("\n" + "="*60)
    print("TEST 1: Variables d'environnement")
    print("="*60)
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    jwt_secret = os.getenv('JWT_SECRET')
    
    print(f"SUPABASE_URL: {supabase_url[:50] if supabase_url else 'NON DÉFINI'}...")
    print(f"SUPABASE_SERVICE_KEY: {'✅ DÉFINI' if supabase_key else '❌ NON DÉFINI'}")
    print(f"JWT_SECRET: {'✅ DÉFINI' if jwt_secret else '❌ NON DÉFINI'}")
    
    if not supabase_url or not supabase_key:
        print("\n❌ ÉCHEC: Variables manquantes")
        return False
    
    print("\n✅ SUCCÈS: Toutes les variables sont définies")
    return True


def test_pydantic_settings():
    """Test 2: Vérifier que pydantic-settings charge les variables."""
    print("\n" + "="*60)
    print("TEST 2: Pydantic Settings")
    print("="*60)
    
    try:
        from app.core.config import get_settings, settings
        
        print(f"Settings importé avec succès")
        print(f"  supabase_url: {settings.supabase_url[:50] if settings.supabase_url else 'VIDE'}...")
        print(f"  supabase_service_key: {'✅' if settings.supabase_service_key else '❌'}")
        print(f"  jwt_secret: {'✅' if settings.jwt_secret else '❌'}")
        
        if settings.is_configured():
            print("\n✅ SUCCÈS: Settings configurés correctement")
            return True
        else:
            print("\n❌ ÉCHEC: Settings incomplets")
            return False
            
    except Exception as e:
        print(f"\n❌ ÉCHEC: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_supabase_connection():
    """Test 3: Vérifier la connexion directe à Supabase."""
    print("\n" + "="*60)
    print("TEST 3: Connexion Supabase")
    print("="*60)
    
    try:
        from supabase import create_client
        from app.core.config import settings
        
        if not settings.supabase_url or not settings.supabase_service_key:
            print("❌ ÉCHEC: Pas de credentials Supabase")
            return False
        
        print("Création du client Supabase...")
        client = create_client(settings.supabase_url, settings.supabase_service_key)
        print("✅ Client créé")
        
        # Test simple: récupérer la liste des tables (ou une query basique)
        print("Test de requête...")
        result = client.table('organizations').select('id, name').limit(1).execute()
        
        if result.data:
            print(f"✅ Requête réussie: {len(result.data)} résultat(s)")
            print(f"   Exemple: {result.data[0]}")
        else:
            print("✅ Connexion OK (pas de données)")
        
        print("\n✅ SUCCÈS: Connexion Supabase établie")
        return True
        
    except Exception as e:
        print(f"\n❌ ÉCHEC: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_supabase_from_auth():
    """Test 4: Vérifier la fonction get_supabase du module auth."""
    print("\n" + "="*60)
    print("TEST 4: Fonction get_supabase() du module auth")
    print("="*60)
    
    try:
        from app.api.auth import get_supabase
        
        print("Appel de get_supabase()...")
        client = get_supabase()
        print("✅ Client récupéré")
        
        # Test query
        print("Test de requête via get_supabase...")
        result = client.table('organizations').select('id').limit(1).execute()
        print(f"✅ Requête OK: {len(result.data)} résultat(s)")
        
        print("\n✅ SUCCÈS: get_supabase() fonctionne")
        return True
        
    except Exception as e:
        print(f"\n❌ ÉCHEC: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_check_email_endpoint():
    """Test 5: Tester l'endpoint check-email."""
    print("\n" + "="*60)
    print("TEST 5: Endpoint /api/v1/auth/check-email")
    print("="*60)
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        print("Création du client de test...")
        client = TestClient(app)
        
        print("Envoi de la requête POST /api/v1/auth/check-email...")
        response = client.post(
            "/api/v1/auth/check-email",
            json={"email": "email.non.existant@gmail.com"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Réponse: {response.text[:200]}")
        
        if response.status_code == 200:
            print("\n✅ SUCCÈS: Endpoint check-email fonctionne")
            return True
        else:
            print(f"\n❌ ÉCHEC: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ ÉCHEC: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests."""
    print("\n" + "🧪"*30)
    print("TESTS DE CONNEXION SUPABASE")
    print("🧪"*30)
    
    # Afficher le répertoire de travail et les fichiers .env
    print("\n📁 Répertoire de travail:", os.getcwd())
    print("📄 Fichiers .env trouvés:")
    for f in ['.env', '../.env', '../../.env', '.env.test', '../.env.test']:
        if os.path.exists(f):
            print(f"   ✅ {f} (existe)")
    
    results = []
    
    # Test 1
    results.append(("Variables d'environnement", test_env_variables()))
    
    # Test 2
    results.append(("Pydantic Settings", test_pydantic_settings()))
    
    # Test 3
    results.append(("Connexion Supabase", test_supabase_connection()))
    
    # Test 4
    results.append(("get_supabase()", test_get_supabase_from_auth()))
    
    # Test 5
    results.append(("Endpoint check-email", test_check_email_endpoint()))
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
    else:
        print("💥 CERTAINS TESTS ONT ÉCHOUÉ")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
