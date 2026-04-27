#!/usr/bin/env python3
"""
Vérifie le contenu HTML stocké pour l'email.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

async def check_html_content():
    """Vérifie le contenu HTML de l'email."""
    from app.services.email_database_service import EmailDatabaseService
    
    db = EmailDatabaseService()
    
    # Chercher par message_id
    message_id = "19db02c16b1ced99"
    email = await db.get_email_by_message_id(message_id)
    
    if not email:
        print("❌ Email non trouvé")
        return
    
    html_content = email.get('content_html', '')
    text_content = email.get('content_text', '')
    raw_content = email.get('content_text_raw', '')
    
    print("📊 Tailles des contenus:")
    print(f"   HTML: {len(html_content)} caractères")
    print(f"   Text: {len(text_content)} caractères")
    print(f"   Raw: {len(raw_content)} caractères")
    
    # Vérifier si le HTML contient la chaîne complète
    de_count_html = html_content.count("De :") + html_content.count("From :")
    de_count_text = text_content.count("De :") + text_content.count("From :")
    
    print(f"\n🔍 Nombre de blocs 'De :'/'From :':")
    print(f"   HTML: {de_count_html}")
    print(f"   Text: {de_count_text}")
    
    # Extraire un échantillon du HTML
    print(f"\n📝 Extrait du HTML (500 premiers caractères):")
    print("-" * 50)
    print(html_content[:500])
    print("-" * 50)
    
    # Chercher la signature de REDACTED_NAME dans le HTML
    if "REDACTED_CONTACT" in html_content:
        print("\n🔍 Signature REDACTED_CONTACT trouvée dans le HTML")
        # Trouver la position
        pos = html_content.find("REDACTED_CONTACT")
        print(f"   Position: {pos}")
        print(f"   Contexte: {html_content[pos-50:pos+100]}")
    
    # Chercher le deuxième forward dans le HTML
    if "De : CAROFF, Enzo\nEnvoyé : mardi 14 avril" in html_content:
        print("\n🔍 DEUXIÈME forward trouvé dans le HTML!")
        pos = html_content.find("De : CAROFF, Enzo\nEnvoyé : mardi 14 avril")
        print(f"   Position: {pos}")
        print(f"   Contexte: {html_content[pos-50:pos+200]}")
    
    # Vérifier ce que le frontend reçoit
    print(f"\n🎯 Ce que le frontend reçoit:")
    print(f"   Le frontend reçoit probablement 'content_html' ou 'content_text_raw'")
    print(f"   Le frontend devrait recevoir 'content_text' (nettoyé)")
    
    # Vérifier l'API
    print(f"\n🔧 Vérification de l'API:")
    print(f"   Route: GET /api/v1/REDACTED_ORG_SLUG/emails/{email['id']}")
    print(f"   Vérifie quel champ est retourné par l'API")

if __name__ == "__main__":
    if 'SUPABASE_SERVICE_KEY' not in os.environ:
        print("⚠️  Exporte SUPABASE_SERVICE_KEY d'abord")
        sys.exit(1)
    
    asyncio.run(check_html_content())