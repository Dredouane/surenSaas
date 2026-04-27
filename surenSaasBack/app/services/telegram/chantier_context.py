"""Chantier Context — gestion du chantier actif d'un utilisateur Telegram."""
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


async def get_active_chantier(
    telegram_id: int,
    supabase: Any,
    org_id: str,
) -> Optional[Dict[str, Any]]:
    """Retourne le chantier actif lié à un utilisateur Telegram, ou None."""
    try:
        result = (
            supabase.table("telegram_users")
            .select("last_chantier_id")
            .eq("telegram_id", telegram_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error(f"Erreur get_active_chantier (select telegram_users): {e}")
        return None

    if not result.data:
        return None
    if isinstance(result.data, list):
        if not result.data or not result.data[0].get("last_chantier_id"):
            return None
        chantier_id = result.data[0]["last_chantier_id"]
    else:
        if not result.data.get("last_chantier_id"):
            return None
        chantier_id = result.data["last_chantier_id"]

    try:
        c = (
            supabase.table("chantiers")
            .select("id, nom, ref, adresse, statut")
            .eq("id", chantier_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        )
        return c.data if c.data else None
    except Exception as e:
        logger.error(f"Erreur get_active_chantier (select chantiers): {e}")
        return None


async def set_active_chantier(
    telegram_id: int,
    chantier_id: str,
    supabase: Any,
    org_id: str,
) -> bool:
    """Persiste le chantier actif pour un utilisateur Telegram."""
    try:
        supabase.table("telegram_users").update(
            {"last_chantier_id": chantier_id, "last_activity_at": "now()"}
        ).eq("telegram_id", telegram_id).eq("org_id", org_id).execute()
        return True
    except Exception as e:
        logger.error(f"Erreur set_active_chantier: {e}")
        return False


async def list_accessible_chantiers(
    telegram_id: int,
    supabase: Any,
    org_id: str,
) -> List[Dict[str, Any]]:
    """Retourne les chantiers accessibles par l'utilisateur Telegram.
    
    Règle métier : tous les chantiers de l'organisation sont accessibles.
    """
    try:
        result = (
            supabase.table("chantiers")
            .select("id, nom, ref, adresse, statut, priorite, conducteur")
            .eq("org_id", org_id)
            .order("nom")
            .limit(50)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Erreur list_accessible_chantiers: {e}")
        return []


async def ensure_chantier_selected(
    telegram_id: int,
    supabase: Any,
    org_id: str,
) -> Optional[Dict[str, Any]]:
    """Vérifie qu'un chantier est sélectionné. Si un seul chantier accessible,
    le sélectionne automatiquement."""
    chantier = await get_active_chantier(telegram_id, supabase, org_id)
    if chantier:
        return chantier

    chantiers = await list_accessible_chantiers(telegram_id, supabase, org_id)
    if len(chantiers) == 1:
        await set_active_chantier(
            telegram_id, chantiers[0]["id"], supabase, org_id
        )
        return chantiers[0]

async def set_state(telegram_id: int, state: str, org_id: str, supabase: Any, data: Dict[str, Any] = None):
    """Stocke un état temporaire dans la table telegram_users."""
    try:
        payload = {"last_state": state, "last_state_data": data}
        logger.info(f"DEBUG: Setting state for {telegram_id}: {state} with data {data}")
        res = supabase.table("telegram_users").update(payload).eq("telegram_id", telegram_id).eq("org_id", org_id).execute()
        logger.info(f"DEBUG: set_state response: {res.data}")
        return True
    except Exception as e:
        logger.error(f"Erreur set_state: {e}")
        return False

async def get_state(telegram_id: int, supabase: Any, org_id: str) -> Optional[Dict[str, Any]]:
    """Récupère l'état courant."""
    try:
        r = supabase.table("telegram_users").select("last_state, last_state_data").eq("telegram_id", telegram_id).eq("org_id", org_id).single().execute()
        logger.info(f"DEBUG: get_state found: {r.data}")
        return r.data if r.data else None
    except Exception as e:
        logger.error(f"Erreur get_state: {e}")
        return None

