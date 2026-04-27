import os
from app.api.auth import get_supabase
from dotenv import load_dotenv
import hashlib

load_dotenv('.env.test')
supabase = get_supabase()

# 1. Restore the secret for the GCP bot (the one I modified)
print("🔄 Restauration du secret du bot GCP...")
supabase.table('telegram_bots').update({'webhook_secret': 'gg2qfHzu1OKpkyQbS-fZ-jV6nt4CvCQ1_VdLn-65VU0'}).eq('bot_username', 'suren_construction_test_bot').execute()

# 2. Register the local E2E bot
bot_username = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_USERNAME")
bot_token = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN")
# Need to get org_id, let's pick the one found in the existing record
org_id = 'REDACTEDORG' 
company_id = 'REDACTED'

token_hash = hashlib.sha256(bot_token.encode()).hexdigest()

# For local testing, we don't necessarily need a secret, but let's be consistent
webhook_secret = 'local_test_secret'
webhook_url = 'https://ethics-each-bonehead.ngrok-free.dev/api/v1/REDACTEDORG/telegram/webhook/local_token'

bot_data = {
    'org_id': org_id,
    'company_id': company_id,
    'bot_token_hash': token_hash,
    'bot_username': bot_username,
    'bot_id': int(bot_token.split(':')[0]),
    'webhook_url': webhook_url,
    'webhook_secret': webhook_secret,
    'is_active': True,
    'is_configured': True,
    'description': 'Bot local E2E'
}

print(f"➕ Enregistrement du bot local: {bot_username}")
res = supabase.table('telegram_bots').insert(bot_data).execute()
print(f"Résultat insertion: {res.data}")
