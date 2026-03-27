"""Bot Construction - Commandes et callbacks."""
from typing import Dict, Any
import re
import logging

from app.api.telegram_core import send_simple_message, send_message_with_keyboard

logger = logging.getLogger(__name__)


async def handle_construction_callback(
    callback_query: Dict[str, Any],
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str
) -> Dict[str, Any]:
    """Gère les callbacks pour le bot construction."""
    from app.api.bot_construction import handle_invoice_validation, handle_invoice_cancellation
    
    from_user = callback_query.get('from', {})
    chat_id = from_user.get('id')
    data = callback_query.get('data', '')
    
    logger.info(f"🔘 Callback construction reçu: {data}")
    
    # Dispatcher les callbacks
    if data.startswith('invoice:validate:'):
        invoice_id = data.split(':')[2]
        return await handle_invoice_validation(chat_id, invoice_id, bot_config, supabase, org_id)
    elif data.startswith('invoice:cancel:'):
        invoice_id = data.split(':')[2]
        return await handle_invoice_cancellation(chat_id, invoice_id, bot_config, supabase, org_id)
    elif data.startswith('invoice:edit:'):
        await send_simple_message(
            chat_id, bot_config,
            "✏️ *Modifier la facture*\n\nCette fonctionnalité sera disponible prochainement."
        )
        return {"ok": True}
    else:
        return await handle_service_callback(chat_id, data, bot_config)


async def handle_start_command(
    message: Dict[str, Any],
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str
) -> Dict[str, Any]:
    """Gère la commande /start avec user_id."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    from_user = message.get('from', {})
    
    parts = text.split(' ', 1)
    if len(parts) < 2:
        logger.warning(f"User ID manquant dans /start de {chat_id}")
        await send_simple_message(
            chat_id, bot_config,
            "👋 Bienvenue !\n\nVeuillez utiliser un lien d'invitation valide.\n"
            "Contactez votre administrateur."
        )
        return {"ok": True}
    
    user_id = parts[1].strip()
    logger.info(f"🔗 User ID reçu: {user_id}")
    
    # Validation UUID
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', user_id.lower()):
        logger.error(f"Format user_id invalide: {user_id}")
        await send_simple_message(chat_id, bot_config, "❌ Lien d'invitation invalide.")
        return {"ok": True}
    
    # Récupérer infos utilisateur
    user_result = supabase.table('users') \
        .select('email, full_name') \
        .eq('id', user_id) \
        .eq('org_id', org_id) \
        .execute()
    
    if not user_result.data:
        logger.error(f"User {user_id} non trouvé")
        await send_simple_message(chat_id, bot_config, "❌ Utilisateur non trouvé.")
        return {"ok": True}
    
    user_info = user_result.data[0]
    first_name = from_user.get('first_name', user_info.get('full_name', 'Utilisateur'))
    
    # Lier compte Telegram
    telegram_id = from_user.get('id')
    username = from_user.get('username')
    
    try:
        existing = supabase.table('telegram_users') \
            .select('*') \
            .eq('telegram_id', telegram_id) \
            .eq('org_id', org_id) \
            .execute()
        
        if not existing.data:
            supabase.table('telegram_users').insert({
                'org_id': org_id,
                'user_id': user_id,
                'telegram_id': telegram_id,
                'telegram_username': username,
                'telegram_first_name': from_user.get('first_name'),
                'telegram_last_name': from_user.get('last_name'),
                'is_verified': True,
                'notification_enabled': True,
                'started_at': 'now()',
                'last_activity_at': 'now()'
            }).execute()
            logger.info(f"✅ Compte Telegram lié à l'utilisateur {user_id}")
        else:
            supabase.table('telegram_users') \
                .update({'last_activity_at': 'now()'}) \
                .eq('telegram_id', telegram_id) \
                .execute()
    except Exception as e:
        logger.error(f"Erreur liaison compte: {e}")
    
    await _send_welcome_message(chat_id, first_name, bot_config)
    return {"ok": True}


async def handle_service_callback(chat_id: int, data: str, bot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Gère les callbacks de service."""
    if data == 'service:invoice_upload':
        await send_simple_message(
            chat_id, bot_config,
            "📄 *Envoyer une facture*\n\n"
            "Envoyez une photo ou un PDF de votre facture.\n"
            "Je vais l'analyser automatiquement."
        )
        return {"ok": True}
    
    elif data == 'menu:help':
        await send_simple_message(
            chat_id, bot_config,
            "❓ *Aide*\n\n"
            "• /start - Afficher le menu\n"
            "• Envoyer une photo/PDF - Analyser une facture\n\n"
            "Besoin d'aide ? Contactez votre administrateur."
        )
        return {"ok": True}
    
    return {"ok": True}


async def send_menu_message(chat_id: int, bot_config: Dict[str, Any]):
    """Affiche le menu principal."""
    text = "📋 *Menu principal*\n\nQue souhaitez-vous faire ?"
    keyboard = {
        "inline_keyboard": [
            [{"text": "📄 Envoyer Facture", "callback_data": "service:invoice_upload"}],
            [{"text": "❓ Aide", "callback_data": "menu:help"}]
        ]
    }
    await send_message_with_keyboard(chat_id, bot_config, text, keyboard)


async def _send_welcome_message(chat_id: int, first_name: str, bot_config: Dict[str, Any]):
    """Envoie le message de bienvenue."""
    welcome_text = (
        f"👋 *Bienvenue {first_name} !*\n\n"
        f"Vous êtes connecté au *Bot Construction*.\n\n"
        f"📋 *Services disponibles :*"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📄 Envoyer Facture", "callback_data": "service:invoice_upload"}],
            [{"text": "❓ Aide", "callback_data": "menu:help"}]
        ]
    }
    
    await send_message_with_keyboard(chat_id, bot_config, welcome_text, keyboard)
