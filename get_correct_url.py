from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

bot = supabase.table('telegram_bots').select('org_id, webhook_url').eq('bot_id', 8684895317).single().execute().data
print(f"Correct URL: {bot.get('webhook_url')}")
