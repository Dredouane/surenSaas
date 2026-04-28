"""
Service database - Client Supabase.

Exporte supabase_client pour les services.
Ajoute un helper pour propager le X-Correlation-ID dans les en-têtes Supabase.
"""

from contextvars import ContextVar
from app.api.auth import get_supabase

# Client Supabase global
supabase_client = get_supabase()

# Variable de contexte pour le correlation_id courant
current_correlation_id: ContextVar[str] = ContextVar("current_correlation_id", default="")


def set_correlation_id(correlation_id: str) -> None:
    """Définit le correlation_id pour le contexte d'exécution courant."""
    current_correlation_id.set(correlation_id)


def get_correlation_id() -> str:
    """Retourne le correlation_id du contexte courant."""
    return current_correlation_id.get()
