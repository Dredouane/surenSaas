#!/usr/bin/env python3
"""
Simule la réponse de l'API pour voir ce que le frontend reçoit.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

async def test_api_response():
    """Teste ce que l'API retourne pour un email."""
    from app.api.emails import get_email
    from app.services.email_database_service import EmailDatabaseService
    from app.api.auth import get_supabase
    
    print("🧪 Test de la réponse API")
    print("=" * 50)
    
    db = EmailDatabaseService()
    
    # Chercher l'email par message_id
    message_id = "19db02c16b1ced99"
    email = await db.get_email_by_message_id(message_id)
    
    if not email:
        print("❌ Email non trouvé")
        return
    
    email_id = email["id"]
    
    print(f"📧 Email ID: {email_id}")
    print(f"📊 Champs disponibles: {list(email.keys())}")
    
    # Vérifier les champs de contenu
    content_fields = ["content_text", "content_html", "content_text_raw"]
    for field in content_fields:
        if field in email:
            value = email[field]
            print(f"\n📝 {field}:")
            print(f"   Présent: OUI")
            print(f"   Taille: {len(value) if value else 0} caractères")
            print(f"   Début: {value[:100] if value else '(vide)'}...")
        else:
            print(f"\n📝 {field}: NON PRÉSENT")
    
    # Simuler ce que l'API retourne (après notre modification)
    print("\n🎯 Ce que l'API retourne (après modification):")
    
    formatted_email = dict(email)
    
    if formatted_email.get("content_text") and formatted_email.get("content_html"):
        formatted_email["display_content"] = formatted_email["content_text"]
        formatted_email["raw_html_content"] = formatted_email["content_html"]
        print("   ✅ 'display_content' = content_text (nettoyé)")
        print("   ✅ 'raw_html_content' = content_html (brut)")
    elif formatted_email.get("content_text"):
        formatted_email["display_content"] = formatted_email["content_text"]
        print("   ✅ 'display_content' = content_text")
    elif formatted_email.get("content_html"):
        formatted_email["display_content"] = formatted_email["content_html"]
        print("   ✅ 'display_content' = content_html")
    
    print(f"\n🔍 Champs retournés par l'API:")
    for key in ["display_content", "content_text", "content_html", "content_text_raw"]:
        if key in formatted_email:
            value = formatted_email[key]
            print(f"   {key}: {len(value) if value else 0} caractères")
    
    # Vérifier ce que le frontend utilise actuellement
    print("\n🔧 Recommandation pour le frontend:")
    print("   Le frontend devrait utiliser 'display_content' si disponible")
    print("   Sinon, utiliser 'content_text' (nettoyé)")
    print("   Éviter d'utiliser 'content_html' directement")
    
    return True

if __name__ == "__main__":
    if 'SUPABASE_SERVICE_KEY' not in os.environ:
        print("⚠️  Exporte SUPABASE_SERVICE_KEY d'abord")
        sys.exit(1)
    
    asyncio.run(test_api_response())