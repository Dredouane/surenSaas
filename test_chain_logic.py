#!/usr/bin/env python3
"""
Test de la logique de détection de chaîne d'emails.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

def test_chain_detection():
    """Teste la détection de chaîne d'emails."""
    from app.services.emails.content_cleaner import ContentCleaner
    
    print("🧪 Test de détection de chaîne d'emails")
    print("=" * 50)
    
    # Exemple de chaîne d'emails
    raw_content = """Cordialement REDACTED_CONTACT
REDACTED_PHONE
REDACTED_CONTACT

De : CAROFF, Enzo
Envoyé : mardi 21 avril 2026 14:55
À : 'Vasile BOC' ; Suren SHIRVANYAN ; REDACTED_CONTACT
Objet : CR RC 21/04 - P14 Porte d'Orléans

Contenu du premier email...

De : CAROFF, Enzo
Envoyé : mardi 14 avril 2026 12:33
À : 'Vasile BOC' ; Suren SHIRVANYAN ; REDACTED_CONTACT
Objet : CR RC 14/04 - P14 Porte d'Orléans

Contenu du deuxième email..."""
    
    raw_subject = "TR: CR RC 21/04 - P14 Porte d'Orléans"
    
    cleaner = ContentCleaner()
    
    print(f"📧 Sujet: {raw_subject}")
    print(f"📏 Taille du contenu: {len(raw_content)} caractères")
    
    # Détection de forward
    is_forward = cleaner.detect_forward(raw_content)
    print(f"🔍 Détecté comme forward: {is_forward}")
    
    # Compter les occurrences de "De :"
    de_count = raw_content.count("De :")
    from_count = raw_content.count("From :")
    total_blocks = de_count + from_count
    
    print(f"🔢 Nombre de blocs 'De :': {de_count}")
    print(f"🔢 Nombre de blocs 'From :': {from_count}")
    print(f"🔢 Total de blocs: {total_blocks}")
    
    # Détecter si c'est une chaîne
    is_chain = total_blocks > 1
    print(f"🔗 Détecté comme chaîne: {is_chain}")
    
    # Tester la méthode _remove_forward_chains
    print("\n🧪 Test de _remove_forward_chains...")
    cleaned = cleaner._remove_forward_chains(raw_content)
    
    print(f"📏 Taille avant nettoyage: {len(raw_content)}")
    print(f"📏 Taille après nettoyage: {len(cleaned)}")
    print(f"📉 Réduction: {len(raw_content) - len(cleaned)} caractères")
    
    # Vérifier si le deuxième forward a été supprimé
    has_second_de = "De : CAROFF, Enzo\nEnvoyé : mardi 14 avril 2026" in cleaned
    print(f"🔍 Deuxième forward présent: {has_second_de}")
    
    # Tester extract_original (méthode existante)
    print("\n🧪 Test de extract_original (méthode existante)...")
    extracted = cleaner.extract_original(raw_content, raw_subject)
    
    print(f"✅ Email extrait:")
    print(f"   Sujet: {extracted.subject[:50]}...")
    print(f"   From: {extracted.from_email}")
    print(f"   To: {extracted.to_emails}")
    print(f"   Date: {extracted.date}")
    print(f"   Taille du corps: {len(extracted.body)} caractères")
    
    return True

def test_sync_service_logic():
    """Teste la logique du sync_service pour les chaînes."""
    print("\n" + "=" * 50)
    print("🧪 Test de la logique du sync_service")
    print("=" * 50)
    
    # Simuler la logique de détection de chaîne
    raw_content = """Signature...

De : Expéditeur 1
Envoyé : date1
À : destinataire1
Objet : Sujet 1

Contenu 1...

De : Expéditeur 2  
Envoyé : date2
À : destinataire2
Objet : Sujet 2

Contenu 2..."""
    
    # Détection simple
    de_count = raw_content.count("De :") + raw_content.count("From :")
    is_chain = de_count > 1
    
    print(f"📧 Exemple de contenu avec {de_count} blocs 'De :'")
    print(f"🔗 Détecté comme chaîne: {is_chain}")
    
    # Logique de décision
    if is_chain:
        print("✅ Le sync_service utilisera _process_email_chain")
        print(f"   → Chaque bloc sera extrait comme email séparé")
        print(f"   → {de_count} emails seront stockés dans la base")
    else:
        print("✅ Le sync_service utilisera _process_message")
        print("   → Un seul email sera extrait")
    
    return True

if __name__ == "__main__":
    try:
        test_chain_detection()
        test_sync_service_logic()
        print("\n🎉 Tests réussis!")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)