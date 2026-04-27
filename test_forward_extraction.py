#!/usr/bin/env python3
"""
Test de l'extraction des emails forward.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

from app.services.emails.content_cleaner import content_cleaner

def test_simple_forward():
    """Test d'un forward simple avec séparateur Gmail."""
    email_content = """Bonjour,

Voici le message que j'ai reçu.

---
Forwarded message ---
De : John Doe <john@example.com>
Date: 21 avril 2026 à 10:30
À : Jane Smith <jane@example.com>
Objet: Réunion demain

Bonjour Jane,

La réunion est prévue pour demain à 14h.

Cordialement,
John"""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test 1: Forward simple ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject}")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

def test_multiple_forwards():
    """Test avec plusieurs forwards imbriqués (le problème original)."""
    email_content = """Salut,

Je forwarde la chaîne complète.

---
Forwarded message ---
De : Alice <alice@example.com>
Date: 20 avril 2026 à 15:00
À : Bob <bob@example.com>
Objet: Premier message

Message 1 de Alice.

---
Forwarded message ---
De : Bob <bob@example.com>
Date: 20 avril 2026 à 16:00
À : Alice <alice@example.com>
Objet: Re: Premier message

Réponse de Bob.

---
Forwarded message ---
De : Alice <alice@example.com>
Date: 20 avril 2026 à 17:00
À : Bob <bob@example.com>
Objet: Suite de la discussion

Dernier message de Alice."""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test 2: Multiple forwards (doit extraire le dernier seulement) ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject} (attendu: 'Suite de la discussion')")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

def test_french_headers():
    """Test avec headers en français."""
    email_content = """Message avec forward français.

---
Message transféré ---
De : Pierre Dupont <pierre@example.com>
Envoyé : 21 avril 2026 11:45
À : Marie Martin <marie@example.com>
Objet: Document important

Voici le document demandé.

Cordialement,
Pierre"""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test 3: Headers français ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject}")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

def test_no_forward():
    """Test sans forward (doit retourner le contenu original)."""
    email_content = """Bonjour,

Ceci est un email normal sans forward.

Cordialement,
Test"""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test 4: Pas de forward ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject}")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

def test_extract_full_email():
    """Test de l'extraction complète avec headers."""
    email_content = """Forward d'email.

--- Forwarded message ---
De : "Test User" <test@example.com>
Date: 21 avril 2026 à 09:00
À : recipient@example.com
Objet: Test d'extraction

Contenu du message original.

Signature."""

    extracted = content_cleaner.extract_original(email_content, "")
    print("=== Test 5: Extraction complète ===")
    print(f"From: {extracted.from_name} <{extracted.from_email}>")
    print(f"To: {', '.join(extracted.to_emails)}")
    print(f"Subject: {extracted.subject}")
    print(f"Date: {extracted.date}")
    print(f"Body:\n{extracted.body}")
    print(f"Cleaned body:\n{extracted.body_cleaned}")
    print()

if __name__ == "__main__":
    print("Test de l'extraction des emails forward\n")
    test_simple_forward()
    test_multiple_forwards()
    test_french_headers()
    test_no_forward()
    test_extract_full_email()