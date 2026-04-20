"""
Service database - Client Supabase.

Exporte supabase_client pour les services.
"""

from app.api.auth import get_supabase

# Client Supabase global
supabase_client = get_supabase()
