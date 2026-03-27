#!/usr/bin/env python3
"""
Tests pour le Bot Telegram Construction - Black Box Testing

Ces tests valident le comportement du backend sans appeler l'API Telegram réelle.
On mock toutes les interactions externes (httpx, Supabase).

Scénarios testés:
1. Webhook handler - routing des updates Telegram
2. Parsing invitation - décodage payload base64
3. Liaison compte - création entrée telegram_users
4. Extraction OCR - structure des données (dummy)
5. Création facture - invoice en status brouillon
6. Validation callback - changement status + notification
7. Notification admins - génération message + lien
8. Génération invitation - création lien signé
9. Registry bots - chargement depuis env vars
10. Sécurité webhook - vérification secret token
"""

import sys
import os
import uuid
import json
import base64
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration test - AVANT tous les imports
os.environ["ENVIRONMENT"] = "test"
os.environ["SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN"] = "test_token_12345"
os.environ["TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME"] = "test_construction_bot"
os.environ["TEST_TELEGRAM_AUDIT_BOT_TOKEN"] = ""
os.environ["TEST_TELEGRAM_NETTOYAGE_BOT_TOKEN"] = ""
os.environ["TELEGRAM_INVITATION_SECRET"] = "test_secret_for_invitations_32_chars"

from fastapi.testclient import TestClient

from app.main import app
from app.services.telegram_invitation_service import TelegramInvitationService
from app.services.telegram.bots_registry import TelegramBotsRegistry

client = TestClient(app)


# ==================== FIXTURES ====================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("app.api.auth.get_supabase") as mock:
        supabase_mock = Mock()
        mock.return_value = supabase_mock
        yield supabase_mock


@pytest.fixture
def mock_auth():
    """Mock authentication for admin endpoints."""
    with patch("app.api.auth.get_current_user_from_cookie") as mock:
        mock.return_value = {
            "sub": str(uuid.uuid4()),
            "email": "admin@test.com",
            "org_id": str(uuid.uuid4()),
            "role": "admin"
        }
        yield mock


@pytest.fixture
def mock_verify_admin():
    """Mock verify_admin dependency."""
    with patch("app.api.admin.verify_admin") as mock:
        mock.return_value = {
            "user_id": str(uuid.uuid4()),
            "org_id": str(uuid.uuid4()),
            "role": "admin"
        }
        yield mock


@pytest.fixture
def sample_telegram_user():
    """Données utilisateur Telegram de test."""
    return {
        "id": 123456789,
        "is_bot": False,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser"
    }


@pytest.fixture
def sample_organization():
    """Organisation de test."""
    return {
        "id": str(uuid.uuid4()),
        "slug": "test-construction",
        "name": "Test Construction"
    }


