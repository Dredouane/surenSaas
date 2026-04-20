"""
Tests de la reconstruction des threads historiques - 3 Scénarios.

⚠️  STATUS: TESTS BROKEN - Mocking à corriger (Avril 2025)
===========================================================
Les tests sont structurés mais ÉCHOUENT car le mocking de Gmail API ne fonctionne pas.

Problème:
    Le service importe create_gmail_client DYNAMIQUEMENT dans la méthode,
    ce qui rend le patching avec unittest.mock impossible.

Solutions à implémenter:
    1. Refactoriser pour injection de dépendance (gmail_client en paramètre)
    2. Utiliser sys.modules manipulation avant import
    3. Créer script de test manuel sans mocking

Scénario 1 (Easy): Gmail API fonctionne - import complet
Scénario 2 (Hybrid): Gmail API échoue, Gemini extrait - partiel enrichi  
Scénario 3 (Fallback): Tout échoue - minimal avec logs

Usage:
    pytest tests/test_thread_reconstruction.py -v  # Va échouer
    pytest tests/test_thread_reconstruction.py -v -m "not slow"  # Saute Gemini

TODO: Voir docstring de TestThreadReconstructionScenarios pour détails
"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

# Configuration des tests - Utilise le vrai compte Gmail
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"
TEST_COMPANY_SLUG = "construction"
TEST_EMAIL_ACCOUNT_ID = "652d53ae-3d7c-4006-8397-43c3a99a0069"  # REDACTED_EMAIL


def get_test_org_and_company():
    """Récupère les IDs de test depuis la DB."""
    from app.api.auth import get_supabase
    supabase = get_supabase()
    
    org_response = supabase.table("organizations")\
        .select("id")\
        .eq("slug", TEST_ORG_SLUG)\
        .single()\
        .execute()
    org_id = org_response.data["id"]
    
    company_response = supabase.table("companies")\
        .select("id")\
        .eq("slug", TEST_COMPANY_SLUG)\
        .eq("org_id", org_id)\
        .single()\
        .execute()
    company_id = company_response.data["id"]
    
    return org_id, company_id


TEST_ORG_ID, TEST_COMPANY_ID = get_test_org_and_company()

# NOTE: Les tests ne nettoient PAS les données pour permettre
# de les visualiser dans l'interface. Nettoyage manuel si besoin:
# DELETE FROM emails WHERE gmail_thread_id LIKE 'thread-reconstruct-%';
# DELETE FROM email_threads WHERE gmail_thread_id LIKE 'thread-reconstruct-%';


class TestThreadReconstructionScenarios:
    """Tests des 3 scénarios de reconstruction de threads.
    
    ⚠️ ATTENTION - Problème de Mocking (Avril 2025):
    ================================================
    Les tests échouent actuellement car le mocking de Gmail API ne fonctionne pas.
    
    Problème:
    ---------
    Le service `thread_reconstruction_service.py` importe `create_gmail_client` 
    DYNAMIQUEMENT à l'intérieur de la méthode `_reconstruct_from_gmail_api()`:
    
        from app.services.emails.gmail_client import create_gmail_client
        gmail_client = create_gmail_client(...)
    
    Cela rend le patching avec `unittest.mock.patch` impossible car l'import
    est fait au moment de l'exécution, pas au chargement du module.
    
    Erreur obtenue:
    ---------------
        Gmail API error: {'message': 'Cannot coerce the result...', 'code': 'PGRST116'}
        'NoneType' object has no attribute 'data'
    
    Solutions possibles:
    --------------------
    1. Refactoriser le service pour accepter gmail_client en injection de dépendance
    2. Utiliser patch au niveau de sys.modules avant l'import du service
    3. Créer un script de test manuel qui injecte directement les emails en DB
    4. Tester avec de vrais appels Gmail API (nécessite vrai refresh_token)
    
    Status: Les tests sont structurés mais ne passent PAS actuellement.
    Les données des fixtures sont correctes et peuvent être utilisées manuellement.
    """
    
    # TODO: Corriger le mocking ou refactoriser le service pour injection de dépendance
    
    def load_fixture(self, filename: str) -> dict:
        """Charge une fixture JSON."""
        filepath = Path(__file__).parent / "data" / "emails" / filename
        with open(filepath, "r") as f:
            return json.load(f)
    
    def get_test_email_account_id(self) -> str:
        """Retourne l'ID du compte email de test (REDACTED_EMAIL)."""
        return TEST_EMAIL_ACCOUNT_ID
    
    def cleanup_test_data(self, gmail_thread_id: str):
        """Nettoie les données de test - DÉSACTIVÉ pour visualisation UI.
        
        Pour nettoyer manuellement:
        DELETE FROM emails WHERE gmail_thread_id LIKE 'thread-reconstruct-%' AND org_id = '...';
        DELETE FROM email_threads WHERE gmail_thread_id LIKE 'thread-reconstruct-%' AND org_id = '...';
        """
        # NOTE: Nettoyage désactivé - les données restent visibles dans l'UI
        # pour démonstration des scénarios de reconstruction
        pass
    
    def inject_email_direct(self, email_data: dict, account_id: str) -> str:
        """Injecte un email directement en DB."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        unique_suffix = f"-{uuid4().hex[:8]}"
        
        email_db_data = {
            "org_id": TEST_ORG_ID,
            "company_id": TEST_COMPANY_ID,
            "email_account_id": account_id,
            "gmail_thread_id": email_data["gmail_thread_id"],
            "gmail_message_id": f"{email_data.get('gmail_message_id', 'msg')}{unique_suffix}",
            "subject": email_data.get("subject", "Test"),
            "sender_email": email_data.get("from", "test@example.com"),
            "sender_name": email_data.get("from_name", "Test"),
            "content_text": email_data.get("body", ""),
            "sent_at": datetime.utcnow().isoformat(),
            "received_at": datetime.utcnow().isoformat(),
            "processing_status": "pending",
            "routing_status": "routed",
            "delivered_to_alias": f"REDACTED_EMAIL"
        }
        
        response = supabase.table("emails").insert(email_db_data).execute()
        return response.data[0]["id"]
    
    def get_thread_by_gmail_id(self, gmail_thread_id: str) -> dict:
        """Récupère un thread par son gmail_thread_id."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        response = supabase.table("email_threads")\
            .select("*")\
            .eq("gmail_thread_id", gmail_thread_id)\
            .eq("org_id", TEST_ORG_ID)\
            .maybe_single()\
            .execute()
        
        return response.data
    
    def count_emails_in_thread(self, gmail_thread_id: str) -> int:
        """Compte les emails d'un thread."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        response = supabase.table("emails")\
            .select("count", count="exact")\
            .eq("gmail_thread_id", gmail_thread_id)\
            .eq("org_id", TEST_ORG_ID)\
            .execute()
        
        return response.count if hasattr(response, 'count') else len(response.data)

    @pytest.mark.asyncio
    async def test_scenario_1_easy_gmail_api_success(self):
        """
        Scénario 1 (Easy): Gmail API fonctionne - reconstruction complète.
        
        STATUS: ⚠️ BROKEN - Mocking ne fonctionne pas (voir docstring classe)
        
        Given:
            - Thread inexistant en DB
            - Gmail API retourne 3 messages historiques
        When:
            - Email arrive avec ce thread_id
        Then:
            - 3 emails importés en DB
            - Thread créé avec email_count=3
            - is_historical_partial=false
            - historical_notes indique succès Gmail API
        
        TODO: Corriger le mocking de create_gmail_client ou refactoriser en injection de dépendance
        """
        print("\n🧪 Scénario 1: Gmail API fonctionne (Easy)")
        
        # Charger la fixture
        fixture = self.load_fixture("email_thread_reconstruction_1_easy_gmail.json")
        gmail_thread_id = fixture["gmail_thread_id"]
        
        # Cleanup préalable
        # NOTE: Pas de nettoyage - données visibles dans l\'UI
        # self.cleanup_test_data(gmail_thread_id)
        
        # Créer compte email
        account_id = self.get_test_email_account_id()
        print(f"✅ Compte email créé")
        
        # Mock Gmail API pour simuler 3 messages
        mock_messages = fixture["simulated_gmail_messages"]
        
        with patch('app.services.emails.gmail_client.create_gmail_client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Configurer le mock pour retourner les 3 messages
            mock_service = MagicMock()
            mock_client.service = mock_service
            mock_client._client = MagicMock()
            
            # Simuler la réponse de l'API threads().get()
            mock_thread_response = {
                "messages": [
                    {"id": msg["gmail_message_id"]} for msg in mock_messages
                ]
            }
            mock_service.users.return_value.threads.return_value.get.return_value.execute.return_value = mock_thread_response
            
            # Simuler get_message pour chaque message
            async def mock_get_message(msg_id):
                for msg in mock_messages:
                    if msg["gmail_message_id"] == msg_id:
                        return {
                            "id": msg_id,
                            "threadId": gmail_thread_id,
                            "payload": {
                                "headers": [
                                    {"name": "From", "value": msg["from"]},
                                    {"name": "Subject", "value": msg["subject"]},
                                    {"name": "Date", "value": msg["date"]}
                                ],
                                "body": {"data": msg["body"]}
                            }
                        }
                return {}
            
            mock_client.get_message = mock_get_message
            mock_client.connect = asyncio.coroutine(lambda: None)
            
            # Injecter l'email entrant (le 3ème message)
            incoming_msg = mock_messages[fixture["incoming_email_index"]]
            email_data = {
                "gmail_thread_id": gmail_thread_id,
                "gmail_message_id": incoming_msg["gmail_message_id"],
                "subject": incoming_msg["subject"],
                "from": incoming_msg["from"],
                "from_name": incoming_msg["from_name"],
                "body": incoming_msg["body"]
            }
            
            email_id = self.inject_email_direct(email_data, account_id)
            print(f"✅ Email injecté: {email_id[:8]}...")
            
            # Exécuter la reconstruction
            from app.services.thread_reconstruction_service import thread_reconstruction_service
            
            success, thread_data, status = await thread_reconstruction_service.reconstruct_thread(
                gmail_thread_id=gmail_thread_id,
                org_id=UUID(TEST_ORG_ID),
                company_id=UUID(TEST_COMPANY_ID),
                current_email_id=email_id
            )
            
            print(f"✅ Reconstruction terminée: status={status}")
        
        # Vérifications
        assert success is True, "La reconstruction devrait réussir"
        assert status == "complete", f"Status attendu: complete, obtenu: {status}"
        
        # Vérifier le thread en DB
        thread = self.get_thread_by_gmail_id(gmail_thread_id)
        assert thread is not None, "Le thread devrait exister en DB"
        assert thread["email_count"] == 3, f"email_count attendu: 3, obtenu: {thread['email_count']}"
        assert thread["is_historical_partial"] is False, "is_historical_partial devrait être False"
        
        # Vérifier historical_notes
        notes = json.loads(thread["historical_notes"])
        assert notes["gmail_api_success"] is True, "gmail_api_success devrait être True"
        
        # Vérifier le nombre d'emails en DB
        email_count = self.count_emails_in_thread(gmail_thread_id)
        assert email_count == 3, f"Nombre d'emails en DB attendu: 3, obtenu: {email_count}"
        
        print(f"✅ Scénario 1 validé: {email_count} emails, thread complet")
        
        # Cleanup
        # NOTE: Pas de nettoyage - données visibles dans l\'UI
        # self.cleanup_test_data(gmail_thread_id)

    @pytest.mark.asyncio
    @pytest.mark.slow  # Appel réel à Gemini (~0.001€)
    async def test_scenario_2_hybrid_gemini_extraction(self):
        """
        Scénario 2 (Hybride): Gmail API échoue, Gemini extrait.
        
        STATUS: ⚠️ BROKEN - Mocking ne fonctionne pas (voir docstring classe)
        
        Given:
            - Forward Outlook avec historique cité
            - Gmail API retourne erreur
        When:
            - Email arrive
        Then:
            - 1 email en DB (le reçu)
            - Thread is_historical_partial=true
            - historical_notes contient extraction Gemini
            - Coût Gemini ~0.001€
        
        TODO: Corriger le mocking ou refactoriser en injection de dépendance
        """
        print("\n🧪 Scénario 2: Gemini extraction (Hybride) - Coût ~0.001€")
        
        # Charger la fixture
        fixture = self.load_fixture("email_thread_reconstruction_2_hybrid.json")
        gmail_thread_id = fixture["gmail_thread_id"]
        
        # Cleanup préalable
        # NOTE: Pas de nettoyage - données visibles dans l\'UI
        # self.cleanup_test_data(gmail_thread_id)
        
        # Créer compte email
        account_id = self.get_test_email_account_id()
        print(f"✅ Compte email créé")
        
        # Mock Gmail API pour qu'elle échoue
        with patch('app.services.emails.gmail_client.create_gmail_client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.connect = asyncio.coroutine(lambda: None)
            
            # Simuler une erreur de l'API
            from googleapiclient.errors import HttpError
            mock_service = MagicMock()
            mock_client.service = mock_service
            mock_service.users.return_value.threads.return_value.get.return_value.execute.side_effect = HttpError(
                resp=Mock(status=404),
                content=b'{"error": {"message": "Thread not found"}}'
            )
            
            # Injecter l'email avec le forward
            forward_content = fixture["forward_content"]
            body_text = forward_content["body_text"]
            
            email_data = {
                "gmail_thread_id": gmail_thread_id,
                "gmail_message_id": "msg-hybrid-test-001",
                "subject": fixture["forward_headers"]["Subject"],
                "from": fixture["forward_headers"]["From"],
                "from_name": "ACORUS",
                "body": body_text
            }
            
            email_id = self.inject_email_direct(email_data, account_id)
            print(f"✅ Email forward injecté: {email_id[:8]}...")
            print(f"🤖 Appel à Gemini pour extraction...")
            
            # Exécuter la reconstruction (appel réel à Gemini)
            from app.services.thread_reconstruction_service import thread_reconstruction_service
            
            success, thread_data, status = await thread_reconstruction_service.reconstruct_thread(
                gmail_thread_id=gmail_thread_id,
                org_id=UUID(TEST_ORG_ID),
                company_id=UUID(TEST_COMPANY_ID),
                current_email_id=email_id
            )
            
            print(f"✅ Reconstruction terminée: status={status}")
        
        # Vérifications
        assert success is True, "La reconstruction devrait réussir (fallback)"
        assert status == "minimal", f"Status attendu: minimal, obtenu: {status}"
        
        # Vérifier le thread en DB
        thread = self.get_thread_by_gmail_id(gmail_thread_id)
        assert thread is not None, "Le thread devrait exister"
        assert thread["email_count"] == 1, f"email_count attendu: 1, obtenu: {thread['email_count']}"
        assert thread["is_historical_partial"] is True, "is_historical_partial devrait être True"
        
        # Vérifier historical_notes contient l'extraction Gemini
        assert thread["historical_notes"] is not None, "historical_notes ne devrait pas être null"
        notes = json.loads(thread["historical_notes"])
        
        assert notes["gmail_api_success"] is False, "gmail_api_success devrait être False"
        assert "gemini_extraction" in notes, "historical_notes devrait contenir gemini_extraction"
        
        gemini_data = notes["gemini_extraction"]
        if gemini_data and gemini_data.get("success"):
            print(f"✅ Gemini a extrait {len(gemini_data.get('emails', []))} emails")
            assert len(gemini_data.get("emails", [])) >= 1, "Au moins 1 email devrait être extrait"
            assert gemini_data.get("confiance", 0) > 0.5, "Confiance devrait être > 0.5"
        
        print(f"✅ Scénario 2 validé: thread partiel avec extraction Gemini")
        
        # Cleanup
        # NOTE: Pas de nettoyage - données visibles dans l\'UI
        # self.cleanup_test_data(gmail_thread_id)

    @pytest.mark.asyncio
    async def test_scenario_3_fallback_minimal(self):
        """
        Scénario 3 (Fallback): Tout échoue, thread minimal.
        
        STATUS: ⚠️ BROKEN - Mocking ne fonctionne pas (voir docstring classe)
        
        Given:
            - Forward corrompu/illisible
            - Gmail API échoue
            - Gemini retourne erreur
        When:
            - Email arrive
        Then:
            - 1 email en DB
            - Thread is_historical_partial=true
            - historical_notes contient logs d'erreurs
            - Aucune exception levée
        
        TODO: Corriger le mocking ou refactoriser en injection de dépendance
        """
        print("\n🧪 Scénario 3: Fallback minimal (Tout échoue)")
        
        # Charger la fixture
        fixture = self.load_fixture("email_thread_reconstruction_3_fallback.json")
        gmail_thread_id = fixture["gmail_thread_id"]
        
        # Cleanup préalable
        # NOTE: Pas de nettoyage - données visibles dans l\'UI
        # self.cleanup_test_data(gmail_thread_id)
        
        # Créer compte email
        account_id = self.get_test_email_account_id()
        print(f"✅ Compte email créé")
        
        # Mocker Gmail API (échec)
        with patch('app.services.emails.gmail_client.create_gmail_client') as mock_gmail_client:
            mock_gmail_client.side_effect = Exception("Connection timeout")
            
            # Mocker Gemini (échec)
            with patch.object(
                'app.services.thread_reconstruction_service.ThreadReconstructionService',
                '_extract_history_with_gemini',
                return_value={
                    "success": False,
                    "confiance": 0,
                    "emails": [],
                    "note": "Extraction impossible - corps illisible"
                }
            ):
                # Injecter l'email corrompu
                email_data = {
                    "gmail_thread_id": gmail_thread_id,
                    "gmail_message_id": "msg-fallback-test-001",
                    "subject": "=?UTF-8?B?RGV2aXM=?=",
                    "from": "unknown@external.com",
                    "from_name": "Unknown",
                    "body": fixture["forward_content"]["body_text"]
                }
                
                email_id = self.inject_email_direct(email_data, account_id)
                print(f"✅ Email corrompu injecté: {email_id[:8]}...")
                
                # Exécuter la reconstruction
                from app.services.thread_reconstruction_service import thread_reconstruction_service
                
                # Ne devrait PAS lever d'exception
                try:
                    success, thread_data, status = await thread_reconstruction_service.reconstruct_thread(
                        gmail_thread_id=gmail_thread_id,
                        org_id=UUID(TEST_ORG_ID),
                        company_id=UUID(TEST_COMPANY_ID),
                        current_email_id=email_id
                    )
                    print(f"✅ Reconstruction terminée sans erreur: status={status}")
                except Exception as e:
                    pytest.fail(f"La reconstruction ne devrait PAS lever d'exception: {e}")
        
        # Vérifications
        assert success is True, "La reconstruction devrait réussir (fallback)"
        assert status == "minimal", f"Status attendu: minimal, obtenu: {status}"
        
        # Vérifier le thread en DB
        thread = self.get_thread_by_gmail_id(gmail_thread_id)
        assert thread is not None, "Le thread devrait exister"
        assert thread["email_count"] == 1, f"email_count attendu: 1, obtenu: {thread['email_count']}"
        assert thread["is_historical_partial"] is True, "is_historical_partial devrait être True"
        
        # Vérifier historical_notes contient les logs
        assert thread["historical_notes"] is not None, "historical_notes ne devrait pas être null"
        notes = json.loads(thread["historical_notes"])
        
        assert "gmail_api_success" in notes, "historical_notes devrait contenir gmail_api_success"
        assert notes["gmail_api_success"] is False, "gmail_api_success devrait être False"
        assert "fallback" in notes.get("strategy_used", "").lower() or "minimal" in notes.get("strategy_used", "").lower(), \
            "strategy_used devrait indiquer fallback"
        
        print(f"✅ Scénario 3 validé: thread minimal créé sans erreur")
        
        # Cleanup
        # NOTE: Pas de nettoyage - données visibles dans l\'UI
        # self.cleanup_test_data(gmail_thread_id)


class TestThreadReconstructionEdgeCases:
    """Tests des cas limites de reconstruction."""
    
    def test_should_reconstruct_new_thread(self):
        """Test: Détecte qu'un nouveau thread nécessite reconstruction."""
        from app.services.thread_reconstruction_service import thread_reconstruction_service
        
        gmail_thread_id = f"thread-new-{uuid4().hex[:8]}"
        
        should_reconstruct, reason = thread_reconstruction_service.should_attempt_reconstruction(
            gmail_thread_id=gmail_thread_id,
            org_id=UUID(TEST_ORG_ID)
        )
        
        assert should_reconstruct is True
        assert "Nouveau thread" in reason
    
    def test_should_not_reconstruct_existing_complete_thread(self):
        """Test: Ne reconstruit pas un thread déjà complet."""
        # Ce test nécessite un thread existant avec plusieurs emails
        # Pour l'instant, on skip si pas de données
        pytest.skip("Nécessite un thread existant en DB")


# Markers pour les tests
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]
