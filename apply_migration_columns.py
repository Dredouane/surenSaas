from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

# Using Supabase RPC to run ALTER TABLE if available, 
# but as a fallback I will print the SQL needed.
# Since I cannot execute ALTER TABLE directly via the Supabase client,
# I will provide the SQL script to be executed in the Supabase SQL Editor.

print("--- EXÉCUTEZ CE SQL DANS VOTRE ÉDITEUR SQL SUPABASE ---")
print("""
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS last_state TEXT;
ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS last_state_data JSONB DEFAULT '{}';
""")
