"""Parsing de dates pour le bot pointages."""
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


def parse_pointage_date(date_str: str) -> str:
    """
    Parse une date depuis ISO (2026-04-27) ou européen (27/04/2026).
    Retourne toujours au format ISO (YYYY-MM-DD).
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError(f"Date invalide: {date_str!r}")

    # Essayer ISO d'abord (YYYY-MM-DD)
    try:
        d = date.fromisoformat(date_str)
        logger.debug("[PARSE_DATE] ISO ok: %s → %s", date_str, d.isoformat())
        return d.isoformat()
    except (ValueError, TypeError):
        pass

    # Essayer européen (DD/MM/YYYY)
    try:
        d = datetime.strptime(date_str, "%d/%m/%Y").date()
        logger.debug("[PARSE_DATE] EU ok: %s → %s", date_str, d.isoformat())
        return d.isoformat()
    except (ValueError, TypeError):
        pass

    raise ValueError(
        f"Format de date non reconnu: {date_str!r}. "
        "Formats acceptés: YYYY-MM-DD ou DD/MM/YYYY"
    )
