from app.api.auth import get_supabase
from dotenv import load_dotenv

load_dotenv('.env.test')
supabase = get_supabase()

# Select all bots
bots = supabase.table('telegram_bots').select('id, bot_username, webhook_secret, bot_id').execute()
for b in bots.data:
    print(f"Bot: {b['bot_username']} (ID: {b['bot_id']}), Secret: '{b['webhook_secret']}'")
