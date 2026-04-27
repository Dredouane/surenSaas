from app.api.auth import get_supabase
from dotenv import load_dotenv
load_dotenv('.env.test')
supabase = get_supabase()

# Exécution de la commande SQL pour ajouter la colonne
# On utilise la fonction rpc si elle existe ou une requête brute via un client de maintenance
# Mais en Supabase client standard, on ne peut pas faire ALTER TABLE.
# Je vais tenter une approche via Supabase RPC si vous en avez, 
# sinon je vais vous demander de lancer ce SQL manuellement dans l'éditeur SQL de Supabase.

print("Veuillez lancer ceci dans votre éditeur SQL Supabase:")
print("ALTER TABLE telegram_users ADD COLUMN last_chantier_id UUID REFERENCES chantiers(id) ON DELETE SET NULL;")
