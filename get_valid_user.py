from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

user = supabase.table('users').select('id, email').eq('org_id', 'REDACTEDORG').limit(1).execute()
print(user.data)
