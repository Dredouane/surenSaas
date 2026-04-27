"""
Client Gmail API avec OAuth2.

Gère l'authentification et les appels à l'API Gmail.
"""

import os
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GmailClient:
    """Client pour l'API Gmail."""
    
    def __init__(self, refresh_token: str):
        self.refresh_token = refresh_token
        self.credentials = None
        self.service = None
        
    async def _get_access_token(self) -> str:
        """Rafraîchit l'access token via le refresh token."""
        client_id = os.getenv("SUREN_GMAIL_OAUTH_CLIENT_ID")
        client_secret = os.getenv("SUREN_GMAIL_OAUTH_CLIENT_SECRET")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token"
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to refresh token: {error_text}")
                
                data = await response.json()
                return data["access_token"]
    
    async def connect(self):
        """Établit la connexion à l'API Gmail."""
        try:
            access_token = await self._get_access_token()
            
            self.credentials = Credentials(
                token=access_token,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("SUREN_GMAIL_OAUTH_CLIENT_ID"),
                client_secret=os.getenv("SUREN_GMAIL_OAUTH_CLIENT_SECRET")
            )
            
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail client connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Gmail API: {e}")
            
            # Vérifier si c'est une erreur de token invalide
            if "invalid_grant" in str(e) or "Token has been expired" in str(e):
                logger.error("Refresh token invalide ou expiré. Un nouveau token est nécessaire.")
                raise Exception(f"Refresh token invalide: {str(e)}")
            
            raise
    
    async def list_messages(
        self, 
        since_uid: Optional[int] = None,
        query: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Liste les messages Gmail.
        
        Args:
            since_uid: UID de départ pour la synchro incrémentale
            query: Requête de recherche Gmail (ex: "after:2024/01/01")
            max_results: Nombre max de résultats
            
        Returns:
            Liste des messages (id, threadId, historyId)
        """
        if not self.service:
            await self.connect()
        
        try:
            # Construction de la requête
            q = query or ""
            
            # Utiliser startHistoryId si since_uid fourni
            if since_uid:
                # Note: Gmail API utilise historyId, pas UID directement
                # On récupère les messages avec uid > since_uid
                pass
            
            results = self.service.users().messages().list(
                userId='me',
                q=q if q else None,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Retrieved {len(messages)} messages from Gmail")
            return messages
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
    
    async def list_messages_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Liste les messages par plage de dates (polling historique).
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            max_results: Nombre max de résultats
        """
        # Format de date pour Gmail: YYYY/MM/DD
        start_str = start_date.strftime("%Y/%m/%d")
        end_str = end_date.strftime("%Y/%m/%d")
        
        query = f"after:{start_str} before:{end_str}"
        
        return await self.list_messages(query=query, max_results=max_results)
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Récupère un message Gmail complet.
        
        Args:
            message_id: ID du message Gmail
            
        Returns:
            Dictionnaire avec tous les détails du message
        """
        if not self.service:
            await self.connect()
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'  # Récupère tout y compris les headers et le body
            ).execute()
            
            return message
            
        except HttpError as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            
            # Si c'est une erreur 401 (non authentifié), essayer de rafraîchir la connexion
            if e.status_code == 401:
                logger.info("Token expiré, tentative de reconnexion...")
                try:
                    # Recréer le service avec un nouveau token
                    await self.connect()
                    
                    # Réessayer la requête
                    message = self.service.users().messages().get(
                        userId='me',
                        id=message_id,
                        format='full'
                    ).execute()
                    
                    logger.info("Reconnexion réussie, message récupéré")
                    return message
                    
                except Exception as retry_error:
                    logger.error(f"Échec de reconnexion: {retry_error}")
            
            raise
    
    def parse_headers(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Extrait les headers du message en dict."""
        headers = message.get('payload', {}).get('headers', [])
        return {h['name']: h['value'] for h in headers}
    
    def get_body_text(self, message: Dict[str, Any]) -> str:
        """Extrait le corps texte du message."""
        parts = message.get('payload', {}).get('parts', [])
        
        # Fonction récursive pour collecter toutes les parties texte
        def collect_text_parts(parts_list, depth=0):
            text_parts = []
            html_parts = []
            
            for part in parts_list:
                mime_type = part.get('mimeType', '')
                data = part.get('body', {}).get('data', '')
                
                if data:
                    try:
                        content = base64.urlsafe_b64decode(data).decode('utf-8')
                        
                        if mime_type == 'text/plain':
                            text_parts.append(content)
                        elif mime_type == 'text/html':
                            html_parts.append(content)
                    except:
                        pass
                
                # Sous-parties
                if 'parts' in part and part['parts']:
                    sub_text, sub_html = collect_text_parts(part['parts'], depth + 1)
                    text_parts.extend(sub_text)
                    html_parts.extend(sub_html)
            
            return text_parts, html_parts
        
        # Collecter toutes les parties texte et HTML
        text_parts, html_parts = collect_text_parts(parts)
        
        # Vérifier si le texte brut contient des markers de forward
        def contains_forward_markers(text):
            import re
            forward_markers = [
                r'Forwarded message',
                r'Original Message',
                r'Begin forwarded message',
                r'De\s*:.*\n.*\nDate\s*:',
                r'From\s*:.*\n.*\nDate\s*:',
                r'Subject\s*:.*\n.*\nTo\s*:',
                r'Objet\s*:.*\n.*\nÀ\s*:',
            ]
            for marker in forward_markers:
                if re.search(marker, text, re.IGNORECASE):
                    return True
            return False
        
        # Priorité 1: texte brut qui contient des markers de forward
        if text_parts:
            # Prendre la partie texte la plus longue
            longest_text = max(text_parts, key=len)
            
            # Vérifier si c'est un forward
            if contains_forward_markers(longest_text):
                return longest_text
            
            # Si le texte est long mais ne contient pas de forward, c'est probablement juste une signature
            # Dans ce cas, essayer le HTML
            if len(longest_text.strip()) > 1000 and html_parts:
                # Le texte est long mais pas un forward, essayer le HTML
                pass
            elif len(longest_text.strip()) > 100:
                # Texte court mais valide
                return longest_text
        
        # Priorité 2: HTML converti en texte
        if html_parts:
            # Prendre la partie HTML la plus longue
            longest_html = max(html_parts, key=len)
            
            # Extraction améliorée de texte HTML
            import re
            
            # Supprimer d'abord les balises <style> et <script> avec leur contenu
            html_without_style_script = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', longest_html, flags=re.DOTALL | re.IGNORECASE)
            
            # Supprimer les commentaires HTML
            html_without_comments = re.sub(r'<!--.*?-->', ' ', html_without_style_script, flags=re.DOTALL)
            
            # Extraire le texte entre balises
            text = re.sub(r'<[^>]+>', ' ', html_without_comments)
            
            # Remplacer les entités HTML courantes
            replacements = {
                '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
                '&quot;': '"', '&apos;': "'", '&cent;': '¢', '&pound;': '£',
                '&yen;': '¥', '&euro;': '€', '&copy;': '©', '&reg;': '®',
                '&#160;': ' ', '&#38;': '&', '&#60;': '<', '&#62;': '>',
                '&#34;': '"', '&#39;': "'", '&#169;': '©', '&#174;': '®',
                '&#8211;': '-', '&#8212;': '--', '&#8216;': "'", '&#8217;': "'",
                '&#8220;': '"', '&#8221;': '"', '&#8230;': '...'
            }
            
            for entity, replacement in replacements.items():
                text = text.replace(entity, replacement)
            
            # Nettoyer les espaces multiples
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            if text:
                return text
        
        # Fallback: chercher dans le body direct
        body = message.get('payload', {}).get('body', {})
        data = body.get('data', '')
        if data:
            try:
                return base64.urlsafe_b64decode(data).decode('utf-8')
            except:
                return ""
        
        return ""
    
    def get_attachments(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Liste les pièces jointes du message."""
        attachments = []
        parts = message.get('payload', {}).get('parts', [])
        
        for part in parts:
            if part.get('filename'):
                attachments.append({
                    'filename': part['filename'],
                    'mimeType': part.get('mimeType'),
                    'attachmentId': part.get('body', {}).get('attachmentId'),
                    'size': part.get('body', {}).get('size')
                })
        
        return attachments
    
    async def download_attachment(
        self, 
        message_id: str, 
        attachment_id: str
    ) -> bytes:
        """
        Télécharge une pièce jointe.
        
        Args:
            message_id: ID du message
            attachment_id: ID de la pièce jointe
            
        Returns:
            Contenu binaire de la pièce jointe
        """
        if not self.service:
            await self.connect()
        
        attachment = self.service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()
        
        data = attachment.get('data', '')
        return base64.urlsafe_b64decode(data)


# Factory pour créer des clients
def create_gmail_client(refresh_token: str) -> GmailClient:
    """Crée un client Gmail avec le refresh token fourni."""
    return GmailClient(refresh_token=refresh_token)
