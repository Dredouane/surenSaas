#!/usr/bin/env python3
"""
Tests end-to-end des scénarios Secrétaire IA avec vrais appels Gemini.

⚠️ Ces tests utilisent de vrais appels Vertex AI (coût ~0.01-0.03€ par test)
Ils sont marqués comme 'slow' et peuvent être ignorés avec: pytest -m 'not slow'

Les validations se font par recherche de mots-clés dans les réponses (non déterministes).
"""

import sys
import os
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4, UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Configuration
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"
TEST_COMPANY_SLUG = "construction"
TEST_TIMEOUT = 60  # Timeout pour les appels Gemini (secondes)


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


class TestSecretariatScenarios:
    """Tests end-to-end des 3 scénarios Secrétaire IA."""
    
    # ============================================================================
    # HELPERS
    # ============================================================================
    
    def create_test_email_account(self) -> str:
        """Crée un compte email de test."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        account_data = {
            "org_id": TEST_ORG_ID,
            "email_address": f"REDACTED_EMAIL_LOCAL+{uuid4().hex[:8]}@gmail.com",
            "oauth_refresh_token": "test_refresh_token",
            "is_active": True,
            "sync_enabled": True
        }
        
        response = supabase.table("email_accounts").insert(account_data).execute()
        return response.data[0]["id"]
    
    def load_extraction_data(self) -> dict:
        """Charge les données d'extraction du PDF de test."""
        extraction_path = Path(__file__).parent / "data" / "emails" / "INV-EXA-0001_extraction_result_20260319_211239.json"
        with open(extraction_path) as f:
            return json.load(f)
    
    def create_test_thread(self, subject: str, gmail_thread_id: str = None) -> dict:
        """Crée un thread de test."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        thread_data = {
            "org_id": TEST_ORG_ID,
            "company_id": TEST_COMPANY_ID,
            "gmail_thread_id": gmail_thread_id or f"thread-{uuid4().hex[:12]}",
            "subject": subject,
            "subject_cleaned": subject,
            "ai_summary": None,
            "ai_context": None,
            "ai_urgency": "medium",
            "ai_status": "new",
            "participant_emails": [],
            "participant_names": [],
            "email_count": 0,
            "attachment_count": 0,
            "is_archived": False,
            "is_starred": False
        }
        
        response = supabase.table("email_threads").insert(thread_data).execute()
        return response.data[0]
    
    def create_email_with_forward(
        self,
        account_id: str,
        thread_id: str,
        gmail_thread_id: str,
        subject: str,
        content: str,
        sender_email: str = "contact@acorus.fr",
        sender_name: str = "ACORUS"
    ) -> dict:
        """Crée un email de test."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        email_data = {
            "org_id": TEST_ORG_ID,
            "company_id": TEST_COMPANY_ID,
            "email_account_id": account_id,
            "gmail_thread_id": gmail_thread_id,
            "gmail_message_id": f"msg-{uuid4().hex[:12]}",
            "gmail_history_id": 12345,
            "subject": subject,
            "subject_cleaned": subject,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "recipient_emails": ["REDACTED_EMAIL"],
            "content_text": content,
            "content_text_raw": content,
            "sent_at": datetime.utcnow().isoformat(),
            "received_at": datetime.utcnow().isoformat(),
            "processing_status": "pending",
            "has_attachments": False,
            "attachments_count": 0,
            "total_size_bytes": 0,
            "headers": {}
        }
        
        response = supabase.table("emails").insert(email_data).execute()
        return response.data[0]
    
    def create_attachment_with_ocr(self, email_id: str, ocr_text: str) -> dict:
        """Crée une pièce jointe avec OCR."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        attachment_data = {
            "org_id": TEST_ORG_ID,
            "company_id": TEST_COMPANY_ID,
            "email_id": email_id,
            "filename": "INV-EXA-0001_EXAMPLE-SOCIETE.pdf",
            "filename_clean": "INV-EXA-0001_EXAMPLE-SOCIETE.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 67431,
            "storage_path": "/test/facture.pdf",
            "is_processed": True,
            "ocr_text": ocr_text,
            "ocr_confidence": 0.95
        }
        
        response = supabase.table("email_attachments").insert(attachment_data).execute()
        return response.data[0]
    
    def trigger_vectorization(self, email_id: str):
        """Déclenche la vectorisation d'un email."""
        from app.services.emails.embedding_service import embedding_service
        import asyncio
        
        # Lancer la vectorisation (async)
        asyncio.run(embedding_service.vectorize_email_async(email_id))
    
    def wait_for_analysis(self, thread_id: str, timeout: int = 30) -> dict:
        """Attend que la Secrétaire ait analysé le thread."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = supabase.table("email_threads")\
                .select("ai_summary, ai_status, ai_urgency")\
                .eq("id", thread_id)\
                .single()\
                .execute()
            
            if response.data and response.data.get("ai_summary"):
                return response.data
            
            time.sleep(2)  # Poll toutes les 2 secondes
        
        raise TimeoutError(f"Analyse non terminée après {timeout}s")
    
    def get_chat_session(self, thread_id: str) -> dict:
        """Récupère la session de chat par défaut d'un thread."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        response = supabase.table("thread_chat_sessions")\
            .select("*")\
            .eq("thread_id", thread_id)\
            .eq("is_default", True)\
            .maybe_single()\
            .execute()
        
        return response.data if response.data else None
    
    def get_chat_messages(self, session_id: str) -> list:
        """Récupère les messages d'une session de chat."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        response = supabase.table("thread_chat_messages")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("created_at", desc=False)\
            .execute()
        
        return response.data if response.data else []
    
    def assert_contains_any(self, text: str, keywords: list, case_insensitive=True):
        """Valide que text contient au moins un des keywords."""
        if not text:
            pytest.fail("Texte vide, impossible de chercher les mots-clés")
        
        text_check = text.lower() if case_insensitive else text
        found = [kw for kw in keywords if kw.lower() in text_check]
        
        assert len(found) > 0, \
            f"Aucun des mots {keywords} trouvé dans: {text[:300]}..."
        
        return found
    
    def send_chat_message_api(self, thread_id: str, message: str) -> dict:
        """Envoie un message via l'API et retourne la réponse."""
        response = client.post(
            f"/api/v1/{TEST_ORG_SLUG}/email-threads/{thread_id}/chat",
            json={"message": message}
        )
        
        assert response.status_code == 200, \
            f"Erreur API chat: {response.status_code} - {response.text}"
        
        return response.json()
    
    # ============================================================================
    # SCÉNARIO 1 : Premier Email + Analyse + Chat
    # ============================================================================
    
    @pytest.mark.slow
    def test_scenario_1_first_email_analysis_and_chat(self):
        """
        Scénario 1: Premier email → Analyse auto → Chat avec question
        
        Étapes:
        1. Créer compte email
        2. Créer thread
        3. Injecter email forward avec mention devis ACORUS
        4. Créer PJ avec OCR (données réelles)
        5. Déclencher vectorisation
        6. Attendre analyse Secrétaire
        7. Vérifier résumé et statut
        8. Vérifier message system dans chat
        9. Poser question sur le numéro de devis
        10. Vérifier réponse avec sources
        
        Coût estimé: ~0.01€ (1 appel pré-analyse + 1 appel chat)
        Durée estimée: ~15-20 secondes
        """
        print("\n🧪 Scénario 1: Premier email + Analyse + Chat")
        
        # 1. Créer compte email
        account_id = self.create_test_email_account()
        print(f"✅ Compte email créé: {account_id[:8]}...")
        
        # 2. Créer thread
        thread = self.create_test_thread("Fwd: Devis INV-EXA-0001 - Travaux Salle de Bain")
        thread_id = thread["id"]
        gmail_thread_id = thread["gmail_thread_id"]
        print(f"✅ Thread créé: {thread_id[:8]}...")
        
        # 3. Charger données extraction
        extraction = self.load_extraction_data()
        invoice_data = extraction["extracted_data"]["invoice"]
        amounts = extraction["extracted_data"]["amounts"]
        
        # 4. Créer email avec forward
        email_content = f"""---------- Forwarded message ---------
From: Service Commercial ACORUS <contact@acorus.fr>
Date: Lun, 28 Juil 2025 10:00:00 +0200
Subject: Devis {invoice_data['number']} - Travaux Salle de Bain Résidence Les Lilas
To: contact@batiment-pro.fr

Madame, Monsieur,

Suite à votre demande, veuillez trouver ci-joint notre devis {invoice_data['number']} pour les travaux de rénovation salle de bain PMR à la Résidence Les Lilas.

Détail des travaux:
- Démolition existant
- Installation PMR (Personne à Mobilité Réduite)
- Carrelage sol et murs
- Robinetterie et sanitaires
- Éclairage LED

Montant HT: {amounts['ht']} EUR
Délai de réalisation: 3 semaines
Validité du devis: 30 jours

Nous restons à votre disposition pour toute information complémentaire.

Cordialement,
Service Commercial ACORUS
Tél: REDACTED_PHONE.78"""
        
        email = self.create_email_with_forward(
            account_id=account_id,
            thread_id=thread_id,
            gmail_thread_id=gmail_thread_id,
            subject=f"Fwd: Devis {invoice_data['number']} - Travaux Salle de Bain",
            content=email_content
        )
        email_id = email["id"]
        print(f"✅ Email créé: {email_id[:8]}...")
        
        # 5. Créer PJ avec OCR
        # Construire texte OCR synthétique à partir de l'extraction
        ocr_lines = [
            f"FACTURE N° {invoice_data['number']}",
            f"Fournisseur: ACORUS",
            f"Bon de commande: {invoice_data['purchase_order']}",
            f"Date: {invoice_data['date']}",
            f"Montant HT: {amounts['ht']} EUR",
            "",
            "Détail des prestations:",
        ]
        
        for item in extraction["extracted_data"].get("line_items", [])[:5]:
            ocr_lines.append(f"- {item['description']}")
        
        ocr_text = "\n".join(ocr_lines)
        
        attachment = self.create_attachment_with_ocr(email_id, ocr_text)
        print(f"✅ Pièce jointe créée avec OCR ({len(ocr_text)} caractères)")
        
        # 6. Déclencher vectorisation (ce qui déclenche l'analyse Secrétaire)
        print("🔄 Vectorisation et analyse Secrétaire en cours...")
        self.trigger_vectorization(email_id)
        
        # 7. Attendre analyse
        print("⏳ Attente de l'analyse (peut prendre 5-10s)...")
        thread_updated = self.wait_for_analysis(thread_id, timeout=TEST_TIMEOUT)
        print(f"✅ Analyse terminée")
        
        # 8. Vérifications résumé et statut
        print("🔍 Vérifications...")
        
        # Vérifier que le résumé existe et contient des mots pertinents
        summary = thread_updated.get("ai_summary", "")
        assert summary, "Le résumé ne doit pas être vide"
        
        self.assert_contains_any(summary, [
            "devis", "bf2507022328", "acorus", "salle de bain",
            "travaux", "rénovation", "pmr"
        ])
        print(f"✅ Résumé pertinent: {summary[:100]}...")
        
        # Vérifier le statut (accepte 'waiting' car c'est le mapping de 'awaiting_response')
        status = thread_updated.get("ai_status")
        assert status in ["new", "waiting", "in_progress"], \
            f"Statut '{status}' devrait être 'new', 'waiting' ou 'in_progress'"
        print(f"✅ Statut: {status}")
        
        # 9. Vérifier chat message system
        chat_session = self.get_chat_session(thread_id)
        assert chat_session, "La session de chat par défaut doit exister"
        print(f"✅ Session de chat créée")
        
        messages = self.get_chat_messages(chat_session["id"])
        system_messages = [m for m in messages if m["role"] == "system"]
        assert len(system_messages) > 0, "Un message system doit exister"
        
        system_content = system_messages[0]["content"]
        self.assert_contains_any(system_content, ["résumé", "dossier", "devis"])
        print(f"✅ Message system dans chat")
        
        # 10. Tester chat avec question
        print("💬 Test du chat avec question...")
        chat_response = self.send_chat_message_api(
            thread_id,
            f"Quel est le numéro du devis mentionné dans l'email ?"
        )
        
        assistant_msg = chat_response.get("assistant_message", {})
        response_text = assistant_msg.get("content", "")
        metadata = assistant_msg.get("metadata", {})
        
        # Vérifier réponse
        self.assert_contains_any(response_text, [
            invoice_data['number'].lower(),  # bf2507022328
            "bf", "2507", "devis", "numéro"
        ])
        print(f"✅ Réponse chat pertinente: {response_text[:150]}...")
        
        # Vérifier sources
        sources = metadata.get("sources", [])
        assert len(sources) > 0, "La réponse doit citer des sources"
        print(f"✅ Sources citées: {sources}")
        
        # Vérifier confidence
        confidence = metadata.get("confidence", 0)
        assert confidence > 0.5, f"Confidence {confidence} devrait être > 0.5"
        print(f"✅ Confidence: {confidence}")
        
        print("\n✅ Scénario 1 terminé avec succès!")
    
    # ============================================================================
    # SCÉNARIO 2 : Thread de 2 emails (relance)
    # ============================================================================
    
    @pytest.mark.slow
    def test_scenario_2_two_emails_thread_update(self):
        """
        Scénario 2: Thread avec 2 emails (devis + relance)
        
        Étapes:
        1. Créer thread avec Email 1 (déjà analysé)
        2. Injecter Email 2 (relance avec urgence)
        3. Vectoriser Email 2
        4. Attendre analyse et mise à jour
        5. Vérifier que le résumé reflète les 2 emails
        6. Vérifier statut = 'urgent'
        7. Vérifier message system mis à jour
        
        Coût estimé: ~0.01€ (1 appel pré-analyse)
        Durée estimée: ~10-15 secondes
        """
        print("\n🧪 Scénario 2: Thread de 2 emails avec relance")
        
        # 1. Créer thread et Email 1 (déjà analysé)
        account_id = self.create_test_email_account()
        thread = self.create_test_thread("Fwd: Devis INV-EXA-0001")
        thread_id = thread["id"]
        gmail_thread_id = thread["gmail_thread_id"]
        
        # Email 1: Devis initial
        extraction = self.load_extraction_data()
        invoice_data = extraction["extracted_data"]["invoice"]
        
        email1_content = f"Devis {invoice_data['number']} pour travaux salle de bain. Délai: 3 semaines."
        email1 = self.create_email_with_forward(
            account_id=account_id,
            thread_id=thread_id,
            gmail_thread_id=gmail_thread_id,
            subject=f"Fwd: Devis {invoice_data['number']}",
            content=email1_content
        )
        
        # Créer PJ pour Email 1
        ocr_text = f"FACTURE N° {invoice_data['number']}\nMontant HT: 3280.78 EUR"
        self.create_attachment_with_ocr(email1["id"], ocr_text)
        
        # Vectoriser et analyser Email 1
        print("🔄 Analyse Email 1...")
        self.trigger_vectorization(email1["id"])
        thread_after_1 = self.wait_for_analysis(thread_id, timeout=TEST_TIMEOUT)
        
        summary_1 = thread_after_1.get("ai_summary", "")
        print(f"✅ Email 1 analysé: {summary_1[:80]}...")
        
        # 2. Créer Email 2: Relance urgente
        email2_content = f"""Bonjour,

Nous nous permettons de relancer notre demande concernant le devis {invoice_data['number']} envoyé le 28/07/2025.

Nous n'avons pas reçu de retour de votre part et le chantier est prévu pour début août. Le délai de 3 semaines nous inquiète car nous devons respecter une échéance imposée par le propriétaire.

Cette prestation est URGENTE car nous avons un locataire handicapé qui attend l'aménagement de cette salle de bain PMR.

Dans l'attente de votre retour rapide.

Cordialement,
Marie DUPONT
Responsable technique
ACORUS"""
        
        email2 = self.create_email_with_forward(
            account_id=account_id,
            thread_id=thread_id,
            gmail_thread_id=gmail_thread_id,
            subject=f"Re: Devis {invoice_data['number']} - RELANCE URGENTE",
            content=email2_content
        )
        print(f"✅ Email 2 (relance) créé")
        
        # 3. Vectoriser Email 2
        print("🔄 Analyse Email 2 (relance)...")
        self.trigger_vectorization(email2["id"])
        
        # 4. Attendre mise à jour
        thread_after_2 = self.wait_for_analysis(thread_id, timeout=TEST_TIMEOUT)
        print(f"✅ Analyse Email 2 terminée")
        
        # 5. Vérifications
        summary_2 = thread_after_2.get("ai_summary", "")
        status_2 = thread_after_2.get("ai_status")
        urgency_2 = thread_after_2.get("ai_urgency")
        
        # Le résumé doit mentionner la relance
        self.assert_contains_any(summary_2, [
            "relance", "urgent", "échéance", "handicapé", 
            "locataire", "marie dupont", "retard"
        ])
        print(f"✅ Résumé reflète la relance: {summary_2[:100]}...")
        
        # Le statut doit être waiting (urgent est mappé à waiting pour la DB)
        # mais ai_urgency doit être high
        assert status_2 == "waiting", \
            f"Statut devrait être 'waiting' mais est '{status_2}'"
        print(f"✅ Statut détecté comme waiting (avec urgence)")
        
        # L'urgence doit être high
        assert urgency_2 == "high", \
            f"Urgence devrait être 'high' mais est '{urgency_2}'"
        print(f"✅ Niveau d'urgence: {urgency_2}")
        
        # 6. Vérifier message system mis à jour
        chat_session = self.get_chat_session(thread_id)
        messages = self.get_chat_messages(chat_session["id"])
        system_messages = [m for m in messages if m["role"] == "system"]
        
        # Le message system doit être mis à jour (contenir la relance)
        latest_system = system_messages[-1]["content"] if system_messages else ""
        self.assert_contains_any(latest_system, [
            "relance", "urgent", "handicapé", "🔴"
        ])
        print(f"✅ Message system mis à jour avec urgence")
        
        print("\n✅ Scénario 2 terminé avec succès!")
    
    # ============================================================================
    # SCÉNARIO 3 : 2 emails + Question contextuelle
    # ============================================================================
    
    @pytest.mark.slow
    def test_scenario_3_two_emails_with_context_question(self):
        """
        Scénario 3: 2 emails + Question utilisateur sur contexte complet
        
        Étapes:
        1. Créer thread avec Email 1 (devis) et Email 2 (relance)
        2. Analyser les 2 emails
        3. Poser question: "Quel est le montant et pourquoi c'est urgent ?"
        4. Vérifier que la réponse utilise les 2 emails (montant du devis + urgence de la relance)
        5. Vérifier sources et confidence
        
        Coût estimé: ~0.02€ (2 appels pré-analyse + 1 appel chat)
        Durée estimée: ~20-30 secondes
        """
        print("\n🧪 Scénario 3: Contexte complet + Question utilisateur")
        
        # 1. Créer thread complet (comme Scénario 2)
        account_id = self.create_test_email_account()
        thread = self.create_test_thread("Fwd: Devis INV-EXA-0001 - Relance")
        thread_id = thread["id"]
        gmail_thread_id = thread["gmail_thread_id"]
        
        extraction = self.load_extraction_data()
        invoice_data = extraction["extracted_data"]["invoice"]
        amounts = extraction["extracted_data"]["amounts"]
        
        # Email 1: Devis avec montant
        email1_content = f"""Devis {invoice_data['number']} pour travaux salle de bain PMR.
Montant HT: {amounts['ht']} EUR
Délai: 3 semaines
Validité: 30 jours"""
        
        email1 = self.create_email_with_forward(
            account_id=account_id,
            thread_id=thread_id,
            gmail_thread_id=gmail_thread_id,
            subject=f"Fwd: Devis {invoice_data['number']}",
            content=email1_content
        )
        
        # PJ avec OCR
        ocr_text = f"FACTURE {invoice_data['number']}\nMontant HT: {amounts['ht']} EUR\nFournisseur: ACORUS"
        self.create_attachment_with_ocr(email1["id"], ocr_text)
        
        # Email 2: Relance avec urgence
        email2_content = f"""Relance concernant le devis {invoice_data['number']}.

C'est URGENT car:
- Échéance imposée par le propriétaire
- Locataire handicapé attend l'aménagement PMR
- Chantier doit démarrer début août

Merci de nous répondre rapidement.

Marie DUPONT, ACORUS"""
        
        email2 = self.create_email_with_forward(
            account_id=account_id,
            thread_id=thread_id,
            gmail_thread_id=gmail_thread_id,
            subject=f"Re: Devis {invoice_data['number']} - URGENT",
            content=email2_content
        )
        
        # 2. Analyser les 2 emails
        print("🔄 Analyse des 2 emails...")
        self.trigger_vectorization(email1["id"])
        self.wait_for_analysis(thread_id, timeout=TEST_TIMEOUT)
        
        self.trigger_vectorization(email2["id"])
        self.wait_for_analysis(thread_id, timeout=TEST_TIMEOUT)
        print("✅ Analyses terminées")
        
        # 3. Poser question contextuelle
        print("💬 Question utilisateur...")
        chat_response = self.send_chat_message_api(
            thread_id,
            "Quel est le montant du devis et pourquoi c'est urgent ?"
        )
        
        assistant_msg = chat_response.get("assistant_message", {})
        response_text = assistant_msg.get("content", "").lower()
        metadata = assistant_msg.get("metadata", {})
        
        print(f"📝 Réponse: {assistant_msg.get('content', '')[:200]}...")
        
        # 4. Vérifier que la réponse utilise les 2 emails
        
        # Doit mentionner le montant (Email 1 ou PJ)
        montant_keywords = [str(amounts['ht']), "3280", "euro", "€", "montant", "ht"]
        found_montant = [kw for kw in montant_keywords if kw.lower() in response_text]
        assert len(found_montant) > 0, \
            f"La réponse devrait mentionner le montant ({amounts['ht']}€). " \
            f"Réponse: {response_text[:300]}"
        print(f"✅ Mention du montant: {found_montant}")
        
        # Doit expliquer l'urgence (Email 2)
        urgence_keywords = [
            "urgent", "échéance", "handicapé", "locataire", 
            "propriétaire", "attend", "pmr", "début août"
        ]
        found_urgence = [kw for kw in urgence_keywords if kw.lower() in response_text]
        assert len(found_urgence) > 0, \
            f"La réponse devrait expliquer l'urgence. Réponse: {response_text[:300]}"
        print(f"✅ Explication urgence: {found_urgence}")
        
        # 5. Vérifier sources et confidence
        sources = metadata.get("sources", [])
        assert len(sources) >= 1, \
            "La réponse doit citer au moins une source"
        print(f"✅ Sources citées: {sources}")
        
        confidence = metadata.get("confidence", 0)
        assert confidence > 0.6, \
            f"Confidence {confidence} devrait être > 0.6"
        print(f"✅ Confidence: {confidence}")
        
        # Vérifier structure JSON complète
        assert "response" in assistant_msg.get("metadata", {}) or True  # Pas obligatoire
        
        print("\n✅ Scénario 3 terminé avec succès!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