@pytest.fixture
def sample_user():
    """Utilisateur de test."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "full_name": "Test User",
        "org_id": str(uuid.uuid4()),
        "role": "user"
    }


@pytest.fixture
def sample_invoice():
    """Facture de test."""
    return {
        "id": str(uuid.uuid4()),
        "org_id": str(uuid.uuid4()),
        "supplier_name": "Fournisseur Test",
        "amount_ttc": 1250.50,
        "status": "brouillon",
        "created_by_telegram": True,
        "created_by": str(uuid.uuid4())
    }


# ==================== TESTS WEBHOOK HANDLER ====================

class TestWebhookHandler:
    """Tests pour le endpoint webhook /webhook/construction"""
    
    def test_webhook_health_check(self):
        """Test 1: Health check du webhook"""
        with patch.dict(os.environ, {"SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN": "test_token", 
                                     "TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME": "test_bot"}):
            # Recréer le registry avec les nouvelles valeurs
            registry = TelegramBotsRegistry()
            
            response = client.get("/api/v1/webhook/construction/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["environment"] == "test"
    
    @patch("app.services.telegram.construction_bot_service.ConstructionBotService.handle_update")
    def test_webhook_receives_message(self, mock_handle_update):
        """Test 1a: Webhook reçoit un message et route vers handle_update"""
        mock_handle_update.return_value = {"status": "message_processed"}
        
        update_payload = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": 123456789,
                    "type": "private"
                },
                "date": int(datetime.now().timestamp()),
                "text": "/start"
            }
        }
        
        response = client.post(
            "/api/v1/webhook/construction",
            json=update_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["result"]["status"] == "message_processed"
        mock_handle_update.assert_called_once_with(update_payload)
    
    @patch("app.services.telegram.construction_bot_service.ConstructionBotService.handle_update")
    def test_webhook_receives_callback_query(self, mock_handle_update):
        """Test 1b: Webhook reçoit un callback_query et route vers handle_update"""
        mock_handle_update.return_value = {"status": "callback_handled"}
        
        update_payload = {
            "update_id": 123456790,
            "callback_query": {
                "id": "12345",
                "from": {
                    "id": 123456789,
                    "is_bot": False,
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 1,
                    "chat": {"id": 123456789, "type": "private"},
                    "date": int(datetime.now().timestamp())
                },
                "data": "validate_invoice:test-id"
            }
        }
        
        response = client.post(
            "/api/v1/webhook/construction",
            json=update_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        mock_handle_update.assert_called_once_with(update_payload)
    
    @patch("app.services.telegram.construction_bot_service.ConstructionBotService.handle_update")
    def test_webhook_with_photo(self, mock_handle_update):
        """Test 1c: Webhook reçoit une photo"""
        mock_handle_update.return_value = {"status": "photo_received"}
        
        update_payload = {
            "update_id": 123456791,
            "message": {
                "message_id": 2,
                "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "date": int(datetime.now().timestamp()),
                "photo": [
                    {"file_id": "small_file_id", "file_unique_id": "small", "width": 320, "height": 240},
                    {"file_id": "large_file_id", "file_unique_id": "large", "width": 1280, "height": 960}
                ]
            }
        }
        
        response = client.post(
            "/api/v1/webhook/construction",
            json=update_payload
        )
        
        assert response.status_code == 200
        mock_handle_update.assert_called_once()


# ==================== TESTS PARSING INVITATION ====================

class TestInvitationParsing:
    """Tests pour le parsing des invitations Telegram"""
    
    def test_decode_valid_payload(self):
        """Test 2: Décoder un payload d'invitation valide"""
        # Créer service avec registry mock
        service = TelegramInvitationService()
        
        # Mock du registry pour retourner un bot
        with patch.object(service, 'get_bot_config') as mock_get_bot:
            mock_get_bot.return_value = Mock(
                username="test_construction_bot",
                bot_name="Construction",
                icon="🏗️",
                description="Test"
            )
            
            user_id = str(uuid.uuid4())
            org_id = str(uuid.uuid4())
            bot_id = "construction"
            
            # Générer un payload valide
            invitation = service.generate_invitation_link(user_id, org_id, bot_id)
            payload_b64 = invitation["telegram_link"].split("start=")[1]
            
            # Décoder
            result = service.decode_invitation_payload(payload_b64)
            
            assert result is not None
            assert result["user_id"] == user_id
            assert result["org_id"] == org_id
            assert result["bot_id"] == bot_id
            assert "expires_at" in result
    
    def test_decode_expired_payload(self):
        """Test 2a: Rejeter un payload expiré"""
        service = TelegramInvitationService()
        
        # Créer un payload expiré manuellement
        expired_timestamp = int((datetime.utcnow() - timedelta(days=1)).timestamp())
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        bot_id = "construction"
        
        sig = service._generate_signature(user_id, org_id, bot_id, expired_timestamp)
        
        payload = {
            "u": user_id,
            "o": org_id,
            "b": bot_id,
            "e": expired_timestamp,
            "s": sig
        }
        
        payload_json = json.dumps(payload, separators=(',', ':'))
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
        
        result = service.decode_invitation_payload(payload_b64)
        
        assert result is None  # Doit être rejeté car expiré
    
    def test_decode_invalid_signature(self):
        """Test 2b: Rejeter un payload avec signature invalide"""
        service = TelegramInvitationService()
        
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        bot_id = "construction"
        exp = int((datetime.utcnow() + timedelta(days=7)).timestamp())
        
        # Créer payload avec mauvaise signature
        payload = {
            "u": user_id,
            "o": org_id,
            "b": bot_id,
            "e": exp,
            "s": "invalid_signature"
        }
        
        payload_json = json.dumps(payload, separators=(',', ':'))
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
        
        result = service.decode_invitation_payload(payload_b64)
        
        assert result is None  # Doit être rejeté car signature invalide
    
    def test_decode_malformed_payload(self):
        """Test 2c: Rejeter un payload malformé"""
        service = TelegramInvitationService()
        
        result = service.decode_invitation_payload("not_valid_base64!!!")
        
        assert result is None  # Doit être rejeté


