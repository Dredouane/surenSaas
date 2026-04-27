import os
from app.api.auth import get_supabase
from dotenv import load_dotenv

load_dotenv('.env.test')
supabase = get_supabase()

# Set webhook_secret to NULL (or an empty string if that's what the code expects for bypass)
result = supabase.table('telegram_bots').update({'webhook_secret': None}).eq('bot_username', 'suren_construction_test_bot').execute()
print(f"Update result: {result.data}")
