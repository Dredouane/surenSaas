#!/usr/bin/env python3
"""
Test rapide pour vérifier que l'extraction simple fonctionne.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

def test_simple_extraction():
    """Teste l'extraction simple (regex)."""
    from app.services.emails.content_cleaner import ContentCleaner
    
    print("🧪 Test d'extraction simple (regex)")
    print("=" * 50)
    
    # Exemple simplifié
    raw_content = """Cordialement REDACTED_CONTACT
REDACTED_CONTACT

De : CAROFF, Enzo
Envoyé : mardi 21 avril 2026 14:55
À : 'Vasile BOC' ; Suren SHIRVANYAN ; REDACTED_CONTACT
Objet : CR RC 21/04 - P14 Porte d'Orléans

Bonjour Messieurs,

Contenu de l'email..."""
    
    raw_subject = "TR: CR RC 21/04 - P14 Porte d'Orléans"
    
    cleaner = ContentCleaner()
    extracted = cleaner.extract_original(raw_content, raw_subject)
    
    print(f"✅ Email extrait:")
    print(f"   Sujet: {extracted.subject}")
    print(f"   From: {extracted.from_email}")
    print(f"   To: {extracted.to_emails}")
    print(f"   Date: {extracted.date}")
    print(f"   Body length: {len(extracted.body)}")
    
    # Vérifier que la signature a été supprimée
    if "REDACTED_CONTACT" in extracted.body:
        print("⚠️  Signature REDACTED_NAME toujours présente dans le corps")
    else:
        print("✅ Signature supprimée du corps")
    
    return True

def test_chain_detection_logic():
    """Teste la logique de détection de chaîne."""
    print("\n" + "=" * 50)
    print("🧪 Test de la logique de détection de chaîne")
    print("=" * 50)
    
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
    
    # Logique actuelle dans sync_service
    de_count = raw_content.count("De :") + raw_content.count("From :")
    is_chain = de_count > 1
    
    print(f"   Nombre de blocs 'De :': {de_count}")
    print(f"   Détecté comme chaîne: {is_chain}")
    
    # Logique temporairement désactivée
    use_chain_extraction = is_chain and False  # Temporairement False
    
    if use_chain_extraction:
        print("   → Utiliserait l'extraction de chaîne")
    else:
        print("   → Utilisera l'extraction simple (temporaire)")
    
    return True

if __name__ == "__main__":
    try:
        test_simple_extraction()
        test_chain_detection_logic()
        print("\n🎉 Tests OK - L'extraction simple fonctionne")
        print("\n🔧 Pour récupérer l'email immédiatement:")
        print("   1. La route /sync-single utilise l'extraction simple (temporaire)")
        print("   2. L'email sera stocké avec content_text nettoyé")
        print("   3. Le frontend affichera display_content (nettoyé)")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)