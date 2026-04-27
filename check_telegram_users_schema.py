from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

# Essayer de sélectionner last_chantier_id sur un utilisateur
try:
    res = supabase.table('telegram_users').select('last_chantier_id').limit(1).execute()
    print("Column exists!")
except Exception as e:
    print(f"Error: {e}")
