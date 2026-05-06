from datetime import datetime


def parse_date(s: str) -> str:
    """Parse a date string and return ISO format (YYYY-MM-DD).

    Tries datetime.fromisoformat first; on ValueError falls back to
    strptime with the %d/%m/%Y format.

    Args:
        s: A date string in ISO format (e.g. "2024-03-15") or
           DD/MM/YYYY format (e.g. "15/03/2024").

    Returns:
        ISO date string (YYYY-MM-DD).

    Raises:
        ValueError: If neither format matches.
    """
    try:
        return datetime.fromisoformat(s).strftime("%Y-%m-%d")
    except ValueError:
        return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
