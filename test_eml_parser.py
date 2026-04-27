#!/usr/bin/env python3
"""
Test du parsing .eml avec l'email problématique.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

def test_eml_parser():
    """Teste le parsing .eml sur l'email déjà téléchargé."""
    from app.services.emails.eml_parser import parse_email_chain
    
    # Chercher un .eml dans /tmp
    import glob
    eml_files = glob.glob("/tmp/19db*.eml")
    
    if not eml_files:
        print("❌ Aucun fichier .eml trouvé dans /tmp")
        print("   Lance d'abord un sync-single pour télécharger un .eml")
        return False
    
    eml_path = eml_files[0]
    print(f"📄 Test avec: {eml_path}")
    
    with open(eml_path, "rb") as f:
        raw_eml = f.read()
    
    print(f"📏 Taille du .eml: {len(raw_eml)} bytes")
    
    emails = parse_email_chain(raw_eml)
    
    print(f"\n✅ {len(emails)} emails extraits:")
    for i, email_data in enumerate(emails):
        print(f"\n📧 Email {i+1}:")
        print(f"   Message-ID: {email_data.get('message_id', 'N/A')}")
        print(f"   From: {email_data.get('from_email', 'N/A')}")
        print(f"   To: {email_data.get('to_emails', [])}")
        print(f"   Subject: {email_data.get('subject', 'N/A')}")
        print(f"   Date: {email_data.get('date', 'N/A')}")
        body = email_data.get('body_text', '') or email_data.get('body_html', '') or ''
        print(f"   Body: {len(body)} caractères")
        print(f"   In-Reply-To: {email_data.get('in_reply_to', 'N/A')}")
        print(f"   References: {email_data.get('references', [])}")
    
    if len(emails) > 1:
        print(f"\n🎯 SUCCÈS: {len(emails)} emails extraits de la chaîne!")
    else:
        print(f"\n⚠️ Un seul email extrait - vérifie que le .eml contient bien une chaîne")
    
    return True

if __name__ == "__main__":
    test_eml_parser()