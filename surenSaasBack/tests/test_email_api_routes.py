#!/usr/bin/env python3
"""
Tests pour le module Emails - Routes API

Scénarios:
1. Email forwardé simple avec PJ (recherche sémantique sur OCR)
2. Chaîne d'emails thread (recherche sémantique dans réponse)
3. Cas limites ignorés (no_alias, org_mismatch, company_not_found, invalid_format)
4. RAG Mail (extraction forward + nettoyage)

Approche:
- Test via les routes API avec TestClient (comme test_api_routes.py)
- Vrai appel à Vertex AI pour les embeddings
- Pas d'appel à Gmail (utilisation des fixtures JSON)
- Les emails sont injectés directement en DB pour simuler la synchro
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Configuration
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"
TEST_COMPANY_SLUG = "construction"

# Récupérer dynamiquement les IDs depuis la DB
def get_test_org_and_company():
    """Récupère l'org_id et company_id depuis la DB."""
    from app.api.auth import get_supabase
    supabase = get_supabase()
    
    # Get org
    org_response = supabase.table("organizations")\
        .select("id")\
        .eq("slug", TEST_ORG_SLUG)\
        .single()\
        .execute()
    
    if not org_response.data:
        raise ValueError(f"Organization {TEST_ORG_SLUG} not found in DB")
    
    org_id = org_response.data["id"]
    
    # Get company
    company_response = supabase.table("companies")\
        .select("id")\
        .eq("slug", TEST_COMPANY_SLUG)\
        .eq("org_id", org_id)\
        .single()\
        .execute()
    
    if not company_response.data:
        raise ValueError(f"Company {TEST_COMPANY_SLUG} not found in DB for org {TEST_ORG_SLUG}")
    
    company_id = company_response.data["id"]
    
    return org_id, company_id

# Initialiser les IDs au chargement du module
TEST_ORG_ID, TEST_COMPANY_ID = get_test_org_and_company()


def load_email_fixture(filename: str) -> dict:
    """Charge une fixture email JSON."""
    filepath = Path(__file__).parent / "data" / "emails" / filename
    with open(filepath, "r") as f:
        return json.load(f)


