
from app.api.auth import get_supabase
from app.services.telegram.audit_service import TelegramAuditService
from app.services.telegram.bot_manager import BotManagerService
from app.services.telegram.webhook_handler import WebhookHandlerService
from app.services.telegram.upload_invoice.service import InvoiceUploadService
from app.services.telegram.notification_service import NotificationService

def get_webhook_handler(bot_token: str = None) -> WebhookHandlerService:
    """Initialise et retourne le WebhookHandlerService avec ses dépendances."""
    supabase = get_supabase()
    audit = TelegramAuditService(supabase)
    bot_manager = BotManagerService(supabase)
    
    # Notification service peut avoir besoin du token
    notification_service = NotificationService(supabase, bot_token)
    
    upload_service = InvoiceUploadService(
        supabase_client=supabase, 
        audit_service=audit, 
        notification_service=notification_service
    )
    
    return WebhookHandlerService(
        supabase_client=supabase,
        audit_service=audit,
        bot_manager=bot_manager,
        upload_invoice_service=upload_service
    )