# ==================== TESTS LIAISON COMPTE ====================

class TestAccountLinking:
    """Tests pour la liaison compte Telegram <> Utilisateur"""
    
    @pytest.mark.asyncio
    async def test_start_command_with_valid_invitation(self, mock_supabase, sample_telegram_user, sample_user):
        """Test 3: Commande /start avec payload valide crée liaison"""
        from app.services.telegram.construction_bot_service import ConstructionBotService
        
        service = ConstructionBotService()
        
        # Générer invitation
        with patch.object(service.invitation_service, 'get_bot_config') as mock_get_bot:
            mock_get_bot.return_value = Mock(
                username="test_construction_bot",
                bot_name="Construction",
                icon="🏗️",
                description="Test"
            )
            
            invitation = service.invitation_service.generate_invitation_link(
                sample_user["id"], 
                sample_user["org_id"],
                "construction"
            )
            payload_b64 = invitation["telegram_link"].split("start=")[1]
        
        # Simuler message /start
        message = {
            "message_id": 1,
            "from": sample_telegram_user,
            "chat": {"id": sample_telegram_user["id"], "type": "private"},
            "date": int(datetime.now().timestamp()),
            "text": f"/start {payload_b64}"
        }
        
        # Mock Supabase - pas d'utilisateur Telegram existant
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new_link_id"}]
        
        # Exécuter (sans mock httpx pour simplifier, on vérifie juste l'appel DB)
        with patch.object(service, '_send_message', new_callable=AsyncMock):
            with patch("app.services.telegram.construction_bot_service.get_supabase", return_value=mock_supabase):
                result = await service._handle_start_command(message)
                
                # Vérifier que l'insertion a été faite
                mock_supabase.table.assert_called()
                assert result["status"] == "account_linked"
                assert result["user_id"] == sample_user["id"]
    
    @pytest.mark.asyncio
    async def test_start_command_without_payload(self, mock_supabase, sample_telegram_user):
        """Test 3a: Commande /start sans payload = message d'aide"""
        from app.services.telegram.construction_bot_service import ConstructionBotService
        
        service = ConstructionBotService()
        
        message = {
            "message_id": 1,
            "from": sample_telegram_user,
            "chat": {"id": sample_telegram_user["id"], "type": "private"},
            "date": int(datetime.now().timestamp()),
            "text": "/start"
        }
        
        with patch.object(service, '_send_message', new_callable=AsyncMock):
            result = await service._handle_start_command(message)
            
            assert result["status"] == "welcome_no_payload"


# ==================== TESTS OCR EXTRACTION ====================

