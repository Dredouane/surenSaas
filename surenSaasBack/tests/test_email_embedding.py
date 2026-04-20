#!/usr/bin/env python3
"""
Tests de vectorisation avec Vertex AI (vrais appels, pas de mocks).

Vérifie que:
1. Les embeddings sont générés correctement
2. La recherche sémantique fonctionne
3. Les pièces jointes sont OCRisées et vectorisées
"""

import sys
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
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
        raise ValueError(f"Organization {TEST_ORG_SLUG} not found in DB")
    
    org_id = org_response.data["id"]
    
    company_response = supabase.table("companies")\
        .select("id")\
        .eq("slug", TEST_COMPANY_SLUG)\
        .eq("org_id", org_id)\
        .single()\
        .execute()
    
    if not company_response.data:
        raise ValueError(f"Company {TEST_COMPANY_SLUG} not found in DB")
    
    company_id = company_response.data["id"]
    
    return org_id, company_id


TEST_ORG_ID, TEST_COMPANY_ID = get_test_org_and_company()


class TestEmbeddingVectorization:
    """Tests de vectorisation avec Vertex AI (vrais appels)."""
    
    def create_test_email_account(self) -> str:
        """Crée un compte email de test."""
        from app.services.email_database_service import email_db
        import asyncio
        
        async def _create():
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
    
    def test_generate_embedding_direct(self):
        """
        Test 1: Génération d'embedding direct avec Vertex AI.
        
        Vérifie que le service peut générer un embedding valide.
        """
        from app.services.emails.embedding_service import embedding_service
        import asyncio
        
        async def _test():
            # Générer un embedding
            text = "Facture ACORUS INV-EXA-0001 pour travaux salle de bain"
            vector = await embedding_service.generate_embedding(text)
            
            # Vérifications
            assert vector is not None
            assert len(vector) == 768  # text-embedding-004
            assert all(isinstance(x, float) for x in vector)
            
            # Vérifier que ce n'est pas un vecteur nul
            assert any(x != 0.0 for x in vector)
            
            return vector
        
        vector = asyncio.run(_test())
        print(f"✅ Embedding généré: {len(vector)} dimensions")
    
    def test_chunking(self):
        """
        Test 2: Découpage en chunks avec overlap.
        """
        from app.services.emails.embedding_service import embedding_service
        
        # Texte long
        text = " ".join([f"mot{i}" for i in range(1000)])
        
        chunks = embedding_service.chunk_text(text)
        
        # Vérifications
        assert len(chunks) > 1  # Devrait être découpé
        
        # Vérifier l'overlap
        if len(chunks) > 1:
            # Les chunks consécutifs devraient avoir du contenu commun (overlap)
            chunk1_words = set(chunks[0].split())
            chunk2_words = set(chunks[1].split())
            common = chunk1_words & chunk2_words
            assert len(common) > 0, "Les chunks devraient avoir un overlap"
        
        print(f"✅ Chunking: {len(chunks)} chunks générés")
    
    def test_vectorize_email_async(self):
        """
        Test 3: Vectorisation complète d'un email.
        
        Crée un email, le vectorise, vérifie les records en DB.
        """
        from app.services.email_database_service import email_db
        from app.services.emails.embedding_service import embedding_service
        import asyncio
        
        async def _test():
            # 1. Créer un compte email
            account_data = {
                "org_id": TEST_ORG_ID,
                "email_address": f"test+{uuid.uuid4().hex[:8]}@gmail.com",
                "oauth_refresh_token": "test_token",
                "is_active": True,
                "sync_enabled": True
            }
            account = await email_db.create_email_account(account_data)
            account_id = account["id"]
            
            # 2. Créer un email de test
            unique_msg_id = f"<test-{uuid.uuid4().hex}@test.com>"
            email_data = {
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_account_id": account_id,
                "delivered_to_alias": f"REDACTED_EMAIL",
                "routing_status": "routed",
                "gmail_thread_id": f"thread-{uuid.uuid4().hex[:8]}",
                "gmail_message_id": unique_msg_id,
                "gmail_history_id": 12345,
                "subject": "Facture INV-EXA-0001",
                "subject_cleaned": "Facture INV-EXA-0001",
                "sender_email": "contact@acorus.fr",
                "sender_name": "ACORUS",
                "recipient_emails": ["client@test.com"],
                "sent_at": datetime.utcnow().isoformat(),
                "received_at": datetime.utcnow().isoformat(),
                "content_text": "Madame, Monsieur, voici la facture INV-EXA-0001 pour les travaux de rénovation salle de bain à la Résidence Les Lilas. Montant HT: 3280.78 EUR. Bon de commande BC2507036455.",
                "content_text_raw": "Raw content",
                "content_cleaned_at": datetime.utcnow().isoformat(),
                "processing_status": "pending",
                "has_attachments": False,
                "attachments_count": 0,
                "total_size_bytes": 0,
                "headers": {}
            }
            
            email = await email_db.create_email(email_data)
            email_id = email["id"]
            
            # 3. Vectoriser l'email
            await embedding_service.vectorize_email_async(email_id)
            
            # 4. Vérifier les embeddings en DB
            embeddings = await email_db.get_embeddings_by_email(email_id)
            
            assert len(embeddings) > 0, "Des embeddings devraient être créés"
            
            # Vérifier le contenu des embeddings
            import json
            for emb in embeddings:
                assert emb["org_id"] == TEST_ORG_ID
                assert emb["company_id"] == TEST_COMPANY_ID
                assert emb["email_id"] == email_id
                assert emb["source_type"] == "email_body"
                # L'embedding peut être stocké comme chaîne JSON ou liste
                embedding = emb["embedding"]
                if isinstance(embedding, str):
                    embedding = json.loads(embedding)
                assert len(embedding) == 768
                assert emb["model_name"] == "text-embedding-004"
            
            # 5. Vérifier que l'email est marqué comme vectorisé
            updated_email = await email_db.get_email_by_id(email_id)
            assert updated_email["processing_status"] == "vectorized"
            
            return len(embeddings)
        
        count = asyncio.run(_test())
        print(f"✅ Email vectorisé: {count} chunks créés")
    
    def test_semantic_search(self):
        """
        Test 4: Recherche sémantique avec embeddings.
        
        Crée plusieurs emails, génère les embeddings, recherche.
        """
        from app.services.email_database_service import email_db
        from app.services.emails.embedding_service import embedding_service
        import asyncio
        
        async def _test():
            # 1. Créer un compte
            account_data = {
                "org_id": TEST_ORG_ID,
                "email_address": f"test+{uuid.uuid4().hex[:8]}@gmail.com",
                "oauth_refresh_token": "test_token",
                "is_active": True,
                "sync_enabled": True
            }
            account = await email_db.create_email_account(account_data)
            account_id = account["id"]
            
            # 2. Créer 2 emails sur des sujets différents
            emails_data = [
                {
                    "subject": "Facture ACORUS salle de bain",
                    "content": "Facture INV-EXA-0001 pour travaux rénovation salle de bain PMR. Montant 3280.78 EUR.",
                    "msg_id": f"<facture-{uuid.uuid4().hex}@test.com>"
                },
                {
                    "subject": "Devis peinture extérieure",
                    "content": "Devis pour peinture façade immeuble. Surface 200m2. Prix au m2 25 EUR.",
                    "msg_id": f"<devis-{uuid.uuid4().hex}@test.com>"
                }
            ]
            
            email_ids = []
            for data in emails_data:
                email_data = {
                    "org_id": TEST_ORG_ID,
                    "company_id": TEST_COMPANY_ID,
                    "email_account_id": account_id,
                    "delivered_to_alias": f"REDACTED_EMAIL",
                    "routing_status": "routed",
                    "gmail_thread_id": f"thread-{uuid.uuid4().hex[:8]}",
                    "gmail_message_id": data["msg_id"],
                    "gmail_history_id": 12345,
                    "subject": data["subject"],
                    "subject_cleaned": data["subject"],
                    "sender_email": "test@test.com",
                    "sender_name": "Test",
                    "recipient_emails": ["client@test.com"],
                    "sent_at": datetime.utcnow().isoformat(),
                    "received_at": datetime.utcnow().isoformat(),
                    "content_text": data["content"],
                    "content_text_raw": data["content"],
                    "content_cleaned_at": datetime.utcnow().isoformat(),
                    "processing_status": "pending",
                    "has_attachments": False,
                    "attachments_count": 0,
                    "total_size_bytes": 0,
                    "headers": {}
                }
                
                email = await email_db.create_email(email_data)
                email_id = email["id"]
                email_ids.append(email_id)
                
                # Vectoriser
                await embedding_service.vectorize_email_async(email_id)
            
            # 3. Générer l'embedding de la query
            query = "travaux salle de bain rénovation"
            query_vector = await embedding_service.generate_embedding(query)
            
            # 4. Recherche sémantique
            results = await email_db.search_similar_emails(
                query_embedding=query_vector,
                org_id=TEST_ORG_ID,
                company_id=TEST_COMPANY_ID,
                match_threshold=0.5,
                match_count=10
            )
            
            # 5. Vérifications
            assert len(results) > 0, "La recherche devrait retourner des résultats"
            
            # Le premier résultat devrait être l'email sur la salle de bain
            # (car c'est le plus sémantiquement proche de la query)
            first_result = results[0]
            assert "salle de bain" in first_result["content_chunk"].lower() or \
                   "bathroom" in first_result["content_chunk"].lower()
            
            return len(results)
        
        count = asyncio.run(_test())
        print(f"✅ Recherche sémantique: {count} résultats trouvés")


