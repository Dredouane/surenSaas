from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

# Chercher le bot qui a le username associé à suren_construction_test_bot
bot = supabase.table('telegram_bots').select('*').eq('bot_username', 'suren_construction_test_bot').single().execute().data
print(f"Bot GCP: {bot}")
