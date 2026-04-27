from app.api.auth import get_supabase
from dotenv import load_dotenv

load_dotenv('.env.test')
supabase = get_supabase()

bot = supabase.table('telegram_bots').select('bot_username').eq('bot_username', 'Arev_travaux_test_e2e_bot').single().execute().data
print(f"Bot username: {bot.get('bot_username')}")