class TestOCRExtraction:
    """Tests pour l'extraction OCR (dummy pour l'instant)"""
    
    @pytest.mark.asyncio
    async def test_extract_from_document_returns_structure(self):
        """Test 4: L'OCR retourne une structure ExtractedInvoiceData valide"""
        from app.agents.construction_invoice_agent import ConstructionInvoiceAgent
        
        agent = ConstructionInvoiceAgent()
        
        # Appeler avec URL mock
        result = await agent.extract_from_document(
            file_url="telegram://test_file_id",
            file_type="photo"
        )
        
        # Vérifier structure (même avec données dummy)
        assert result.supplier_name is not None
        assert isinstance(result.amount_ttc, (int, float))
        assert result.amount_ttc > 0
        assert result.invoice_date is not None
        assert result.line_items is not None
        assert len(result.line_items) > 0
        assert result.confidence_score > 0
        assert result.extraction_method == "dummy_v1"
    
    @pytest.mark.asyncio
    async def test_validate_extraction_detects_errors(self):
        """Test 4a: La validation détecte les erreurs dans les données"""
        from app.agents.construction_invoice_agent import ConstructionInvoiceAgent, ExtractedInvoiceData
        
        agent = ConstructionInvoiceAgent()
        
        # Données invalides (manque supplier_name)
        invalid_data = ExtractedInvoiceData(
            supplier_name="",
            amount_ttc=-100,
            invoice_date=None
        )
        
        validation = await agent.validate_extraction(invalid_data)
        
        assert validation["valid"] == False
        assert len(validation["errors"]) > 0


# ==================== TESTS CRÉATION FACTURE ====================

class TestInvoiceCreation:
    """Tests pour la création de facture depuis Telegram"""
    
    @pytest.mark.asyncio
    async def test_file_received_creates_draft_invoice(self, mock_supabase, sample_telegram_user, sample_user, sample_invoice):
        """Test 5: Réception fichier crée facture en brouillon"""
        from app.services.telegram.construction_bot_service import ConstructionBotService
        
        service = ConstructionBotService()
        
        # Mock utilisateur lié
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "user_id": sample_user["id"],
            "org_id": sample_user["org_id"],
            "telegram_id": sample_telegram_user["id"]
        }
        
        # Mock création facture
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [sample_invoice]
        
        message = {
            "message_id": 2,
            "from": sample_telegram_user,
            "chat": {"id": sample_telegram_user["id"], "type": "private"},
            "date": int(datetime.now().timestamp()),
            "photo": [{"file_id": "test_file_id", "file_unique_id": "test", "width": 100, "height": 100}]
        }
        
        with patch.object(service, '_send_message', new_callable=AsyncMock):
            with patch("app.services.telegram.construction_bot_service.get_supabase", return_value=mock_supabase):
                result = await service._handle_file_received(message)
                
                # Vérifier que la méthode retourne bien un statut
                assert "status" in result
                assert result["user_id"] == sample_user["id"]
    
    @pytest.mark.asyncio
    async def test_file_received_rejects_unlinked_user(self, mock_supabase, sample_telegram_user):
        """Test 5a: User non lié = refus"""
        from app.services.telegram.construction_bot_service import ConstructionBotService
        
        service = ConstructionBotService()
        
        # Mock utilisateur NON lié
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        
        message = {
            "message_id": 2,
            "from": sample_telegram_user,
            "chat": {"id": sample_telegram_user["id"], "type": "private"},
            "date": int(datetime.now().timestamp()),
            "photo": [{"file_id": "test_file_id", "file_unique_id": "test", "width": 100, "height": 100}]
        }
        
        with patch.object(service, '_send_message', new_callable=AsyncMock):
            with patch("app.services.telegram.construction_bot_service.get_supabase", return_value=mock_supabase):
                result = await service._handle_file_received(message)
                
                assert result["status"] == "user_not_linked"


# ==================== TESTS VALIDATION CALLBACK ====================

