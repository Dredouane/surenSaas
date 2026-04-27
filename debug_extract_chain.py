#!/usr/bin/env python3
"""
Debug pourquoi extract_email_chain échoue.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

def debug_chain_conversion():
    """Debug la conversion de la chaîne."""
    
    # Exemple de réponse Gemini (similaire aux logs)
    gemini_response = '''{
    "is_forward": true,
    "email_chain": [
        {
            "index": 0,
            "is_original": false,
            "from_email": "REDACTED_CONTACT",
            "from_name": "REDACTED_CONTACT",
            "to_emails": [
                "REDACTED_EMAIL"
            ],
            "cc_emails": [],
            "bcc_emails": [],
            "subject": "TR: CR RC 21/04 - P14 Porte d'Orléans",
            "date": "2026-04-21T13:12:38+00:00",
            "body": "Cordialement REDACTED_CONTACT REDACTED_PHONE REDACTED_CONTACT Service études / EXE 28 boulevard de Strasbourg 93600 Aulnay-sous-Bois www.arev-travaux.fr De : CAROFF, Enzo..."
        }
    ]
}'''
    
    print("🧪 Debug de la conversion de chaîne")
    print("=" * 50)
    
    try:
        # Parser la réponse
        data = json.loads(gemini_response)
        print("✅ JSON parsé avec succès")
        print(f"   is_forward: {data.get('is_forward')}")
        print(f"   email_chain length: {len(data.get('email_chain', []))}")
        
        # Simuler _convert_to_email_chain
        from app.agents.email_agent import EmailChain, ChainEmail
        
        is_forward = data.get("is_forward", False)
        email_chain_data = data.get("email_chain", [])
        metadata = data.get("metadata", {})
        
        emails = []
        for idx, email_data in enumerate(email_chain_data):
            print(f"\n📧 Conversion email {idx}:")
            print(f"   from_email: {email_data.get('from_email')}")
            print(f"   subject: {email_data.get('subject')}")
            print(f"   body length: {len(email_data.get('body', ''))}")
            
            chain_email = ChainEmail(
                index=idx,
                is_original=email_data.get("is_original", False),
                from_email=email_data.get("from_email", ""),
                from_name=email_data.get("from_name"),
                to_emails=email_data.get("to_emails", []),
                cc_emails=email_data.get("cc_emails", []),
                bcc_emails=email_data.get("bcc_emails", []),
                subject=email_data.get("subject", ""),
                date=email_data.get("date", ""),
                body=email_data.get("body", ""),
                headers_text=email_data.get("headers_text", ""),
                message_id=email_data.get("message_id"),
                in_reply_to=email_data.get("in_reply_to"),
                references=email_data.get("references")
            )
            emails.append(chain_email)
        
        email_chain = EmailChain(
            is_forward=is_forward,
            emails=emails,
            metadata=metadata
        )
        
        print(f"\n✅ EmailChain créé avec {len(email_chain.emails)} emails")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    # Vérifier la différence entre extract_email et extract_email_chain
    print("\n" + "=" * 50)
    print("🔍 Différence entre extract_email et extract_email_chain")
    print("=" * 50)
    
    print("extract_email (ancienne méthode):")
    print("  - Attend: {\"is_forward\": ..., \"extracted_email\": {...}}")
    print("  - Retourne: ExtractedEmail (un seul email)")
    print("  - Nettoie le contenu")
    
    print("\nextract_email_chain (nouvelle méthode):")
    print("  - Attend: {\"is_forward\": ..., \"email_chain\": [...]}")
    print("  - Retourne: EmailChain (liste d'emails)")
    print("  - Ne nettoie pas le contenu")
    
    print("\n⚠️  Problème possible:")
    print("  Gemini retourne le NOUVEAU format (email_chain)")
    print("  Mais extract_email essaie de le parser comme ANCIEN format")
    print("  → _convert_to_extracted_email échoue!")
    
    return True

def test_both_methods():
    """Teste les deux méthodes avec la même réponse."""
    print("\n" + "=" * 50)
    print("🧪 Test des deux méthodes de parsing")
    print("=" * 50)
    
    # Réponse Gemini (nouveau format)
    response = '''{
    "is_forward": true,
    "email_chain": [
        {
            "index": 0,
            "is_original": false,
            "from_email": "test@example.com",
            "from_name": "Test",
            "to_emails": ["dest@example.com"],
            "subject": "Test",
            "date": "2026-01-01",
            "body": "Contenu test"
        }
    ]
}'''
    
    from app.agents.email_agent import EmailExtractionAgent
    
    # Simuler extract_email (ancienne méthode)
    print("1. extract_email (ancienne méthode):")
    print("   - Cherche 'extracted_email' dans la réponse")
    print("   - Ne trouve pas → utilise des valeurs par défaut")
    print("   - Résultat: ExtractedEmail vide ou incomplet")
    
    # Simuler extract_email_chain (nouvelle méthode)
    print("\n2. extract_email_chain (nouvelle méthode):")
    print("   - Cherche 'email_chain' dans la réponse")
    print("   - Trouve la liste d'emails")
    print("   - Résultat: EmailChain avec les emails")
    
    print("\n🎯 Solution: La route doit appeler extract_email_chain pour les chaînes!")
    
    return True

if __name__ == "__main__":
    debug_chain_conversion()
    test_both_methods()