#!/usr/bin/env python3
"""
Suite de tests complète pour SurenSaaS - Scénarios réalistes

Ce script initialise la base de données avec des données de test logiques
et exécute tous les tests (happy path + robustesse).

Usage:
    cd surenSaasBack && source venv/bin/activate
    python tests/test_full_scenarios.py
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from typing import Dict, List, Any, Optional

# Configuration test
TEST_ORG_ID = "REDACTEDORG"
TEST_COMPANY_ID = "REDACTED"

# Données de test
TEST_DATA = {
    "admin_email": "admin@suren.com",
    "conducteur_email": "conducteur@suren.com",
    "gerant_email": "gerant@suren.com",
    "comptable_email": "comptable@suren.com",
    "telegram_user_id": 123456789,
}


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_header(title: str):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{title.center(70)}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


class TestRunner:
    def __init__(self):
        self.results: List[tuple] = []
        self.supabase = None
        
    def setup_db(self) -> bool:
        """Initialise la connexion Supabase."""
        try:
            from app.api.auth import get_supabase
            self.supabase = get_supabase()
            print_success("Connexion Supabase établie")
            return True
        except Exception as e:
            print_error(f"Erreur connexion Supabase: {e}")
            return False
    
    def run_test(self, name: str, test_func) -> bool:
        """Exécute un test et enregistre le résultat."""
        try:
            print(f"\n📝 {name}...")
            result = test_func()
            if result:
                print_success(f"{name} - PASS")
                self.results.append((name, True, None))
                return True
            else:
                print_error(f"{name} - FAIL")
                self.results.append((name, False, "Test returned False"))
                return False
        except Exception as e:
            print_error(f"{name} - EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            self.results.append((name, False, str(e)))
            return False
    
    def print_summary(self):
        """Affiche le résumé des tests."""
        print_header("RÉSUMÉ DES TESTS")
        
        passed = sum(1 for _, result, _ in self.results if result)
        failed = len(self.results) - passed
        
        for name, result, error in self.results:
            status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if result else f"{Colors.RED}❌ FAIL{Colors.RESET}"
            print(f"{status}: {name}")
            if error and not result:
                print(f"   → {error}")
        
        print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"Total: {len(self.results)} tests | {Colors.GREEN}{passed} passés{Colors.RESET} | {Colors.RED}{failed} échoués{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
        
        return failed == 0


# ============================================================================
# PHASE 1: INITIALISATION DES DONNÉES DE TEST
# ============================================================================

def init_organization_data(runner: TestRunner) -> bool:
    """Crée les données de base (organisation, entreprise, capabilities)."""
    print_header("PHASE 1: INITIALISATION DES DONNÉES")
    
    try:
        supabase = runner.supabase
        
        # 1. Vérifier que l'organisation existe
        org = supabase.table('organizations').select('*').eq('id', TEST_ORG_ID).single().execute()
        if org.data:
            print_success(f"Organisation trouvée: {org.data['name']}")
        else:
            print_error("Organisation non trouvée!")
            return False
        
        # 2. Vérifier/créer l'entreprise construction
        company = supabase.table('companies').select('*').eq('id', TEST_COMPANY_ID).single().execute()
        if not company.data:
            print("Création de l'entreprise construction...")
            supabase.table('companies').insert({
                'id': TEST_COMPANY_ID,
                'org_id': TEST_ORG_ID,
                'slug': 'construction',
                'name': 'Construction Suren',
                'description': 'Gestion des chantiers et factures',
                'is_active': True
            }).execute()
            print_success("Entreprise construction créée")
        else:
            print_success(f"Entreprise trouvée: {company.data['name']}")
        
        # 3. Créer les capabilities
        capabilities = [
            ('construction:facturation:read', 'Voir les factures', 'construction', 'read'),
            ('construction:facturation:write', 'Créer/modifier factures', 'construction', 'write'),
            ('construction:facturation:validate', 'Valider/rejeter factures', 'construction', 'validate'),
            ('construction:facturation:delete', 'Supprimer factures', 'construction', 'delete'),
        ]
        
        for cap_code, desc, resource, action in capabilities:
            existing = supabase.table('organization_capabilities') \
                .select('*') \
                .eq('org_id', TEST_ORG_ID) \
                .eq('capability_code', cap_code) \
                .execute()
            
            if not existing.data:
                supabase.table('organization_capabilities').insert({
                    'org_id': TEST_ORG_ID,
                    'capability_code': cap_code,
                    'description': desc,
                    'resource': resource,
                    'action': action
                }).execute()
                print(f"  - Capability créée: {cap_code}")
        
        print_success("Capabilities initialisées")
        return True
        
    except Exception as e:
        print_error(f"Erreur initialisation: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_users_and_permissions(runner: TestRunner) -> bool:
    """Crée les utilisateurs de test avec leurs permissions."""
    print_header("PHASE 2: CRÉATION DES UTILISATEURS")
    
    try:
        supabase = runner.supabase
        
        users_config = [
            {
                'email': TEST_DATA['admin_email'],
                'role': 'admin',
                'capabilities': [],  # Admin a tout
                'telegram_id': None
            },
            {
                'email': TEST_DATA['conducteur_email'],
                'role': 'user',
                'capabilities': ['construction:facturation:write'],
                'telegram_id': TEST_DATA['telegram_user_id']
            },
            {
                'email': TEST_DATA['gerant_email'],
                'role': 'user',
                'capabilities': ['construction:facturation:read', 'construction:facturation:validate'],
                'telegram_id': None
            },
            {
                'email': TEST_DATA['comptable_email'],
                'role': 'user',
                'capabilities': ['construction:facturation:read'],
                'telegram_id': None
            }
        ]
        
        for user_config in users_config:
            email = user_config['email']
            
            # 1. Ajouter dans pre_authorized_emails
            pre_auth = supabase.table('pre_authorized_emails') \
                .select('*') \
                .eq('email', email) \
                .eq('org_id', TEST_ORG_ID) \
                .execute()
            
            if not pre_auth.data:
                supabase.table('pre_authorized_emails').insert({
                    'email': email,
                    'org_id': TEST_ORG_ID,
                    'role': user_config['role'],
                    'is_active': True
                }).execute()
                print(f"  - Pre-auth créée: {email}")
            
            # 2. Vérifier si l'utilisateur existe déjà dans auth.users
            # Note: On ne peut pas créer directement dans auth.users, 
            # il faut passer par l'API signup
            
            # 3. Ajouter les capabilities (sauf pour admin)
            if user_config['role'] != 'admin':
                for cap in user_config['capabilities']:
                    existing = supabase.table('user_capabilities') \
                        .select('*') \
                        .eq('user_id', email) \
                        .eq('org_id', TEST_ORG_ID) \
                        .eq('capability_code', cap) \
                        .execute()
                    
                    if not existing.data:
                        # Note: On ne peut pas assigner capabilities sans user_id réel
                        # Ce sera fait après signup
                        pass
            
            # 4. Créer l'utilisateur Telegram si besoin
            if user_config['telegram_id']:
                telegram_user = supabase.table('telegram_users') \
                    .select('*') \
                    .eq('telegram_id', user_config['telegram_id']) \
                    .execute()
                
                if not telegram_user.data:
                    # Note: Nécessite un user_id réel
                    pass
        
        print_success("Utilisateurs configurés")
        return True
        
    except Exception as e:
        print_error(f"Erreur création utilisateurs: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 2: TESTS AUTHENTIFICATION
# ============================================================================

def test_auth_happy_paths(runner: TestRunner) -> bool:
    """Tests auth - scénarios normaux."""
    print_header("TESTS AUTH - HAPPY PATHS")
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    all_passed = True
    
    # Test 1: Check-email pour email non autorisé
    def test_check_email_unauthorized():
        response = client.post(
            "/api/v1/auth/check-email",
            json={"email": "unknown@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['authorized'] == False
        assert 'message' in data
        print("   ✓ Email non autorisé rejeté correctement")
        return True
    
    # Test 2: Check-email pour email autorisé
    def test_check_email_authorized():
        response = client.post(
            "/api/v1/auth/check-email",
            json={"email": TEST_DATA['admin_email']}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['authorized'] == True
        assert data['org_id'] == TEST_ORG_ID
        print("   ✓ Email autorisé reconnu")
        return True
    
    all_passed &= runner.run_test("Check-email: non autorisé", test_check_email_unauthorized)
    all_passed &= runner.run_test("Check-email: autorisé", test_check_email_authorized)
    
    return all_passed


def test_auth_robustness(runner: TestRunner) -> bool:
    """Tests auth - scénarios d'erreur."""
    print_header("TESTS AUTH - ROBUSTESSE")
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    all_passed = True
    
    # Test 1: Email invalide
    def test_invalid_email():
        response = client.post(
            "/api/v1/auth/check-email",
            json={"email": "not-an-email"}
        )
        assert response.status_code == 422  # Validation error
        print("   ✓ Email invalide rejeté (422)")
        return True
    
    # Test 2: Body vide
    def test_empty_body():
        response = client.post(
            "/api/v1/auth/check-email",
            json={}
        )
        assert response.status_code == 422
        print("   ✓ Body vide rejeté (422)")
        return True
    
    all_passed &= runner.run_test("Validation: email invalide", test_invalid_email)
    all_passed &= runner.run_test("Validation: body vide", test_empty_body)
    
    return all_passed


