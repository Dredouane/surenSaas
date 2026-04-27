from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

# org_id used in the request
org_id = 'REDACTEDORG'
telegram_id = 5917823647

res = supabase.table('telegram_users').select('*').eq('telegram_id', telegram_id).eq('org_id', org_id).execute()
print(res.data)
