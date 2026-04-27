#!/usr/bin/env python3
"""
Debug de la structure de l'email.
"""

import re

# Extrait du début de l'email
email_start = """mardi 21 avril 2026 14:55 À : 'Vasile BOC' <v.boc@groupetcpr.com>; Suren SHIRVANYAN <s.vanyan@REDACTED_DOMAIN>; REDACTED_CONTACT <REDACTED_CONTACT>; j.boutry <j.boutry@wellechafaudage.com>; Carlos DE ALMEID <carlos.dealmeida@REDACTED_DOMAIN> Cc : ROUSSEAUX, Dimitri <di.rousseaux@bouygues-construction.com>; GONSOLIN, Mayeul <m.gonsolin@bouygues-construction.com>; FASSIH, Youssef <y.fassih@bouygues-construction.com>; DA SILVA, Fabien <fa.dasilva@bouygues-construction.com> Objet : CR RC 21/04 - P14 Porte d'Orléans Bonjour Messieurs, Vous trouverez ci-dessous le CR de la réunion de coordination de ce jour :"""

print("=== Analyse de la structure ===")
print(f"Contenu: {email_start[:200]}...")
print()

# Test de patterns
patterns = [
    (r"À\s*:\s*([^\n]+)", "À :"),
    (r"Cc\s*:\s*([^\n]+)", "Cc :"),
    (r"Objet\s*:\s*([^\n]+)", "Objet :"),
]

for pattern, name in patterns:
    match = re.search(pattern, email_start, re.IGNORECASE)
    if match:
        print(f"{name} trouvé: {match.group(1)[:100]}...")
    else:
        print(f"{name} NON trouvé")

print()
print("=== Test avec lookahead amélioré ===")

# Test avec lookahead
pattern = r"À\s*:\s*([^\n]{1,500}?)(?=\s*(?:Cc|Objet|$|\n))"
match = re.search(pattern, email_start, re.IGNORECASE)
if match:
    print(f"À : (avec lookahead): {match.group(1)}")
    
# Test pour Cc
pattern = r"Cc\s*:\s*([^\n]{1,500}?)(?=\s*(?:Objet|$|\n))"
match = re.search(pattern, email_start, re.IGNORECASE)
if match:
    print(f"Cc : (avec lookahead): {match.group(1)}")
    
# Test pour Objet
pattern = r"Objet\s*:\s*([^\n]{1,500}?)(?=\s*(?:Bonjour|$|\n))"
match = re.search(pattern, email_start, re.IGNORECASE)
if match:
    print(f"Objet : (avec lookahead): {match.group(1)}")