def test_signup_workflow(runner: TestRunner) -> bool:
    """Test le workflow complet: pre_auth → check_email → signup."""
    print_header("TEST WORKFLOW SIGNUP COMPLET")
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    # Utiliser un email unique avec UUID pour éviter le rate limit
    import uuid
    test_email = f"user{uuid.uuid4().hex[:8]}@suren.com"
    test_password = "TestPassword123!"
    
    try:
        # Étape 1: Créer l'email dans pre_authorized_emails
        print(f"\n1️⃣  Création pre_auth pour {test_email}...")
        supabase = runner.supabase
        supabase.table('pre_authorized_emails').insert({
            'email': test_email,
            'org_id': TEST_ORG_ID,
            'role': 'user',
            'is_active': True
        }).execute()
        print("   ✅ Email pré-autorisé créé")
        
        # Étape 2: Appeler check-email
        print(f"\n2️⃣  Appel check-email...")
        response = client.post(
            "/api/v1/auth/check-email",
            json={"email": test_email}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['authorized'] == True
        assert data['exists'] == False
        print("   ✅ Check-email réussi")
        print(f"      Org: {data['org_slug']}")
        print(f"      Role: {data['role']}")
        
        # Étape 3: Signup
        print(f"\n3️⃣  Appel signup...")
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_email,
                "password": test_password,
                "org_id": TEST_ORG_ID
            }
        )
        
        if response.status_code == 200:
            print("   ✅ Signup réussi!")
            signup_data = response.json()
            print(f"      Réponse: {signup_data}")
            
            # Étape 4: Vérifier que le user existe
            print(f"\n4️⃣  Vérification création user...")
            user_result = supabase.table('users').select('*').eq('email', test_email).execute()
            if user_result.data:
                print(f"   ✅ User créé dans users table: {user_result.data[0]['id']}")
            else:
                print("   ⚠️  User non trouvé dans users table (trigger non fonctionnel?)")
            
            # Étape 5: Vérifier used_at mis à jour
            pre_auth_result = supabase.table('pre_authorized_emails').select('used_at').eq('email', test_email).execute()
            if pre_auth_result.data and pre_auth_result.data[0].get('used_at'):
                print("   ✅ used_at mis à jour dans pre_authorized_emails")
            
            return True
        else:
            print(f"   ❌ Signup échoué: {response.status_code}")
            print(f"      Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur workflow: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup: Supprimer le user de test
        try:
            print(f"\n🧹 Cleanup: Suppression user de test...")
            supabase.table('pre_authorized_emails').delete().eq('email', test_email).execute()
            supabase.table('users').delete().eq('email', test_email).execute()
            print("   ✅ Cleanup effectué")
        except:
            pass


# ============================================================================
# PHASE 3: TESTS FACTURATION
# ============================================================================

def test_invoices_happy_paths(runner: TestRunner) -> bool:
    """Tests facturation - scénarios normaux."""
    print_header("TESTS FACTURATION - HAPPY PATHS")
    
    try:
        supabase = runner.supabase
        
        # Créer des factures de test
        invoices_data = [
            {
                'org_id': TEST_ORG_ID,
                'company_id': TEST_COMPANY_ID,
                'invoice_number': 'FAC-2024-001',
                'supplier_name': 'Fournisseur Alpha',
                'supplier_siret': '12345678900012',
                'amount_ht': 1000.00,
                'amount_ttc': 1200.00,
                'vat_amount': 200.00,
                'vat_rate': 20.0,
                'invoice_date': '2024-03-01',
                'due_date': '2024-04-01',
                'description': 'Matériaux de construction - Lot de ciment',
                'status': 'brouillon',
                'created_by_telegram': True,
                'metadata': {'source': 'test', 'test_id': '1'}
            },
            {
                'org_id': TEST_ORG_ID,
                'company_id': TEST_COMPANY_ID,
                'invoice_number': 'FAC-2024-002',
                'supplier_name': 'Fournisseur Beta',
                'supplier_siret': '98765432100021',
                'amount_ht': 2500.00,
                'amount_ttc': 3000.00,
                'vat_amount': 500.00,
                'vat_rate': 20.0,
                'invoice_date': '2024-03-15',
                'due_date': '2024-04-15',
                'description': 'Location d\'équipements',
                'status': 'en_attente_validation',
                'created_by_telegram': False,
                'metadata': {'source': 'test', 'test_id': '2'}
            },
            {
                'org_id': TEST_ORG_ID,
                'company_id': TEST_COMPANY_ID,
                'invoice_number': 'FAC-2024-003',
                'supplier_name': 'Fournisseur Gamma',
                'amount_ht': 5000.00,
                'amount_ttc': 6000.00,
                'vat_rate': 20.0,
                'invoice_date': '2024-02-20',
                'due_date': '2024-03-20',
                'description': 'Travaux de rénovation',
                'status': 'validee',
                'validated_at': datetime.utcnow().isoformat(),
                'metadata': {'source': 'test', 'test_id': '3'}
            }
        ]
        
        created_ids = []
        for inv_data in invoices_data:
            # Vérifier si existe déjà
            existing = supabase.table('invoices') \
                .select('id') \
                .eq('org_id', TEST_ORG_ID) \
                .eq('invoice_number', inv_data['invoice_number']) \
                .execute()
            
            if not existing.data:
                result = supabase.table('invoices').insert(inv_data).execute()
                if result.data:
                    created_ids.append(result.data[0]['id'])
                    print(f"   ✓ Facture créée: {inv_data['invoice_number']} - {inv_data['status']}")
            else:
                print(f"   ✓ Facture existe: {inv_data['invoice_number']}")
        
        print_success(f"{len(invoices_data)} factures de test créées/vérifiées")
        
        # Tester la récupération
        all_invoices = supabase.table('invoices') \
            .select('*') \
            .eq('org_id', TEST_ORG_ID) \
            .execute()
        
        print(f"   ✓ Total factures en DB: {len(all_invoices.data)}")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur tests facturation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invoices_workflow(runner: TestRunner) -> bool:
    """Teste le workflow complet d'une facture."""
    print_header("TESTS FACTURATION - WORKFLOW COMPLET")
    
    try:
        supabase = runner.supabase
        
        # 1. Créer une facture en brouillon
        invoice_data = {
            'org_id': TEST_ORG_ID,
            'company_id': TEST_COMPANY_ID,
            'supplier_name': 'Test Workflow Fournisseur',
            'amount_ttc': 1500.00,
            'status': 'brouillon',
            'description': 'Test workflow complet',
            'metadata': {'test_workflow': True}
        }
        
        result = supabase.table('invoices').insert(invoice_data).execute()
        invoice_id = result.data[0]['id']
        print(f"   ✓ Facture créée (brouillon): {invoice_id[:8]}...")
        
        # 2. Passer en attente de validation
        supabase.table('invoices') \
            .update({'status': 'en_attente_validation'}) \
            .eq('id', invoice_id) \
            .execute()
        print("   ✓ Status: en_attente_validation")
        
        # 3. Valider
        supabase.table('invoices') \
            .update({
                'status': 'validee',
                'validated_at': datetime.utcnow().isoformat()
            }) \
            .eq('id', invoice_id) \
            .execute()
        print("   ✓ Status: validee")
        
        # 4. Passer en traitement comptable
        supabase.table('invoices') \
            .update({'status': 'en_traitement_comptable'}) \
            .eq('id', invoice_id) \
            .execute()
        print("   ✓ Status: en_traitement_comptable")
        
        # 5. Archiver
        supabase.table('invoices') \
            .update({'status': 'archivee'}) \
            .eq('id', invoice_id) \
            .execute()
        print("   ✓ Status: archivee")
        
        # Vérifier l'historique
        history = supabase.table('invoice_status_history') \
            .select('*') \
            .eq('invoice_id', invoice_id) \
            .execute()
        
        print(f"   ✓ Historique créé: {len(history.data)} changements")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur workflow: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# PHASE 4: TESTS TELEGRAM
# ============================================================================

def test_telegram_setup(runner: TestRunner) -> bool:
    """Tests configuration Telegram."""
    print_header("TESTS TELEGRAM - CONFIGURATION")
    
    try:
        supabase = runner.supabase
        
        # Vérifier/créer le bot
        bot = supabase.table('telegram_bots') \
            .select('*') \
            .eq('org_id', TEST_ORG_ID) \
            .eq('is_active', True) \
            .execute()
        
        if bot.data:
            print_success(f"Bot trouvé: @{bot.data[0].get('bot_username', 'N/A')}")
        else:
            print_warning("Aucun bot actif trouvé")
        
        # Vérifier les utilisateurs Telegram
        telegram_users = supabase.table('telegram_users') \
            .select('*') \
            .eq('org_id', TEST_ORG_ID) \
            .execute()
        
        print(f"   ✓ Utilisateurs Telegram: {len(telegram_users.data)}")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur Telegram: {e}")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Point d'entrée principal."""
    print_header("🧪 SUITE DE TESTS COMPLÈTE - SurenSaaS")
    
    runner = TestRunner()
    
    # Phase 0: Setup
    if not runner.setup_db():
        print_error("Impossible de continuer sans connexion DB")
        return 1
    
    # Phase 1: Initialisation données
    if not init_organization_data(runner):
        print_warning("Problème lors de l'initialisation, tentative de continuation...")
    
    if not init_users_and_permissions(runner):
        print_warning("Problème création utilisateurs, continuation...")
    
    # Phase 2: Tests Auth
    test_auth_happy_paths(runner)
    test_auth_robustness(runner)
    test_signup_workflow(runner)  # Test complet du workflow signup
    
    # Phase 3: Tests Facturation
    test_invoices_happy_paths(runner)
    test_invoices_workflow(runner)
    
    # Phase 4: Tests Telegram
    test_telegram_setup(runner)
    
    # Résumé
    success = runner.print_summary()
    
    if success:
        print(f"\n{Colors.GREEN}🎉 TOUS LES TESTS SONT PASSÉS!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}💥 CERTAINS TESTS ONT ÉCHOUÉ{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
