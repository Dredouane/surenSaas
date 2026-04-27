#!/usr/bin/env python3
"""
Vérifie ce qui a été stocké dans la base pour l'email.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

async def check_email_in_db():
    """Vérifie l'email dans la base."""
    from app.services.email_database_service import EmailDatabaseService
    
    db = EmailDatabaseService()
    
    # Chercher par message_id
    message_id = "19db02c16b1ced99"
    email = await db.get_email_by_message_id(message_id)
    
    if not email:
        print("❌ Email non trouvé dans la base")
        return
    
    print("✅ Email trouvé dans la base:")
    print(f"   ID: {email.get('id')}")
    print(f"   Sujet: {email.get('subject')}")
    print(f"   Sujet nettoyé: {email.get('subject_cleaned')}")
    print(f"   From: {email.get('sender_email')} ({email.get('sender_name')})")
    print(f"   To: {email.get('recipient_emails')}")
    print()
    
    # Comparer les contenus
    raw_len = len(email.get('content_text_raw', ''))
    cleaned_len = len(email.get('content_text', ''))
    html_len = len(email.get('content_html', ''))
    
    print(f"📊 Tailles des contenus:")
    print(f"   Raw: {raw_len} caractères")
    print(f"   Cleaned: {cleaned_len} caractères")
    print(f"   HTML: {html_len} caractères")
    print()
    
    if raw_len == cleaned_len:
        print("⚠️  ATTENTION: Raw et Cleaned ont la même taille!")
        print("   Le nettoyage n'a peut-être pas fonctionné.")
    else:
        print(f"✅ Différence: {raw_len - cleaned_len} caractères nettoyés")
    
    print()
    print("📝 Extrait du contenu nettoyé (200 premiers caractères):")
    print("-" * 50)
    print(email.get('content_text', '')[:200])
    print("-" * 50)
    
    print()
    print("📝 Extrait du contenu brut (200 premiers caractères):")
    print("-" * 50)
    print(email.get('content_text_raw', '')[:200])
    print("-" * 50)
    
    # Vérifier si c'est le même contenu
    if email.get('content_text', '') == email.get('content_text_raw', ''):
        print("\n❌ PROBLEME: content_text == content_text_raw")
        print("   Le contenu nettoyé n'a pas été stocké séparément!")
    else:
        print("\n✅ OK: content_text différent de content_text_raw")

if __name__ == "__main__":
    if 'SUPABASE_SERVICE_KEY' not in os.environ:
        print("⚠️  Exporte SUPABASE_SERVICE_KEY d'abord")
        sys.exit(1)
    
    asyncio.run(check_email_in_db())