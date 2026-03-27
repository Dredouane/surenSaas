from fastapi import Request, HTTPException
from functools import wraps
import time
from typing import Dict, List
import hashlib

# Stockage en mémoire pour rate limiting
# Structure: {key: [timestamps]}
_memory_store: Dict[str, List[float]] = {}

def _get_client_identifier(request: Request) -> str:
    """Génère un identifiant unique basé sur IP + User-Agent hashé."""
    ip = request.client.host if request.client else 'unknown'
    user_agent = request.headers.get('user-agent', '')
    
    # Combiner IP + User-Agent pour éviter les collisions sur réseaux partagés
    identifier = f"{ip}:{user_agent}"
    return hashlib.md5(identifier.encode()).hexdigest()[:16]

def rate_limit(max_requests: int = 5, window: int = 60):
    """
    Rate limiting en mémoire par client.
    
    Args:
        max_requests: Nombre max de requêtes
        window: Fenêtre de temps en secondes
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_id = _get_client_identifier(request)
            endpoint = func.__name__
            key = f"ratelimit:{endpoint}:{client_id}"
            
            now = time.time()
            
            # Initialiser si première requête
            if key not in _memory_store:
                _memory_store[key] = []
            
            # Nettoyer les anciennes entrées
            _memory_store[key] = [
                ts for ts in _memory_store[key] 
                if now - ts < window
            ]
            
            # Vérifier limite
            if len(_memory_store[key]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Trop de tentatives. Réessayez dans {window} secondes."
                )
            
            # Ajouter timestamp actuel
            _memory_store[key].append(now)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Nettoyage périodique (optionnel - pour éviter fuite mémoire)
def cleanup_rate_limit_store(max_age: int = 3600):
    """Nettoie les entrées trop anciennes."""
    now = time.time()
    keys_to_remove = []
    
    for key, timestamps in _memory_store.items():
        # Garder seulement les entrées récentes
        _memory_store[key] = [ts for ts in timestamps if now - ts < max_age]
        
        if not _memory_store[key]:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del _memory_store[key]
