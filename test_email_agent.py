#!/usr/bin/env python3
"""
Test de l'agent IA d'extraction d'emails.
"""

import asyncio
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "surenSaasBack"))

from app.agents.email_agent import EmailExtractionAgent
from app.services.emails.content_cleaner import content_cleaner


# Email forward problématique (chaîne d'emails)
TEST_EMAIL_FORWARD = """
Bonjour,

Je te forward l'email de notre fournisseur.

--- Forwarded message ---
De: Service Commercial ACORUS <contact@acorus.fr>
Envoyé: mardi 21 avril 2026 14:55
À: CAROFF, Enzo
Objet: Ré: Devis n°2026-0421-001

Bonjour Monsieur CAROFF,

Suite à notre échange téléphonique, je vous transmets notre devis détaillé.

Cordialement,
Le service commercial

--- Forwarded message ---
De: Enzo CAROFF <enzo.caroff@entreprise.fr>
Envoyé: lundi 20 avril 2026 11:30
À: contact@acorus.fr
Objet: Demande de devis

Bonjour,

Je souhaiterais recevoir un devis pour les services suivants:
- Installation système
- Maintenance annuelle

Merci,
Enzo CAROFF
"""

# Email simple (pas forward)
TEST_EMAIL_SIMPLE = """
Bonjour Jean,

Voici le document que tu as demandé.

Cordialement,
Marie
"""

# Email avec signature et mentions légales
TEST_EMAIL_WITH_SIGNATURE = """
Bonjour,

Voici les informations demandées.

Cordialement,

Marie Dupont
Responsable Commercial
Tél: 01 23 45 67 89

---
Ce message et toutes les pièces jointes sont confidentiels.
Si vous avez reçu ce message par erreur, merci de le détruire.
"""


async def test_email_agent():
    """Test l'agent IA d'extraction d'emails."""
    print("🧪 Test de l'EmailExtractionAgent")
    
    # Initialiser l'agent
    agent = EmailExtractionAgent()
    
    # Test 1: Email forward problématique
    print("\n1. Test email forward (chaîne d'emails):")
    extracted = await agent.extract_email(
        raw_content=TEST_EMAIL_FORWARD,
        raw_subject="Fwd: Ré: Devis n°2026-0421-001"
    )
    
    print(f"   Sujet: {extracted.subject}")
    print(f"   From: {extracted.from_email} ({extracted.from_name})")
    print(f"   To: {extracted.to_emails}")
    print(f"   Date: {extracted.date}")
    print(f"   Body cleaned (50 premiers chars): {extracted.body_cleaned[:50]}...")
    
    # Vérifier qu'on a bien extrait le DERNIER email (Enzo -> ACORUS)
    assert "enzo.caroff@entreprise.fr" in extracted.from_email or "contact@acorus.fr" in extracted.to_emails
    assert "Demande de devis" in extracted.subject or "devis" in extracted.subject.lower()
    
    # Test 2: Comparaison avec l'ancienne méthode
    print("\n2. Comparaison avec content_cleaner (regex):")
    extracted_regex = content_cleaner.extract_original(TEST_EMAIL_FORWARD, "Fwd: Ré: Devis n°2026-0421-001")
    
    print(f"   IA - Sujet: {extracted.subject}")
    print(f"   Regex - Sujet: {extracted_regex.subject}")
    print(f"   IA - From: {extracted.from_email}")
    print(f"   Regex - From: {extracted_regex.from_email}")
    
    # Test 3: Email simple
    print("\n3. Test email simple (pas forward):")
    extracted_simple = await agent.extract_email(
        raw_content=TEST_EMAIL_SIMPLE,
        raw_subject="Document demandé"
    )
    
    print(f"   Sujet: {extracted_simple.subject}")
    print(f"   Body cleaned: {extracted_simple.body_cleaned[:50]}...")
    assert "Bonjour Jean" in extracted_simple.body_cleaned
    
    # Test 4: Email avec signature
    print("\n4. Test email avec signature:")
    extracted_sig = await agent.extract_email(
        raw_content=TEST_EMAIL_WITH_SIGNATURE,
        raw_subject="Informations"
    )
    
    print(f"   Body cleaned: {extracted_sig.body_cleaned[:100]}...")
    # Vérifier que la signature a été supprimée
    assert "Responsable Commercial" not in extracted_sig.body_cleaned
    assert "Ce message et toutes les pièces jointes" not in extracted_sig.body_cleaned
    
    print("\n✅ Tous les tests passés!")


async def test_real_email_extraction():
    """Test avec un email réel du test précédent."""
    print("\n🧪 Test avec email réel du dataset")
    
    # Lire l'email réel du fichier de test
    test_file = "test_real_email_extraction.py"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraire l'email du fichier de test
        import re
        email_match = re.search(r'TEST_EMAIL_CONTENT = r?"""(.*?)"""', content, re.DOTALL)
        if email_match:
            real_email = email_match.group(1)
            
            agent = EmailExtractionAgent()
            extracted = await agent.extract_email(
                raw_content=real_email,
                raw_subject="Fwd: Important: Meeting Tomorrow"
            )
            
            print(f"   Sujet extrait: {extracted.subject}")
            print(f"   From: {extracted.from_email}")
            print(f"   Body (100 premiers chars): {extracted.body_cleaned[:100]}...")
            
            # Vérifier les résultats
            assert extracted.subject
            assert "Meeting" in extracted.subject or "meeting" in extracted.subject.lower()
    else:
        print("   ⚠️ Fichier de test non trouvé")


if __name__ == "__main__":
    print("🚀 Lancement des tests EmailExtractionAgent")
    
    try:
        asyncio.run(test_email_agent())
        asyncio.run(test_real_email_extraction())
    except Exception as e:
        print(f"❌ Erreur pendant les tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)