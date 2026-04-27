from app.api.auth import get_supabase
from dotenv import load_dotenv

load_dotenv('.env.test')
supabase = get_supabase()

# Set webhook_secret to None to bypass the X-Telegram-Bot-Api-Secret-Token check
result = supabase.table('telegram_bots').update({'webhook_secret': None}).eq('bot_username', 'Arev_travaux_test_e2e_bot').execute()
print(f"Update result: {result.data}")
