import os
import httpx
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from app.api.auth import get_supabase

# Load env file
load_dotenv('.env.test')

async def setup():
    token = os.getenv("TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN")
    api_url = os.getenv("API_URL")
    
    if not token or not api_url:
        print(f"❌ Error: token={bool(token)}, api_url={api_url}")
        return

    supabase = get_supabase()
    bot_id = int(token.split(':')[0])
    bot = supabase.table('telegram_bots').select('*').eq('bot_id', bot_id).single().execute().data
    
    if not bot:
        print(f"❌ Bot avec ID {bot_id} non trouvé dans Supabase")
        return

    webhook_token = bot['webhook_url'].split('/')[-1]
    full_webhook_url = f"{api_url.rstrip('/')}/api/v1/{bot['org_id']}/telegram/webhook/{webhook_token}"
    
    print(f"🔧 Webhook URL: {full_webhook_url}")
    
    async with httpx.AsyncClient() as client:
        r = await client.post(f"https://api.telegram.org/bot{token}/setWebhook", json={'url': full_webhook_url})
        print(f"✅ Résultat: {r.json()}")

asyncio.run(setup())