class TestAttachmentOCR:
    """Tests d'OCR et vectorisation des pièces jointes."""
    
    def test_create_attachment_with_ocr(self):
        """
        Test 5: Création d'une pièce jointe avec OCR.
        
        Note: Ce test vérifie la structure, pas l'OCR réel (nécessite un vrai PDF).
        """
        from app.services.email_database_service import email_db
        import asyncio
        
        async def _test():
            # Créer d'abord un email
            account_data = {
                "org_id": TEST_ORG_ID,
                "email_address": f"test+{uuid.uuid4().hex[:8]}@gmail.com",
                "oauth_refresh_token": "test_token",
                "is_active": True,
                "sync_enabled": True
            }
            account = await email_db.create_email_account(account_data)
            account_id = account["id"]
            
            email_data = {
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_account_id": account_id,
                "delivered_to_alias": f"test@test.com",
                "routing_status": "routed",
                "gmail_thread_id": f"thread-{uuid.uuid4().hex[:8]}",
                "gmail_message_id": f"<test-{uuid.uuid4().hex}@test.com>",
                "gmail_history_id": 12345,
                "subject": "Test avec PJ",
                "subject_cleaned": "Test avec PJ",
                "sender_email": "test@test.com",
                "recipient_emails": ["client@test.com"],
                "sent_at": datetime.utcnow().isoformat(),
                "received_at": datetime.utcnow().isoformat(),
                "content_text": "Email avec pièce jointe",
                "content_text_raw": "Email avec pièce jointe",
                "processing_status": "pending",
                "has_attachments": True,
                "attachments_count": 1,
                "total_size_bytes": 1000,
                "headers": {}
            }
            
            email = await email_db.create_email(email_data)
            email_id = email["id"]
            
            # Créer une pièce jointe avec OCR simulé
            attachment = await email_db.create_attachment({
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_id": email_id,
                "filename": "test_facture.pdf",
                "filename_clean": "test_facture.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 50000,
                "storage_path": "/test/path/test_facture.pdf",
                "is_processed": True,
                "ocr_text": "FACTURE N° INV-EXA-0001\nMontant HT: 3280.78 EUR\nClient: ACORUS",
                "ocr_confidence": 0.95
            })
            
            # Vérifier
            attachments = await email_db.get_attachments_by_email(email_id)
            assert len(attachments) == 1
            assert attachments[0]["ocr_text"] is not None
            assert "INV-EXA-0001" in attachments[0]["ocr_text"]
            
            return attachment["id"]
        
        att_id = asyncio.run(_test())
        print(f"✅ Pièce jointe créée avec OCR: {att_id}")
    
    def test_vectorize_attachment(self):
        """
        Test 6: Vectorisation du texte OCR d'une pièce jointe.
        """
        from app.services.email_database_service import email_db
        from app.services.emails.embedding_service import embedding_service
        import asyncio
        
        async def _test():
            # Créer un email avec PJ OCRisée
            account_data = {
                "org_id": TEST_ORG_ID,
                "email_address": f"test+{uuid.uuid4().hex[:8]}@gmail.com",
                "oauth_refresh_token": "test_token",
                "is_active": True,
                "sync_enabled": True
            }
            account = await email_db.create_email_account(account_data)
            account_id = account["id"]
            
            email_data = {
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_account_id": account_id,
                "delivered_to_alias": f"test@test.com",
                "routing_status": "routed",
                "gmail_thread_id": f"thread-{uuid.uuid4().hex[:8]}",
                "gmail_message_id": f"<test-{uuid.uuid4().hex}@test.com>",
                "gmail_history_id": 12345,
                "subject": "Test OCR",
                "subject_cleaned": "Test OCR",
                "sender_email": "test@test.com",
                "recipient_emails": ["client@test.com"],
                "sent_at": datetime.utcnow().isoformat(),
                "received_at": datetime.utcnow().isoformat(),
                "content_text": "Voir PJ",
                "content_text_raw": "Voir PJ",
                "processing_status": "pending",
                "has_attachments": True,
                "attachments_count": 1,
                "total_size_bytes": 1000,
                "headers": {}
            }
            
            email = await email_db.create_email(email_data)
            email_id = email["id"]
            
            # Créer la PJ avec OCR
            ocr_text = "FACTURE INV-EXA-0001\nMontant HT: 3280.78 EUR\nClient: ACORUS\nRéférence: BC2507036455"
            
            attachment = await email_db.create_attachment({
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_id": email_id,
                "filename": "facture.pdf",
                "filename_clean": "facture.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 50000,
                "storage_path": "/test/facture.pdf",
                "is_processed": True,
                "ocr_text": ocr_text,
                "ocr_confidence": 0.95
            })
            attachment_id = attachment["id"]
            
            # Vectoriser l'email (devrait aussi vectoriser la PJ)
            await embedding_service.vectorize_email_async(email_id)
            
            # Vérifier les embeddings
            embeddings = await email_db.get_embeddings_by_email(email_id)
            
            # Devrait avoir des embeddings pour le body ET la PJ
            body_embeddings = [e for e in embeddings if e["source_type"] == "email_body"]
            att_embeddings = [e for e in embeddings if e["source_type"] == "attachment"]
            
            assert len(body_embeddings) > 0, "Devrait avoir des embeddings pour le body"
            assert len(att_embeddings) > 0, "Devrait avoir des embeddings pour la PJ"
            
            # Vérifier que les embeddings de la PJ sont liés au bon attachment
            for emb in att_embeddings:
                assert emb["source_id"] == attachment_id
            
            return len(embeddings)
        
        count = asyncio.run(_test())
        print(f"✅ Vectorisation PJ: {count} embeddings créés (body + PJ)")


