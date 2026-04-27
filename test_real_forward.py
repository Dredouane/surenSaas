#!/usr/bin/env python3
"""
Test avec un email forward réel plus complexe.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

from app.services.emails.content_cleaner import content_cleaner

def test_real_forward_chain():
    """Test avec une chaîne de forwards réelle."""
    email_content = """Bonjour,

Je te forwarde toute la discussion.

---
Forwarded message ---
De : Service Client <service@entreprise.com>
Date: 20 avril 2026 à 14:30
À : client@domaine.com
Objet: Votre commande #12345

Bonjour,

Votre commande a été expédiée.

Cordialement,
Service Client

---
Forwarded message ---
De : client@domaine.com
Date: 20 avril 2026 à 15:15
À : Service Client <service@entreprise.com>
Objet: Re: Votre commande #12345

Merci pour l'information. Quand puis-je m'attendre à la livraison ?

---
Forwarded message ---
De : Service Client <service@entreprise.com>
Date: 20 avril 2026 à 16:00
À : client@domaine.com
Objet: Re: Votre commande #12345

La livraison est prévue pour demain.

Cordialement,
Service Client"""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test chaîne de forwards réelle ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject}")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

def test_forward_without_separator():
    """Test avec forward sans séparateur explicite (commence directement par 'De :')."""
    email_content = """Je forwarde ce message:

De : Test User <test@example.com>
À : recipient@example.com
Objet: Test sans séparateur

Contenu du message.

Signature."""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test forward sans séparateur ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject}")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

def test_mixed_language_headers():
    """Test avec headers mélangés français/anglais."""
    email_content = """Forward mixte:

--- Forwarded message ---
From: John Smith <john@example.com>
Date: 21 avril 2026 à 11:00
To: Marie Dupont <marie@example.com>
Subject: Meeting tomorrow

Hello Marie,

Let's meet tomorrow at 10am.

Best,
John"""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test headers mélangés ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject}")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

if __name__ == "__main__":
    print("Tests avancés d'extraction d'emails forward\n")
    test_real_forward_chain()
    test_forward_without_separator()
    test_mixed_language_headers()