class TestEmailModule:
    """Tests du module Emails via API routes."""
    
    # def setup_method(self):
    #     """Setup avant chaque test."""
    #     # Cleanup de la DB de test
    #     # self.cleanup_test_data()
    
    # def teardown_method(self):
    #     """Cleanup après chaque test."""
    #     # self.cleanup_test_data()
    
    # def cleanup_test_data(self):
    #     """Nettoie les données de test."""
    #     from app.services.email_database_service import email_db
    #     import asyncio
    #     
    #     async def _cleanup():
    #         await email_db.cleanup_test_data()
    #     
    #     try:
    #         asyncio.run(_cleanup())
    #     except Exception as e:
    #         print(f"Cleanup error (may be normal if tables don't exist): {e}")
    
    def create_test_email_account(self) -> str:
        """Crée un compte email de test et retourne son ID."""
        from app.services.email_database_service import email_db
        import asyncio
        import uuid
        
        async def _create():
            # Utiliser un email unique pour éviter les conflits (pas de cleanup)
            unique_email = f"REDACTED_EMAIL_LOCAL+{uuid.uuid4().hex[:8]}@gmail.com"
            account_data = {
                "org_id": TEST_ORG_ID,
                "email_address": unique_email,
                "oauth_refresh_token": "test_refresh_token",
                "is_active": True,
                "sync_enabled": True
            }
            account = await email_db.create_email_account(account_data)
            return account["id"]
        
        return asyncio.run(_create())
    
    def inject_test_email(self, email_data: dict, account_id: str) -> str:
        """Injecte un email de test en DB (simule la synchro Gmail)."""
        from app.services.email_database_service import email_db
        from app.services.emails.content_cleaner import content_cleaner
        import asyncio
        import uuid
        
        async def _inject():
            # Extraire et nettoyer le contenu si c'est un forward
            forwarded = email_data.get("forwarded_content", {})
            original_body = forwarded.get("original_body", "")
            original_headers = forwarded.get("original_headers", {})
            
            if original_body and original_headers:
                # Reconstruire le format de forward complet avec headers
                raw_body = f"""---------- Forwarded message ---------
From: {original_headers.get('From', '')}
Date: {original_headers.get('Date', '')}
Subject: {original_headers.get('Subject', '')}
To: {original_headers.get('To', '')}

{original_body}"""
                raw_subject = original_headers.get("Subject", "")
            else:
                raw_body = email_data.get("body", "")
                raw_subject = email_data.get("subject", "")
            
            if raw_body:
                extracted = content_cleaner.extract_original(raw_body, raw_subject)
                body_cleaned = extracted.body_cleaned
                subject_cleaned = extracted.subject
                sender_email = extracted.from_email
                sender_name = extracted.from_name
                to_emails = extracted.to_emails
            else:
                body_cleaned = email_data.get("body", "")
                subject_cleaned = email_data.get("subject", "")
                sender_email = email_data.get("sender_email", "")
                sender_name = None
                to_emails = []
            
            # Rendre les IDs Gmail uniques pour éviter les conflits (pas de cleanup)
            unique_suffix = f"-{uuid.uuid4().hex[:8]}"
            gmail_message_id = email_data.get("gmail_message_id", "")
            if gmail_message_id:
                gmail_message_id = f"{gmail_message_id}{unique_suffix}"
            
            email_db_data = {
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_account_id": account_id,
                "delivered_to_alias": email_data.get("delivered_to"),
                "routing_status": "routed",
                "gmail_thread_id": email_data.get("gmail_thread_id"),
                "gmail_message_id": gmail_message_id,
                "gmail_history_id": email_data.get("gmail_uid"),
                "subject": subject_cleaned,
                "subject_cleaned": subject_cleaned,
                "sender_email": sender_email,
                "sender_name": sender_name,
                "recipient_emails": to_emails if to_emails else [email_data.get("delivered_to")],
                "sent_at": email_data.get("forwarded_content", {}).get("original_headers", {}).get("Date", datetime.utcnow().isoformat()),
                "received_at": datetime.utcnow().isoformat(),
                "content_text": body_cleaned,
                "content_text_raw": raw_body if raw_body else email_data.get("body", ""),
                "content_cleaned_at": datetime.utcnow().isoformat(),
                "processing_status": "pending",
                "in_reply_to": email_data.get("in_reply_to"),
                "references": email_data.get("references"),
                "has_attachments": False,
                "attachments_count": 0,
                "total_size_bytes": 0,
                "headers": email_data.get("raw_headers", {})
            }
            
            email = await email_db.create_email(email_db_data)
            return email["id"]
        
        return asyncio.run(_inject())
    
    def test_scenario_1_forwarded_simple_with_attachment(self):
        """
        Scénario 1: Email forwardé simple avec facture ACORUS.
        
        Vérifie que l'email est correctement stocké avec:
        - Extraction du mail original (pas le forward)
        - Association à la bonne company
        """
        # Arrange
        account_id = self.create_test_email_account()
        fixture = load_email_fixture("email_1_forwarded_simple.json")
        expected = fixture["expected"]
        
        # Act - Injecter l'email (simule la synchro)
        email_id = self.inject_test_email(fixture, account_id)
        
        # Assert - Vérifier via l'API
        response = client.get(f"/api/v1/{TEST_ORG_SLUG}/emails/{email_id}")
        assert response.status_code == 200
        
        email = response.json()
        assert email["sender_email"] == expected["sender_email"]
        assert email["sender_name"] == expected["sender_name"]
        assert email["subject"] == expected["subject"]
        assert email["company_id"] == TEST_COMPANY_ID
        assert email["routing_status"] == expected["routing_status"]
        assert "INV-EXA-0001" in email["content_text"]
        assert "3280" in email["content_text"] or "3 280" in email["content_text"]
    
    def test_scenario_2_email_thread(self):
        """
        Scénario 2: Chaîne d'emails (thread).
        
        Vérifie que les emails du même thread sont regroupés.
        """
        import uuid
        
        # Arrange - utiliser un thread_id unique pour éviter les conflits
        unique_thread_id = f"thread-test-{uuid.uuid4().hex[:8]}"
        account_id = self.create_test_email_account()
        fixture1 = load_email_fixture("email_1_forwarded_simple.json")
        fixture2 = load_email_fixture("email_2_forwarded_reply.json")
        
        # Modifier les fixtures pour utiliser le même thread_id unique
        fixture1["gmail_thread_id"] = unique_thread_id
        fixture2["gmail_thread_id"] = unique_thread_id
        
        # Act - Injecter les deux emails
        email1_id = self.inject_test_email(fixture1, account_id)
        email2_id = self.inject_test_email(fixture2, account_id)
        
        # Assert - Vérifier via l'API que le thread est complet
        response = client.get(f"/api/v1/{TEST_ORG_SLUG}/emails/{email1_id}")
        assert response.status_code == 200
        
        email1 = response.json()
        assert "thread_emails" in email1
        assert len(email1["thread_emails"]) == 1
        assert email1["thread_emails"][0]["id"] == email2_id
    
    def test_scenario_3_ignored_emails_routing(self):
        """
        Scénario 3: Emails ignorés par le routing.
        
        Vérifie que les emails avec alias invalide sont rejetés.
        """
        from app.services.emails.alias_router import alias_router
        import asyncio
        
        # Patch l'org_slug pour les tests
        original_org_slug = alias_router.env_org_slug
        alias_router.env_org_slug = TEST_ORG_SLUG
        
        try:
            # Test 3a: Pas d'alias
            result = asyncio.run(alias_router.route("REDACTED_EMAIL"))
            assert result.routing_status == "ignored_no_alias"
            
            # Test 3b: Org mismatch
            result = asyncio.run(alias_router.route("REDACTED_EMAIL"))
            assert result.routing_status == "ignored_org_mismatch"
            
            # Test 3c: Company inexistante
            result = asyncio.run(alias_router.route("REDACTED_EMAIL"))
            assert result.routing_status == "ignored_company_not_found"
            
            # Test 3d: Format invalide
            result = asyncio.run(alias_router.route("REDACTED_EMAIL"))
            assert result.routing_status == "ignored_invalid_format"
        finally:
            alias_router.env_org_slug = original_org_slug
    
    def test_scenario_5_rag_mail_cleaning(self):
        """
        Scénario 5: Extraction forward + RAG Mail.
        
        Vérifie le nettoyage du contenu:
        - Extraction du mail original
        - Suppression signatures
        - Suppression mentions légales
        """
        from app.services.emails.content_cleaner import content_cleaner
        
        # Email forwardé brut
        raw_forward = """---------- Forwarded message ---------
From: Service Commercial ACORUS <contact@acorus.fr>
Date: Mon, 28 Jul 2025 10:00:00 +0200
Subject: Facture INV-EXA-0001
To: client@batiment-pro.fr

Madame, Monsieur,

Veuillez trouver ci-joint notre facture N° INV-EXA-0001 pour les travaux 
de rénovation de la salle de bain PMR à la Résidence Les Lilas.

Montant HT : 3 280,78 €
Bon de commande : BC2507036455

Cordialement,
--
Service Commercial ACORUS
Tél : REDACTED_PHONE.78
www.acorus.fr

Ce message et toutes les pièces jointes sont confidentiels..."""
        
        # Extraction
        extracted = content_cleaner.extract_original(raw_forward, "Fwd: Facture INV-EXA-0001")
        
        # Vérifier extraction
        assert extracted.from_email == "contact@acorus.fr"
        assert extracted.from_name == "Service Commercial ACORUS"
        assert extracted.subject == "Facture INV-EXA-0001"
        assert "client@batiment-pro.fr" in extracted.to_emails
        
        # Vérifier nettoyage
        cleaned = extracted.body_cleaned
        
        # Doit contenir le contenu métier
        assert "INV-EXA-0001" in cleaned
        assert "3 280,78" in cleaned or "3280.78" in cleaned
        assert "Résidence Les Lilas" in cleaned
        
        # Ne doit PAS contenir
        assert "REDACTED_PHONE.78" not in cleaned  # Téléphone
        assert "www.acorus.fr" not in cleaned  # Site web
        assert "confidentiels" not in cleaned.lower()  # Mention légale
        assert "Forwarded message" not in cleaned  # Header forward


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