class TestScenario1Complete:
    """
    Test Scénario 1 Complet : Email forwardé avec PJ + OCR + recherche sémantique.
    
    Ce test vérifie le flux complet:
    1. Création email avec contenu forwardé
    2. OCR de la pièce jointe PDF réelle
    3. Vectorisation du body et du texte OCR
    4. Recherche sémantique sur le contenu OCR
    """
    
    def test_scenario_1_forward_with_ocr_and_search(self):
        """
        Test 7: Scénario 1 complet - Facture ACORUS avec PJ.
        
        Utilise le vrai PDF de test et effectue une recherche sémantique.
        """
        from app.services.email_database_service import email_db
        from app.services.emails.embedding_service import embedding_service
        from app.services.emails.content_cleaner import content_cleaner
        from app.agents.generic_extractor import create_invoice_extractor
        import asyncio
        
        async def _test():
            # 1. Créer un compte email
            account_data = {
                "org_id": TEST_ORG_ID,
                "email_address": f"REDACTED_EMAIL_LOCAL+{uuid.uuid4().hex[:8]}@gmail.com",
                "oauth_refresh_token": "test_token",
                "is_active": True,
                "sync_enabled": True
            }
            account = await email_db.create_email_account(account_data)
            account_id = account["id"]
            
            # 2. Contenu forwardé (simulé)
            raw_forward = """---------- Forwarded message ---------
From: Service Commercial ACORUS <contact@acorus.fr>
Date: Mon, 28 Jul 2025 10:00:00 +0200
Subject: Facture INV-EXA-0001 - Travaux salle de bain Résidence Les Lilas
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
            
            # 3. Extraire et nettoyer le contenu
            extracted = content_cleaner.extract_original(raw_forward, "Fwd: Facture INV-EXA-0001")
            
            # 4. Créer l'email
            unique_msg_id = f"<facture-acorus-{uuid.uuid4().hex}@test.com>"
            email_data = {
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_account_id": account_id,
                "delivered_to_alias": f"REDACTED_EMAIL",
                "routing_status": "routed",
                "gmail_thread_id": f"thread-{uuid.uuid4().hex[:8]}",
                "gmail_message_id": unique_msg_id,
                "gmail_history_id": 12345,
                "subject": extracted.subject,
                "subject_cleaned": extracted.subject,
                "sender_email": extracted.from_email,
                "sender_name": extracted.from_name,
                "recipient_emails": extracted.to_emails,
                "sent_at": datetime.utcnow().isoformat(),
                "received_at": datetime.utcnow().isoformat(),
                "content_text": extracted.body_cleaned,
                "content_text_raw": raw_forward,
                "content_cleaned_at": datetime.utcnow().isoformat(),
                "processing_status": "pending",
                "has_attachments": True,
                "attachments_count": 1,
                "total_size_bytes": 67431,
                "headers": {}
            }
            
            email = await email_db.create_email(email_data)
            email_id = email["id"]
            
            # 5. OCR de la pièce jointe réelle
            pdf_path = Path(__file__).parent / "data" / "emails" / "INV-EXA-0001_EXAMPLE-SOCIETE.pdf"
            
            if pdf_path.exists():
                # Extraire le texte avec l'extracteur existant
                extractor = create_invoice_extractor()
                extraction_result = await extractor.extract(str(pdf_path))
                # raw_data contient les données extraites, on les convertit en texte
                if extraction_result and extraction_result.raw_data:
                    raw_data = extraction_result.raw_data
                    # Essayer d'extraire le texte des différentes clés possibles
                    ocr_text = raw_data.get("raw_text", "")
                    if not ocr_text:
                        # Convertir tout le raw_data en texte
                        import json
                        ocr_text = json.dumps(raw_data, ensure_ascii=False, indent=2)
                    ocr_confidence = raw_data.get("confidence", 0.95)
                else:
                    ocr_text = ""
                    ocr_confidence = 0.0
            else:
                # Fallback si le PDF n'existe pas
                ocr_text = "FACTURE INV-EXA-0001\nACORUS\nMontant HT: 3280.78 EUR\nEXAMPLE-SOCIETE"
                ocr_confidence = 0.95
            
            # 6. Créer la pièce jointe
            attachment = await email_db.create_attachment({
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_id": email_id,
                "filename": "INV-EXA-0001_EXAMPLE-SOCIETE.pdf",
                "filename_clean": "INV-EXA-0001_EXAMPLE-SOCIETE.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 67431,
                "storage_path": str(pdf_path) if pdf_path.exists() else "/test/facture.pdf",
                "is_processed": True,
                "ocr_text": ocr_text,
                "ocr_confidence": ocr_confidence
            })
            attachment_id = attachment["id"]
            
            # 7. Vectoriser l'email (body + PJ)
            await embedding_service.vectorize_email_async(email_id)
            
            # 8. Vérifier les embeddings créés
            embeddings = await email_db.get_embeddings_by_email(email_id)
            
            body_embs = [e for e in embeddings if e["source_type"] == "email_body"]
            att_embs = [e for e in embeddings if e["source_type"] == "attachment"]
            
            assert len(body_embs) > 0, "Body devrait être vectorisé"
            assert len(att_embs) > 0, "PJ devrait être vectorisée"
            
            # 9. Recherche sémantique sur le contenu OCR
            query = "Montant HT 3280 ACORUS facture"
            query_vector = await embedding_service.generate_embedding(query)
            
            results = await email_db.search_similar_emails(
                query_embedding=query_vector,
                org_id=TEST_ORG_ID,
                company_id=TEST_COMPANY_ID,
                match_threshold=0.5,
                match_count=5
            )
            
            # 10. Vérifications finales
            assert len(results) > 0, "La recherche devrait retourner des résultats"
            
            # Vérifier que l'email est marqué comme vectorisé
            updated_email = await email_db.get_email_by_id(email_id)
            assert updated_email["processing_status"] == "vectorized"
            
            return {
                "email_id": email_id,
                "attachment_id": attachment_id,
                "embeddings_count": len(embeddings),
                "body_chunks": len(body_embs),
                "att_chunks": len(att_embs),
                "search_results": len(results),
                "ocr_text_preview": ocr_text[:100] if ocr_text else ""
            }
        
        result = asyncio.run(_test())
        print(f"✅ Scénario 1 complet:")
        print(f"   - Email: {result['email_id']}")
        print(f"   - Embeddings: {result['embeddings_count']} (body: {result['body_chunks']}, PJ: {result['att_chunks']})")
        print(f"   - Résultats recherche: {result['search_results']}")
        print(f"   - OCR preview: {result['ocr_text_preview']}...")


class TestSearchEndpoint:
    """Tests de l'endpoint de recherche sémantique API."""
    
    def test_search_endpoint(self):
        """
        Test 8: Endpoint de recherche sémantique.
        
        Crée un email vectorisé puis effectue une recherche via l'API.
        """
        from app.services.email_database_service import email_db
        from app.services.emails.embedding_service import embedding_service
        import asyncio
        
        async def _setup():
            # Créer un compte et un email vectorisé
            account_data = {
                "org_id": TEST_ORG_ID,
                "email_address": f"test+{uuid.uuid4().hex[:8]}@gmail.com",
                "oauth_refresh_token": "test_token",
                "is_active": True,
                "sync_enabled": True
            }
            account = await email_db.create_email_account(account_data)
            
            email_data = {
                "org_id": TEST_ORG_ID,
                "company_id": TEST_COMPANY_ID,
                "email_account_id": account["id"],
                "delivered_to_alias": f"test@test.com",
                "routing_status": "routed",
                "gmail_thread_id": f"thread-{uuid.uuid4().hex[:8]}",
                "gmail_message_id": f"<test-{uuid.uuid4().hex}@test.com>",
                "gmail_history_id": 12345,
                "subject": "Facture travaux salle de bain",
                "subject_cleaned": "Facture travaux salle de bain",
                "sender_email": "contact@acorus.fr",
                "sender_name": "ACORUS",
                "recipient_emails": ["client@test.com"],
                "sent_at": datetime.utcnow().isoformat(),
                "received_at": datetime.utcnow().isoformat(),
                "content_text": "Facture INV-EXA-0001 pour travaux rénovation salle de bain. Montant 3280.78 EUR.",
                "content_text_raw": "Raw content",
                "processing_status": "pending",
                "has_attachments": False,
                "attachments_count": 0,
                "total_size_bytes": 0,
                "headers": {}
            }
            
            email = await email_db.create_email(email_data)
            email_id = email["id"]
            
            # Vectoriser
            await embedding_service.vectorize_email_async(email_id)
            
            return email_id
        
        # Setup: créer l'email vectorisé
        email_id = asyncio.run(_setup())
        
        # Test: appeler l'endpoint de recherche
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        response = client.post(
            f"/api/v1/{TEST_ORG_SLUG}/emails/search",
            params={
                "query": "facture salle de bain 3280",
                "match_threshold": 0.5,
                "match_count": 5
            }
        )
        
        # Vérifications
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert data["query"] == "facture salle de bain 3280"
        
        # Devrait trouver au moins un résultat
        assert data["results_count"] > 0
        
        # Vérifier la structure des résultats
        first_result = data["results"][0]
        assert "email_id" in first_result
        assert "subject" in first_result
        assert "similarity_score" in first_result
        assert "content_preview" in first_result
        
        print(f"✅ Endpoint recherche: {data['results_count']} résultats trouvés")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