class TestValidationCallback:
    """Tests pour la validation via callback Telegram"""
    
    @pytest.mark.asyncio
    async def test_validate_invoice_changes_status(self, mock_supabase, sample_invoice):
        """Test 6: Validation change status facture brouillon → en_attente_validation"""
        from app.services.telegram.construction_bot_service import ConstructionBotService
        
        service = ConstructionBotService()
        
        # Mock facture existante
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_invoice
        
        # Mock update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{**sample_invoice, "status": "en_attente_validation"}]
        
        callback_query = {
            "id": "callback_123",
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "message": {"message_id": 10, "chat": {"id": 123456789, "type": "private"}},
            "data": f"validate_invoice:{sample_invoice['id']}"
        }
        
        with patch.object(service, '_send_message', new_callable=AsyncMock):
            with patch.object(service, '_answer_callback_query', new_callable=AsyncMock):
                with patch.object(service, '_notify_admins_new_invoice', new_callable=AsyncMock) as mock_notify:
                    result = await service._handle_callback_query(callback_query)
                    
                    assert result["status"] == "invoice_validated"
                    assert result["invoice_id"] == sample_invoice["id"]
                    mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_invoice_deletes_draft(self, mock_supabase, sample_invoice):
        """Test 6a: Annulation supprime facture brouillon"""
        from app.services.telegram.construction_bot_service import ConstructionBotService
        
        service = ConstructionBotService()
        
        callback_query = {
            "id": "callback_124",
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "message": {"message_id": 10, "chat": {"id": 123456789, "type": "private"}},
            "data": f"cancel_invoice:{sample_invoice['id']}"
        }
        
        with patch.object(service, '_send_message', new_callable=AsyncMock):
            with patch.object(service, '_answer_callback_query', new_callable=AsyncMock):
                result = await service._handle_callback_query(callback_query)
                
                assert result["status"] == "invoice_cancelled"
                assert result["invoice_id"] == sample_invoice["id"]


# ==================== TESTS NOTIFICATION ADMINS ====================

class TestAdminNotifications:
    """Tests pour les notifications aux admins"""
    
    @pytest.mark.asyncio
    async def test_notify_admins_sends_messages(self, mock_supabase, sample_invoice, sample_organization):
        """Test 7: Notification envoie message à tous les admins avec lien"""
        from app.services.telegram.construction_bot_service import ConstructionBotService
        
        service = ConstructionBotService()
        
        # Mock facture avec infos utilisateur
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            **sample_invoice,
            "users": {"email": "user@test.com", "full_name": "Test User"},
            "companies": {"name": "Test Company"}
        }
        
        # Mock organisation
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = sample_organization
        
        # Mock admins avec Telegram
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"user_id": "admin1", "telegram_users": {"telegram_id": 111111}},
            {"user_id": "admin2", "telegram_users": {"telegram_id": 222222}}
        ]
        
        with patch.object(service, '_send_message', new_callable=AsyncMock) as mock_send:
            with patch("app.services.telegram.construction_bot_service.get_supabase", return_value=mock_supabase):
                await service._notify_admins_new_invoice(sample_invoice["id"], 123456789)
                
                # Vérifier que les messages ont été envoyés aux admins (pas à l'expéditeur)
                assert mock_send.call_count == 2
                
                # Vérifier que le message contient le lien
                calls = mock_send.call_args_list
                for call in calls:
                    args = call[0]
                    assert sample_organization["slug"] in args[1]  # Message contient le slug
                    assert sample_invoice["id"] in args[1]  # Message contient l'ID facture


# ==================== TESTS GÉNÉRATION INVITATION ====================

