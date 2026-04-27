from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

bots = supabase.table('telegram_bots').select('id, bot_id, bot_username, webhook_url, org_id').execute()
print(bots.data)
