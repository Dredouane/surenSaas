#!/usr/bin/env python3
"""
Trouve le dernier email reçu dans Gmail.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "surenSaasBack"))

async def find_recent_email():
    """Trouve le dernier email reçu."""
    from app.services.email_database_service import EmailDatabaseService
    from app.services.emails.gmail_client import create_gmail_client
    
    print("🔍 Recherche du dernier email reçu...")
    
    # Récupérer un compte email
    db = EmailDatabaseService()
    accounts = await db.get_email_accounts_by_org("test")  # À adapter
    
    if not accounts:
        print("❌ Aucun compte email trouvé")
        return
    
    account = accounts[0]
    print(f"📧 Compte: {account['email_address']}")
    
    # Connecter à Gmail
    try:
        gmail_client = create_gmail_client(account["oauth_refresh_token"])
        await gmail_client.connect()
        
        # Récupérer les derniers messages
        messages = await gmail_client.list_messages(max_results=5)
        
        print(f"\n📨 {len(messages)} derniers messages:")
        for i, msg in enumerate(messages):
            print(f"\n{i+1}. Message ID: {msg['id']}")
            print(f"   Thread ID: {msg.get('threadId', 'N/A')}")
            
            # Récupérer les détails
            try:
                message_detail = await gmail_client.get_message(msg['id'])
                headers = gmail_client.parse_headers(message_detail)
                subject = headers.get("Subject", "Pas de sujet")
                from_addr = headers.get("From", "Inconnu")
                
                print(f"   Sujet: {subject[:50]}...")
                print(f"   De: {from_addr}")
                
                # Vérifier si c'est un forward
                raw_body = gmail_client.get_body_text(message_detail)
                de_count = raw_body.count("De :") + raw_body.count("From :")
                print(f"   Blocs 'De :': {de_count}")
                if de_count > 1:
                    print(f"   ⚠️  CHAÎNE DÉTECTÉE!")
                
            except Exception as e:
                print(f"   ❌ Erreur récupération: {e}")
        
        # Suggestion pour tester
        if messages:
            print(f"\n🎯 Pour tester avec sync-single:")
            print(f"   Message ID: {messages[0]['id']}")
            print(f"   Account ID: {account['id']}")
            print(f"\n📋 Curl command:")
            print(f'curl -X POST "http://localhost:8000/api/v1/REDACTED_ORG_SLUG/emails/sync-single" \\')
            print(f'  -H "Content-Type: application/json" \\')
            print(f'  -d \'{{"account_id": "{account["id"]}", "gmail_message_id": "{messages[0]["id"]}"}}\'')
        
    except Exception as e:
        print(f"❌ Erreur connexion Gmail: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if 'SUPABASE_SERVICE_KEY' not in os.environ:
        print("⚠️  Exporte SUPABASE_SERVICE_KEY d'abord")
        sys.exit(1)
    
    asyncio.run(find_recent_email())