import os
from app.api.auth import get_supabase
from dotenv import load_dotenv

load_dotenv('.env.test')
supabase = get_supabase()

bots = supabase.table('telegram_bots').select('*').execute()
print(bots.data)
