"""Routes API pour le webhook du bot Telegram Construction."""
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Dict, Any, Optional
import os

from app.api.auth import get_supabase
from app.core.logging import get_logger
from app.services.telegram.bots_registry import telegram_bots_registry
from app.services.telegram.construction_bot_service import ConstructionBotService

logger = get_logger(__name__)
router = APIRouter(prefix="/webhook/construction", tags=["telegram"])


@router.post("")
async def handle_construction_bot_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Webhook pour recevoir les updates du bot Telegram Construction.
    
    Cette route gère:
    - Les commandes /start (lien d'invitation)
    - L'upload de photos/PDF
    - La validation des factures extraites
    """
    try:
        # RÃ©cupÃ©rer le body de la requÃªte
        body = await request.json()
        
        # VÃ©rifier le token secret si configurÃ© (sÃ©curitÃ©)
        # Note: Telegram envoie ce header si configurÃ© lors du setWebhook
        environment = os.getenv("ENVIRONMENT", "test").lower()
        expected_secret = os.getenv(f"TELEGRAM_WEBHOOK_SECRET_{environment.upper()}")
        
        if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
            logger.warning("Token secret webhook invalide")
            raise HTTPException(status_code=403, detail="Invalid secret token")
        
        # Initialiser le service
        bot_service = ConstructionBotService()
        
        # Traiter l'update
        result = await bot_service.handle_update(body)
        
        return {"ok": True, "result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur traitement webhook Telegram: {e}")
        # Toujours retourner 200 Ã  Telegram pour Ã©viter les retries
        # mais logger l'erreur
        return {"ok": False, "error": str(e)}


@router.get("/health")
async def webhook_health_check():
    """Health check pour le webhook."""
    bot_config = telegram_bots_registry.get_bot('construction')
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "test"),
        "bot_username": bot_config.username if bot_config else None,
        "configured": bot_config is not None
    }
