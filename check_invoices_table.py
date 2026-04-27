from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

# Essayer de récupérer une facture sans jointure
try:
    res = supabase.table('invoices').select('id, created_by').limit(1).execute()
    print(f"Columns: {res.data[0].keys() if res.data else 'No data'}")
except Exception as e:
    print(f"Error: {e}")
