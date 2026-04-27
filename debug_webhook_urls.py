from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()
bots = supabase.table('telegram_bots').select('webhook_url, bot_id').execute()
for b in bots.data:
    print(f"Bot ID: {b['bot_id']}, URL: {b['webhook_url']}")
