#!/usr/bin/env python3
"""
Tests pour les endpoints API Email Threads Management.

Approche TDD:
- Tests via routes API avec TestClient
- Mock des réponses IA pour l'instant
- Validation de l'affichage des données
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4, UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Configuration
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"
TEST_COMPANY_SLUG = "construction"


def get_test_org_and_company():
    """Récupère l'org_id et company_id depuis la DB."""
    from app.api.auth import get_supabase
    supabase = get_supabase()
    
    org_response = supabase.table("organizations")\
        .select("id")\
        .eq("slug", TEST_ORG_SLUG)\
        .single()\
        .execute()
    
    if not org_response.data:
        raise ValueError(f"Organization {TEST_ORG_SLUG} not found")
    
    org_id = org_response.data["id"]
    
    company_response = supabase.table("companies")\
        .select("id")\
        .eq("slug", TEST_COMPANY_SLUG)\
        .eq("org_id", org_id)\
        .single()\
        .execute()
    
    if not company_response.data:
        raise ValueError(f"Company {TEST_COMPANY_SLUG} not found")
    
    return org_id, company_response.data["id"]


TEST_ORG_ID, TEST_COMPANY_ID = get_test_org_and_company()


class TestEmailThreadsAPI:
    """Tests des endpoints API Email Threads."""
    
    def create_test_thread(self, subject: str = "Test Thread") -> dict:
        """Crée un thread de test en DB."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        thread_data = {
            "org_id": TEST_ORG_ID,
            "company_id": TEST_COMPANY_ID,
            "gmail_thread_id": f"thread-{uuid4().hex[:12]}",
            "subject": subject,
            "subject_cleaned": subject,
            "ai_summary": f"Résumé mocké pour {subject}",
            "ai_context": "Contexte mocké pour test",
            "ai_urgency": "high",
            "ai_status": "new",
            "participant_emails": ["client@test.com"],
            "participant_names": ["Client Test"],
            "email_count": 2,
            "attachment_count": 1,
            "first_email_at": datetime.utcnow().isoformat(),
            "last_email_at": datetime.utcnow().isoformat(),
            "is_archived": False,
            "is_starred": False
        }
        
        response = supabase.table("email_threads").insert(thread_data).execute()
        return response.data[0] if response.data else None
    
    def create_test_email_account(self) -> str:
        """Crée un compte email de test."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        account_data = {
            "org_id": TEST_ORG_ID,
            "email_address": f"test+{uuid4().hex[:8]}@gmail.com",
            "oauth_refresh_token": "test_token",
            "is_active": True,
            "sync_enabled": True
        }
        
        response = supabase.table("email_accounts").insert(account_data).execute()
        return response.data[0]["id"] if response.data else None
    
    def create_test_emails_for_thread(self, thread: dict, count: int = 2):
        """Crée des emails pour un thread."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        # Créer un compte email pour les tests
        account_id = self.create_test_email_account()
        
        emails = []
        for i in range(count):
            email_data = {
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_account_id": account_id,
                "gmail_thread_id": thread["gmail_thread_id"],
                "gmail_message_id": f"msg-{uuid4().hex[:12]}",
                "subject": thread["subject"],
                "sender_email": "client@test.com" if i % 2 == 0 else "moi@entreprise.fr",
                "sender_name": "Client Test" if i % 2 == 0 else "Moi",
                "content_text": f"Message {i+1} du thread",
                "sent_at": datetime.utcnow().isoformat(),
                "received_at": datetime.utcnow().isoformat(),
                "processing_status": "vectorized",
                "has_attachments": False,
                "attachments_count": 0
            }
            emails.append(email_data)
        
        supabase.table("emails").insert(emails).execute()
    
    def test_list_threads(self):
        """
        Scénario: Liste des threads pour une entreprise.
        
        Given: Une entreprise avec des threads
        When: GET /api/v1/{org}/email-threads?companyId={id}
        Then:
            - Status 200
            - Structure correcte (data, pagination)
            - Chaque thread a: id, subject, aiSummary, aiUrgency, metrics
        """
        # Créer un thread de test
        thread = self.create_test_thread("Test Liste Threads")
        
        # Appeler l'API
        response = client.get(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads",
            params={"company_id": TEST_COMPANY_ID}
        )
        
        # Vérifications
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        
        # Vérifier la structure d'un thread
        if data["data"]:
            first_thread = data["data"][0]
            assert "id" in first_thread
            assert "subject" in first_thread
            assert "ai_summary" in first_thread
            assert "ai_urgency" in first_thread
            assert "ai_status" in first_thread
            assert "metrics" in first_thread
            assert "flags" in first_thread
            assert "participants" in first_thread
    
    def test_list_threads_search(self):
        """
        Scénario: Recherche textuelle dans les threads.
        
        Given: Threads avec différents sujets
        When: GET /email-threads?search=Sanibatiment
        Then: Seulement les threads correspondants
        """
        # Créer threads avec sujets différents
        thread1 = self.create_test_thread("Devis Sanibatiment urgent")
        thread2 = self.create_test_thread("Facture EDF mensuelle")
        
        # Rechercher
        response = client.get(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads",
            params={
                "company_id": TEST_COMPANY_ID,
                "search": "Sanibatiment"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier que le résultat contient le bon thread
        subjects = [t["subject"] for t in data["data"]]
        assert any("Sanibatiment" in s for s in subjects)
    
    def test_list_threads_pagination(self):
        """
        Scénario: Pagination de la liste.
        
        When: GET /email-threads?page=1&limit=5
        Then:
            - 5 threads max
            - pagination.total défini
            - pagination.total_pages défini
        """
        # Créer plusieurs threads
        for i in range(7):
            self.create_test_thread(f"Thread pagination {i}")
        
        response = client.get(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads",
            params={
                "company_id": TEST_COMPANY_ID,
                "page": 1,
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) <= 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 5
        assert data["pagination"]["total"] >= 7
        assert data["pagination"]["total_pages"] >= 2
    
    def test_get_thread_detail(self):
        """
        Scénario: Détail d'un thread avec ses emails.
        
        Given: Un thread avec 2 emails
        When: GET /api/v1/{org}/email-threads/{id}
        Then:
            - Status 200
            - Thread avec aiSummary, aiUrgency, aiStatus
            - Tableau emails avec role (client/toi)
            - Session de chat présente
        """
        # Créer thread avec emails
        thread = self.create_test_thread("Test Détail Thread")
        self.create_test_emails_for_thread(thread, count=2)
        
        response = client.get(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{thread['id']}"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == thread["id"]
        assert data["subject"] == thread["subject"]
        assert "ai_summary" in data
        assert "ai_context" in data
        assert "ai_urgency" in data
        assert "ai_status" in data
        assert "emails" in data
        assert len(data["emails"]) == 2
        assert "chat_session" in data
    
    def test_get_thread_not_found(self):
        """
        Scénario: Thread inexistant.
        
        When: GET /email-threads/{invalidId}
        Then: Status 404
        """
        response = client.get(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{uuid4()}"
        )
        
        assert response.status_code == 404
    
    def test_get_thread_chat(self):
        """
        Scénario: Récupérer le chat d'un thread.
        
        Given: Thread avec session de chat
        When: GET /email-threads/{id}/chat
        Then:
            - Status 200
            - session avec id, name, isDefault
            - messages avec au moins le résumé system
        """
        # Créer thread (crée automatiquement une session)
        thread = self.create_test_thread("Test Chat")
        
        response = client.get(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{thread['id']}/chat"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "session" in data
        assert "messages" in data
        
        session = data["session"]
        assert "id" in session
        assert "name" in session
        assert "rag_context" in session
        
        # Vérifier qu'il y a au moins un message (le résumé system)
        assert len(data["messages"]) >= 1
        
        # Vérifier que le premier message est system
        first_msg = data["messages"][0]
        assert first_msg["role"] == "system"
        assert "Résumé du dossier" in first_msg["content"]
    
    def test_send_chat_message(self):
        """
        Scénario: Envoyer un message au chat.
        
        Given: Thread avec session de chat
        When: POST /email-threads/{id}/chat
              Body: { "message": "Question ?" }
        Then:
            - Status 200
            - user_message créé (role = user)
            - assistant_message créé (role = assistant)
            - Réponse cohérente
        """
        # Créer thread
        thread = self.create_test_thread("Test Envoi Message")
        
        response = client.post(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{thread['id']}/chat",
            json={"message": "Quel est le montant du devis ?"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "user_message" in data
        assert "assistant_message" in data
        
        user_msg = data["user_message"]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "Quel est le montant du devis ?"
        
        assistant_msg = data["assistant_message"]
        assert assistant_msg["role"] == "assistant"
        assert len(assistant_msg["content"]) > 0
    
    def test_update_thread_status(self):
        """
        Scénario: Mettre à jour le statut IA d'un thread.
        
        When: PATCH /email-threads/{id}
              Body: { "ai_status": "in_progress" }
        Then:
            - Status 200
            - ai_status mis à jour
        """
        thread = self.create_test_thread("Test Update Status")
        
        response = client.patch(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{thread['id']}",
            json={"ai_status": "in_progress"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["ai_status"] == "in_progress"
        
        # Vérifier en DB
        from app.api.auth import get_supabase
        supabase = get_supabase()
        updated = supabase.table("email_threads")\
            .select("ai_status")\
            .eq("id", thread["id"])\
            .single()\
            .execute()
        
        assert updated.data["ai_status"] == "in_progress"
    
    def test_star_thread(self):
        """
        Scénario: Marquer un thread comme favori.
        
        When: PATCH /email-threads/{id}
              Body: { "is_starred": true }
        Then: is_starred = true
        """
        thread = self.create_test_thread("Test Star")
        
        response = client.patch(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{thread['id']}",
            json={"is_starred": True}
        )
        
        assert response.status_code == 200
        assert response.json()["is_starred"] == True
    
    def test_archive_thread(self):
        """
        Scénario: Archiver un thread.
        
        When: PATCH /email-threads/{id}
              Body: { "is_archived": true }
        Then: is_archived = true
        """
        thread = self.create_test_thread("Test Archive")
        
        response = client.patch(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{thread['id']}",
            json={"is_archived": True}
        )
        
        assert response.status_code == 200
        assert response.json()["is_archived"] == True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
