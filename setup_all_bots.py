from app.api.auth import get_supabase
from dotenv import load_dotenv
import os

load_dotenv('.env.test')
supabase = get_supabase()

# GCP URL
GCP_URL = "https://test-surensaas-back-REDACTED-ew.a.run.app"
# Local URL
LOCAL_URL = "https://ethics-each-bonehead.ngrok-free.dev"

# Map tokens and usernames to their respective environments
bots_config = [
    {
        'bot_username': 'Arev_travaux_test_e2e_bot',
        'api_url': GCP_URL,
        'token': os.getenv("TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN")
    },
    {
        'bot_username': 'suren_construction_test_bot',
        'api_url': LOCAL_URL,
        'token': os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_BOT_TOKEN")
    }
]

for b in bots_config:
    if not b['token']:
        print(f"Skipping {b['bot_username']} (no token found)")
        continue
    
    bot = supabase.table('telegram_bots').select('*').eq('bot_username', b['bot_username']).single().execute().data
    if not bot:
        print(f"Bot {b['bot_username']} not found")
        continue
        
    webhook_token = bot['webhook_url'].split('/')[-1]
    new_webhook_url = f"{b['api_url'].rstrip('/')}/api/v1/{bot['org_id']}/telegram/webhook/{webhook_token}"
    
    print(f"Updating {b['bot_username']} to {new_webhook_url}")
    supabase.table('telegram_bots').update({'webhook_url': new_webhook_url}).eq('id', bot['id']).execute()
