from app.api.auth import get_supabase
from dotenv import load_dotenv

load_dotenv('.env.test')
supabase = get_supabase()

bot = supabase.table('telegram_bots').select('bot_username, webhook_secret').eq('bot_username', 'Arev_travaux_test_e2e_bot').single().execute()
print(f"Bot info: {bot.data}")
