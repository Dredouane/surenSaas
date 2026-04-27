from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

# Vérifier si l'utilisateur Telegram est bien lié à un user_id
user_id = '5917823647' # ID Telegram trouvé dans les logs précédents
res = supabase.table('telegram_users').select('user_id').eq('telegram_id', user_id).single().execute()
print(f"User ID lié: {res.data}")
