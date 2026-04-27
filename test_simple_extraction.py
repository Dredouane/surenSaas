#!/usr/bin/env python3
"""
Test simple de l'extraction d'emails.
"""

import re
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "surenSaasBack"))

# Importer seulement ce dont on a besoin
from app.services.emails.content_cleaner import ContentCleaner, ExtractedEmail


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


def test_regex_extraction():
    """Test l'extraction regex."""
    print("🧪 Test du content_cleaner (regex)")
    
    cleaner = ContentCleaner()
    
    # Test avec l'email forward problématique
    extracted = cleaner.extract_original(TEST_EMAIL_FORWARD, "Fwd: Ré: Devis n°2026-0421-001")
    
    print(f"   Sujet: {extracted.subject}")
    print(f"   From: {extracted.from_email} ({extracted.from_name})")
    print(f"   To: {extracted.to_emails}")
    print(f"   Date: {extracted.date}")
    print(f"   Body cleaned (50 premiers chars): {extracted.body_cleaned[:50]}...")
    
    # Vérifier ce que le regex extrait
    print(f"\n   ⚠️ Résultat regex:")
    print(f"     - From: {extracted.from_email}")
    print(f"     - On veut: enzo.caroff@entreprise.fr (DERNIER forward)")
    
    # Analyser manuellement ce qui se passe
    print(f"\n   🔍 Analyse manuelle:")
    
    # Détecter les forwards
    is_forward = cleaner.detect_forward(TEST_EMAIL_FORWARD)
    print(f"     - Détecté comme forward: {is_forward}")
    
    # Extraire les headers
    headers = cleaner.extract_original_headers(TEST_EMAIL_FORWARD)
    print(f"     - Headers trouvés: {list(headers.keys())}")
    print(f"     - From header: {headers.get('from', 'N/A')}")
    
    # Extraire le corps
    body = cleaner.extract_original_body(TEST_EMAIL_FORWARD)
    print(f"     - Corps extrait (100 premiers chars): {body[:100]}...")
    
    return extracted


def analyze_problem():
    """Analyse le problème d'extraction."""
    print("\n🔍 Analyse du problème:")
    
    content = TEST_EMAIL_FORWARD
    
    # Chercher tous les séparateurs
    forward_patterns = [
        r"-{3,}\s*Forwarded message\s*-{3,}",
        r"_+\s*Original Message\s*_+",
        r"Begin forwarded message:",
    ]
    
    print("   Séparateurs trouvés:")
    for pattern in forward_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            print(f"     - '{match.group()}' à la position {match.start()}")
    
    # Compter les forwards
    separator_count = 0
    for pattern in forward_patterns:
        separator_count += len(list(re.finditer(pattern, content, re.IGNORECASE)))
    
    print(f"\n   Total séparateurs: {separator_count}")
    print(f"   C'est une chaîne de {separator_count} forwards imbriqués")
    
    # Le problème: le regex extrait le PREMIER forward qu'il trouve
    # Mais on veut le DERNIER (le plus récent)
    print(f"\n   ⚠️ Problème identifié:")
    print(f"     - Le regex actuel extrait le PREMIER forward")
    print(f"     - On a besoin du DERNIER forward (le plus récent)")
    print(f"     - Solution IA: comprendre le contexte et extraire le dernier")


def test_improved_regex():
    """Test une version améliorée du regex."""
    print("\n🧪 Test regex amélioré (trouver dernier forward)")
    
    content = TEST_EMAIL_FORWARD
    
    # Pattern pour trouver le DERNIER séparateur
    forward_pattern = r"-{3,}\s*Forwarded message\s*-{3,}"
    
    # Trouver TOUS les matches
    matches = list(re.finditer(forward_pattern, content, re.IGNORECASE))
    
    if matches:
        print(f"   Nombre de forwards trouvés: {len(matches)}")
        
        # Prendre le DERNIER match (le plus récent)
        last_match = matches[-1]
        print(f"   Dernier séparateur à la position: {last_match.start()}")
        
        # Extraire le contenu après le dernier séparateur
        content_after_last = content[last_match.end():]
        print(f"   Contenu après dernier séparateur (100 premiers chars):")
        print(f"   '{content_after_last[:100]}...'")
        
        # Maintenant extraire les headers de cette section
        # Pattern pour "De :" après le dernier séparateur
        de_pattern = r"De\s*:\s*(.+?)(?:\n|$)"
        de_match = re.search(de_pattern, content_after_last, re.IGNORECASE)
        
        if de_match:
            print(f"\n   ✅ Dernier forward trouvé:")
            print(f"     - De: {de_match.group(1)}")
            print(f"     - C'est bien Enzo -> ACORUS (le dernier)")
        else:
            print(f"\n   ❌ Pas de 'De :' trouvé après dernier séparateur")
    else:
        print("   ❌ Aucun forward trouvé")


def main():
    """Fonction principale."""
    print("🚀 Analyse de l'extraction d'emails forwards")
    
    try:
        # Test regex actuel
        extracted = test_regex_extraction()
        
        # Analyser le problème
        analyze_problem()
        
        # Test regex amélioré
        test_improved_regex()
        
        print("\n🎯 Conclusion:")
        print("   - Le regex actuel extrait le PREMIER forward (ACORUS -> Enzo)")
        print("   - On veut le DERNIER forward (Enzo -> ACORUS)")
        print("   - L'agent IA devrait résoudre ce problème en comprenant le contexte")
        print("   - Solution temporaire: améliorer extract_original_body() pour trouver le dernier séparateur")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()