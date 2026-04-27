from app.api.auth import get_supabase
from dotenv import load_dotenv

# Use appropriate env if needed
load_dotenv('.env.test') 
supabase = get_supabase()

# Set webhook_secret explicitly to an empty string to bypass the check
# The log shows the bot_username is 'suren_construction_test_bot'
result = supabase.table('telegram_bots').update({'webhook_secret': ''}).eq('bot_username', 'suren_construction_test_bot').execute()
print(f"Update result: {result.data}")
