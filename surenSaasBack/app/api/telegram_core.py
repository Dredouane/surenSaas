"""Core Telegram - Router générique et helpers API."""
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Dict, Any, Optional
import os
import re
import logging
import httpx

from app.api.auth import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram-webhooks"])


# ==================== ROUTER PRINCIPAL ====================

@router.post("/api/v1/{org_id}/telegram/webhook/{webhook_token}")
async def handle_telegram_webhook(
    org_id: str,
    webhook_token: str,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """Webhook principal pour tous les bots Telegram."""
    try:
        body = await request.json()
        logger.info(f"📨 Webhook Telegram reçu pour org_id: {org_id}")
        
        supabase = get_supabase()
        bot_result = supabase.table('telegram_bots') \
            .select('*') \
            .eq('org_id', org_id) \
            .like('webhook_url', f'%{webhook_token}%') \
            .eq('is_active', True) \
            .execute()
        
        if not bot_result.data:
            logger.warning(f"Bot non trouvé pour org_id: {org_id}")
            raise HTTPException(status_code=404, detail="Bot not found")
        
        bot_config = bot_result.data[0]
        
        # Vérifier secret token
        expected_secret = bot_config.get('webhook_secret')
        if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
            logger.warning("Token secret webhook invalide")
            raise HTTPException(status_code=403, detail="Invalid secret token")
        
        # Dispatcher selon le type de bot (extrait du bot_username)
        bot_username = bot_config.get('bot_username', '')
        bot_slug = _extract_bot_slug_from_username(bot_username)
        logger.info(f"🤖 Bot identifié: {bot_username} → slug: '{bot_slug}'")
        
        callback_query = body.get('callback_query')
        if callback_query:
            return await _dispatch_callback(callback_query, bot_config, supabase, org_id, bot_slug)
        
        message = body.get('message', {})
        if message:
            return await _dispatch_message(message, bot_config, supabase, org_id, bot_slug)
        
        return {"ok": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur traitement webhook: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


async def _dispatch_message(
    message: Dict[str, Any], 
    bot_config: Dict[str, Any], 
    supabase: Any,
    org_id: str,
    bot_slug: str
) -> Dict[str, Any]:
    """Dispatch les messages selon le bot."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    logger.info(f"📩 Message reçu de {chat_id} pour bot: {bot_slug}")
    
    # Dispatch vers le handler spécifique au bot
    if bot_slug == 'construction':
        from app.api.bot_construction import handle_construction_message
        return await handle_construction_message(message, bot_config, supabase, org_id)
    else:
        logger.warning(f"Bot non géré: {bot_slug}")
        await send_simple_message(chat_id, bot_config, "🤖 Bot en cours de configuration.")
        return {"ok": True}


async def _dispatch_callback(
    callback_query: Dict[str, Any],
    bot_config: Dict[str, Any],
    supabase: Any,
    org_id: str,
    bot_slug: str
) -> Dict[str, Any]:
    """Dispatch les callbacks selon le bot."""
    from app.api.bot_construction_commands import handle_construction_callback
    
    query_id = callback_query.get('id')
    from_user = callback_query.get('from', {})
    chat_id = from_user.get('id')
    data = callback_query.get('data', '')
    
    logger.info(f"🔘 Callback reçu: {data} pour bot: {bot_slug}")
    
    bot_token = get_bot_token(bot_config)
    if bot_token:
        await answer_callback(query_id, bot_token)
    
    # Dispatch vers le handler spécifique
    if bot_slug == 'construction':
        return await handle_construction_callback(callback_query, bot_config, supabase, org_id)
    else:
        logger.warning(f"Callback pour bot non géré: {bot_slug}")
        return {"ok": True}


@router.get("/api/v1/{org_id}/telegram/webhook/{webhook_token}/health")
async def webhook_health(org_id: str, webhook_token: str):
    """Health check."""
    return {"status": "ok", "org_id": org_id}


# ==================== HELPERS API TELEGRAM ====================

def get_bot_config_from_username(bot_username: str) -> Dict[str, str]:
    """Extrait la config depuis le username du bot.
    
    Format: suren_{bot_id}_{env}_bot
    Ex: suren_construction_test_bot → bot_id: CONSTRUCTION, env: TEST
    """
    env = os.getenv("ENVIRONMENT", "test").upper()
    
    match = re.match(r'suren_(.+?)_(test|prod)_bot', bot_username.lower())
    if not match:
        logger.error(f"Format bot_username invalide: {bot_username}")
        return {}
    
    bot_id = match.group(1).upper()
    prefix = f"SUREN_{env}_TELEGRAM_{bot_id}"
    
    return {
        'token': os.getenv(f"{prefix}_BOT_TOKEN"),
        'url': os.getenv(f"{prefix}_BOT_URL"),
        'username': os.getenv(f"{prefix}_BOT_USERNAME"),
        'bot_id': bot_id
    }


def get_bot_token(bot_config: Dict[str, Any]) -> Optional[str]:
    """Récupère le token depuis les variables d'environnement."""
    bot_username = bot_config.get('bot_username')
    if not bot_username:
        logger.error("bot_username non trouvé dans bot_config")
        return None
    
    config = get_bot_config_from_username(bot_username)
    token = config.get('token')
    
    if not token:
        logger.error(f"Token non trouvé pour {bot_username}")
    
    return token


async def send_simple_message(
    chat_id: int,
    bot_config: Dict[str, Any],
    text: str,
    parse_mode: str = "Markdown"
):
    """Envoie un message texte simple."""
    bot_token = get_bot_token(bot_config)
    if not bot_token:
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
            result = resp.json()
            if result.get('ok'):
                logger.debug(f"✅ Message envoyé à {chat_id}")
            else:
                logger.error(f"❌ Erreur envoi message: {result}")
    except Exception as e:
        logger.error(f"❌ Exception envoi message: {e}")


async def send_message_with_keyboard(
    chat_id: int,
    bot_config: Dict[str, Any],
    text: str,
    keyboard: Dict[str, Any],
    parse_mode: str = "Markdown"
):
    """Envoie un message avec clavier inline."""
    bot_token = get_bot_token(bot_config)
    if not bot_token:
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": keyboard
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
            result = resp.json()
            if result.get('ok'):
                logger.debug(f"✅ Message avec keyboard envoyé à {chat_id}")
            else:
                logger.error(f"❌ Erreur envoi keyboard: {result}")
    except Exception as e:
        logger.error(f"❌ Exception envoi keyboard: {e}")


async def answer_callback(query_id: str, bot_token: str):
    """Accuse réception d'un callback query."""
    if not bot_token:
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    payload = {"callback_query_id": query_id}
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception as e:
        logger.warning(f"Erreur answer callback: {e}")


def _extract_bot_slug_from_username(bot_username: str) -> str:
    """Extrait le slug du bot depuis le username.
    
    Format: suren_{slug}_{env}_bot
    Ex: suren_construction_test_bot → construction
    """
    if not bot_username:
        return ''
    
    match = re.match(r'suren_(.+?)_(test|prod)_bot', bot_username.lower())
    if match:
        return match.group(1)
    
    logger.warning(f"Format bot_username non reconnu: {bot_username}")
    return ''


def escape_markdown(text: str) -> str:
    """Échappe les caractères spéciaux Markdown de Telegram.
    
    Args:
        text: Texte à échapper
        
    Returns:
        Texte avec caractères échappés
    """
    if not text:
        return text
    
    # Caractères à échapper dans Markdown v2 de Telegram
    # Note: On utilise Markdown simple (pas v2), donc moins de caractères à échapper
    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text


def escape_html(text: str) -> str:
    """Échappe les caractères HTML.
    
    Args:
        text: Texte à échapper
        
    Returns:
        Texte avec caractères HTML échappés
    """
    if not text:
        return text
    
    html_escape_map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
    }
    for char, escaped in html_escape_map.items():
        text = text.replace(char, escaped)
    return text


async def send_message_safe(
    chat_id: int,
    bot_config: Dict[str, Any],
    text: str,
    keyboard: Optional[Dict[str, Any]] = None,
    log_prefix: str = ""
) -> Dict[str, Any]:
    """Envoie un message avec fallback Markdown → HTML → Texte brut.
    
    Args:
        chat_id: ID du chat Telegram
        bot_config: Configuration du bot
        text: Texte à envoyer
        keyboard: Clavier inline (optionnel)
        log_prefix: Préfixe pour les logs
        
    Returns:
        Résultat de l'envoi avec le mode utilisé
    """
    bot_token = get_bot_token(bot_config)
    if not bot_token:
        logger.error(f"{log_prefix}Token du bot non trouvé")
        return {'success': False, 'error': 'Token not found', 'mode': None}
    
    # Essai 1: Markdown (avec échappement préalable)
    try:
        result = await _send_message_with_mode(
            chat_id, bot_token, text, keyboard, 'Markdown'
        )
        if result.get('ok'):
            logger.info(f"{log_prefix}✅ Message envoyé avec succès (Markdown)")
            return {'success': True, 'mode': 'Markdown', 'message_id': result.get('result', {}).get('message_id')}
    except Exception as e:
        logger.warning(f"{log_prefix}⚠️ Échec Markdown: {e}")
    
    # Essai 2: Convertir en HTML
    try:
        html_text = _markdown_to_html(text)
        result = await _send_message_with_mode(
            chat_id, bot_token, html_text, keyboard, 'HTML'
        )
        if result.get('ok'):
            logger.info(f"{log_prefix}✅ Message envoyé avec succès (HTML fallback)")
            return {'success': True, 'mode': 'HTML', 'message_id': result.get('result', {}).get('message_id')}
    except Exception as e:
        logger.warning(f"{log_prefix}⚠️ Échec HTML: {e}")
    
    # Essai 3: Texte brut (sans formatage)
    try:
        plain_text = _strip_markdown(text)
        result = await _send_message_with_mode(
            chat_id, bot_token, plain_text, keyboard, None
        )
        if result.get('ok'):
            logger.info(f"{log_prefix}✅ Message envoyé avec succès (texte brut fallback)")
            return {'success': True, 'mode': 'Plain', 'message_id': result.get('result', {}).get('message_id')}
    except Exception as e:
        logger.error(f"{log_prefix}❌ Échec complet de l'envoi: {e}")
        return {'success': False, 'error': str(e), 'mode': None}


async def _send_message_with_mode(
    chat_id: int,
    bot_token: str,
    text: str,
    keyboard: Optional[Dict[str, Any]],
    parse_mode: Optional[str]
) -> Dict[str, Any]:
    """Envoie un message avec un mode de parsing spécifique."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    if keyboard:
        payload["reply_markup"] = keyboard
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30.0)
        return response.json()


def _markdown_to_html(text: str) -> str:
    """Convertit le formatage Markdown simple en HTML."""
    import re
    
    # Échapper d'abord le HTML
    text = escape_html(text)
    
    # Convertir **texte** ou *texte* en <b>texte</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<b>\1</b>', text)
    
    # Convertir _texte_ en <i>texte</i>
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    
    # Convertir `texte` en <code>texte</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    return text


def _strip_markdown(text: str) -> str:
    """Supprime le formatage Markdown pour obtenir du texte brut."""
    import re
    
    # Supprimer les balises Markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **gras**
    text = re.sub(r'\*(.+?)\*', r'\1', text)      # *gras*
    text = re.sub(r'_(.+?)_', r'\1', text)        # _italique_
    text = re.sub(r'`(.+?)`', r'\1', text)        # `code`
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1', text)  # [lien](url)
    
    return text
