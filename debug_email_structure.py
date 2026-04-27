#!/usr/bin/env python3
"""
Debug la structure de l'email problématique.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

from app.services.emails.content_cleaner import ContentCleaner

# Créer une instance du cleaner
cleaner = ContentCleaner()

# Email de test (remplace par le vrai contenu si tu l'as)
TEST_EMAIL = """TR: CR RC 21/04 - P14 Porte d'Orléans

[Contenu de l'email forward... probablement avec plusieurs forwards imbriqués]

--- Forwarded message ---
De: Personne A <a@exemple.com>
Date: date1
À: Personne B <b@exemple.com>
Objet: Sujet 1

Contenu 1

--- Forwarded message ---  
De: Personne B <b@exemple.com>
Date: date2
À: Personne C <c@exemple.com>
Objet: Sujet 2

Contenu 2
"""

print("=== Analyse de la structure d'email ===")
print()

# 1. Détecter si c'est un forward
is_forward = cleaner.detect_forward(TEST_EMAIL)
print(f"1. Détecté comme forward: {is_forward}")
print()

# 2. Extraire les headers
headers = cleaner.extract_original_headers(TEST_EMAIL)
print(f"2. Headers extraits: {list(headers.keys())}")
for key, value in headers.items():
    print(f"   {key}: {value[:100]}...")
print()

# 3. Extraire le corps
body = cleaner.extract_original_body(TEST_EMAIL)
print(f"3. Corps extrait (200 premiers caractères):")
print(body[:200])
print("...")
print()

# 4. Analyser avec extract_original
extracted = cleaner.extract_original(TEST_EMAIL, "TR: CR RC 21/04 - P14 Porte d'Orléans")
print(f"4. Résultat complet:")
print(f"   From: {extracted.from_email} ({extracted.from_name})")
print(f"   To: {extracted.to_emails}")
print(f"   Subject: {extracted.subject}")
print(f"   Date: {extracted.date}")
print(f"   Body cleaned (100 premiers): {extracted.body_cleaned[:100]}...")
print()

# 5. Chercher tous les séparateurs
print("5. Recherche de tous les séparateurs de forward:")
forward_patterns = cleaner.FORWARD_SEPARATOR_PATTERNS
for pattern in forward_patterns:
    import re
    matches = list(re.finditer(pattern, TEST_EMAIL, re.IGNORECASE))
    for match in matches:
        print(f"   Pattern '{pattern[:30]}...' trouvé à position {match.start()}")
        # Afficher un peu de contexte
        start = max(0, match.start() - 50)
        end = min(len(TEST_EMAIL), match.end() + 50)
        print(f"   Contexte: ...{TEST_EMAIL[start:end]}...")
        print()