class TestInvitationGeneration:
    """Tests pour l'API de génération d'invitation"""
    
    @patch("app.api.admin.verify_admin")
    def test_generate_invitation_requires_bot_id(self, mock_verify_admin):
        """Test 8: Génération d'invitation requiert bot_id"""
        user_id = str(uuid.uuid4())
        
        mock_verify_admin.return_value = {"user_id": str(uuid.uuid4()), "org_id": str(uuid.uuid4()), "role": "admin"}
        
        response = client.post(
            f"/api/v1/admin/users/{user_id}/telegram-invitation",
            json={}  # Pas de bot_id
        )
        
        assert response.status_code == 400
        assert "bot_id" in response.json()["detail"].lower() or "requis" in response.json()["detail"].lower()
    
    @patch("app.api.admin.verify_admin")
    def test_generate_invitation_rejects_invalid_bot(self, mock_verify_admin):
        """Test 8a: Génération refuse bot invalide"""
        user_id = str(uuid.uuid4())
        
        mock_verify_admin.return_value = {"user_id": str(uuid.uuid4()), "org_id": str(uuid.uuid4()), "role": "admin"}
        
        response = client.post(
            f"/api/v1/admin/users/{user_id}/telegram-invitation",
            json={"bot_id": "invalid_bot_not_configured"}
        )
        
        assert response.status_code == 400


# ==================== TESTS REGISTRY BOTS ====================

class TestBotRegistry:
    """Tests pour le registre des bots"""
    
    def test_list_available_bots(self):
        """Test 9: Liste les bots configurés"""
        # Créer un registry avec les variables d'env configurées
        with patch.dict(os.environ, {
            "SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN": "test_token",
            "TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME": "test_construction_bot"
        }):
            registry = TelegramBotsRegistry()
            
            bots = registry.get_available_bots_for_display()
            
            # Au moins le bot construction doit être configuré
            assert len(bots) >= 1
            
            construction_bot = next((b for b in bots if b["bot_id"] == "construction"), None)
            assert construction_bot is not None
            assert construction_bot["configured"] == True
            assert construction_bot["username"] == "test_construction_bot"
    
    def test_get_bot_config(self):
        """Test 9a: Récupère config d'un bot spécifique"""
        with patch.dict(os.environ, {
            "SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN": "test_token",
            "TEST_TELEGRAM_CONSTRUCTION_BOT_USERNAME": "test_construction_bot"
        }):
            registry = TelegramBotsRegistry()
            
            bot_config = registry.get_bot("construction")
            
            assert bot_config is not None
            assert bot_config.bot_id == "construction"
            assert bot_config.username == "test_construction_bot"
    
    def test_get_unconfigured_bot_returns_none(self):
        """Test 9b: Bot non configuré retourne None"""
        with patch.dict(os.environ, {
            "TEST_TELEGRAM_AUDIT_BOT_TOKEN": ""  # Pas de token
        }):
            registry = TelegramBotsRegistry()
            
            # On n'a pas configuré le bot 'audit' dans les tests
            bot_config = registry.get_bot("audit")
            
            assert bot_config is None


# ==================== TESTS SÉCURITÉ WEBHOOK ====================

class TestWebhookSecurity:
    """Tests pour la sécurité du webhook"""
    
    def test_webhook_rejects_invalid_secret(self):
        """Test 10: Webhook avec secret invalide retourne 403"""
        # Configurer un secret
        os.environ["TELEGRAM_WEBHOOK_SECRET_TEST"] = "valid_secret_123"
        
        update_payload = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "date": int(datetime.now().timestamp()),
                "text": "test"
            }
        }
        
        response = client.post(
            "/api/v1/webhook/construction",
            json=update_payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_secret"}
        )
        
        assert response.status_code == 403
    
    @patch("app.services.telegram.construction_bot_service.ConstructionBotService.handle_update")
    def test_webhook_accepts_valid_secret(self, mock_handle_update):
        """Test 10a: Webhook avec secret valide fonctionne"""
        os.environ["TELEGRAM_WEBHOOK_SECRET_TEST"] = "valid_secret_123"
        mock_handle_update.return_value = {"status": "ok"}
        
        update_payload = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "date": int(datetime.now().timestamp()),
                "text": "test"
            }
        }
        
        response = client.post(
            "/api/v1/webhook/construction",
            json=update_payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "valid_secret_123"}
        )
        
        assert response.status_code == 200


# ==================== EXÉCUTION ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
