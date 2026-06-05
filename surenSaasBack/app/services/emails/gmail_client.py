"""
Client Gmail IMAP avec mot de passe d'application.

Remplace l'ancien client OAuth2 par IMAP direct.
Utilise SUREN_GMAIL_RECEPTION_IMAP_ADRESS et SUREN_GMAIL_RECEPTION_IMAP_MDP.
"""

import os
import imaplib
import email
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from email.header import decode_header, make_header
from email.mime.base import MIMEBase
from uuid import uuid4

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _decode_header_value(value) -> str:
    """Décode un header email encodé en string lisible."""
    if value is None:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (UnicodeDecodeError, LookupError):
        return str(value).encode('ascii', errors='replace').decode('ascii')


class GmailClient:
    """Client IMAP pour Gmail avec mot de passe d'application."""

    def __init__(self, email_address: str, app_password: str):
        self.email_address = email_address
        self.app_password = app_password
        self._imap = None

    async def connect(self):
        """Établit la connexion IMAP."""
        try:
            self._imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            self._imap.login(self.email_address, self.app_password)
            logger.info("IMAP Gmail connecté")
        except imaplib.IMAP4.error as e:
            logger.error(f"Échec connexion IMAP: {e}")
            raise

    def _ensure_connected(self):
        """Vérifie que la connexion IMAP est active."""
        if self._imap is None:
            raise RuntimeError("IMAP non connecté. Appelez connect() d'abord.")

    def _extract_header(self, msg: email.message.Message, name: str) -> str:
        """Extrait et décode un header."""
        raw = msg.get(name, "")
        if isinstance(raw, str):
            return raw
        return _decode_header_value(raw)

    def _get_body_text(self, msg: email.message.Message) -> str:
        """Extrait le corps texte d'un message email.Message (synchrone)."""
        text_parts = []
        html_parts = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                try:
                    charset = part.get_content_charset() or "utf-8"
                    decoded = payload.decode(charset, errors="replace")
                    if content_type == "text/plain":
                        text_parts.append(decoded)
                    elif content_type == "text/html":
                        html_parts.append(decoded)
                except (UnicodeDecodeError, LookupError):
                    continue
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    charset = msg.get_content_charset() or "utf-8"
                    decoded = payload.decode(charset, errors="replace")
                    content_type = msg.get_content_type()
                    if content_type == "text/plain":
                        text_parts.append(decoded)
                    elif content_type == "text/html":
                        html_parts.append(decoded)
                except (UnicodeDecodeError, LookupError):
                    pass

        # Priorité texte brut
        if text_parts:
            longest = max(text_parts, key=len)
            if len(longest.strip()) > 50:
                return longest

        # Fallback HTML → texte
        if html_parts:
            longest_html = max(html_parts, key=len)
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', longest_html, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r'<!--.*?-->', ' ', clean, flags=re.DOTALL)
            clean = re.sub(r'<[^>]+>', ' ', clean)
            clean = re.sub(r'&[a-zA-Z]+;|&#[0-9]+;', ' ', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()
            return clean

        return ""

    def _msg_to_gmail_dict(self, uid: int, msg: email.message.Message) -> Dict[str, Any]:
        """Convertit un email.message.Message en dict compatible API Gmail."""
        msg_id = uid
        thread_id = self._extract_header(msg, "Message-ID") or self._extract_header(msg, "References") or f"thread-{uuid4()}"

        # Construire un dict simulant la structure Gmail API
        return {
            "id": str(msg_id),
            "threadId": thread_id.replace("<", "").replace(">", "").strip(),
            "historyId": int(datetime.utcnow().timestamp()),
            "sizeEstimate": len(msg.as_bytes()),
            "internalDate": str(int(datetime.utcnow().timestamp() * 1000)),
            "payload": {
                "headers": [
                    {"name": "Subject", "value": self._extract_header(msg, "Subject")},
                    {"name": "From", "value": self._extract_header(msg, "From")},
                    {"name": "To", "value": self._extract_header(msg, "To")},
                    {"name": "Date", "value": self._extract_header(msg, "Date")},
                    {"name": "Delivered-To", "value": self._extract_header(msg, "Delivered-To")},
                    {"name": "In-Reply-To", "value": self._extract_header(msg, "In-Reply-To")},
                    {"name": "References", "value": self._extract_header(msg, "References")},
                    {"name": "Message-ID", "value": self._extract_header(msg, "Message-ID")},
                ],
                "parts": [],
                "body": {"data": ""},
                "mimeType": msg.get_content_type(),
            },
            "attachments": self._extract_attachments(msg),
            "_raw_msg": msg,
        }

    def _extract_attachments(self, msg: email.message.Message) -> List[Dict[str, Any]]:
        """Extrait la liste des pièces jointes d'un message."""
        attachments = []
        if not msg.is_multipart():
            return attachments

        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                decoded_name = _decode_header_value(filename)
                attachments.append({
                    "filename": decoded_name,
                    "mimeType": part.get_content_type(),
                    "attachmentId": str(uuid4()),
                    "size": len(part.get_payload(decode=True) or b""),
                })
        return attachments

    async def list_messages(
        self,
        since_uid: Optional[int] = None,
        query: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Liste les messages depuis la boîte de réception.

        Retourne les messages les PLUS ANCIENS en premier (ceux pas encore traités).
        Le sync_service utilise le last_uid pour avancer progressivement.
        """
        self._ensure_connected()

        try:
            self._imap.select("INBOX", readonly=True)

            search_criteria = "ALL"
            if query and isinstance(query, str) and query.strip():
                search_criteria = query

            status, data = self._imap.search(None, search_criteria)
            if status != "OK" or not data[0]:
                return []

            all_uids = data[0].split()

            # Si since_uid fourni, ne prendre que les UIDs plus grands
            uids_to_process = []
            if since_uid:
                for uid_str in all_uids:
                    if int(uid_str) > since_uid:
                        uids_to_process.append(uid_str)
            else:
                uids_to_process = all_uids

            total_remaining = len(uids_to_process)

            # Prendre les PLUS ANCIENS en priorité (début de la liste)
            batch = uids_to_process[:max_results]

            logger.info(f"IMAP: {len(batch)} messages sur {total_remaining} restants (since_uid={since_uid})")

            messages = []
            for uid_str in batch:
                status, msg_data = self._imap.fetch(uid_str, "(RFC822)")
                if status != "OK":
                    continue
                raw_email = msg_data[0][1]
                parsed = email.message_from_bytes(raw_email)
                uid_int = int(uid_str)
                msg_dict = self._msg_to_gmail_dict(uid_int, parsed)
                msg_dict["_has_more"] = total_remaining > max_results
                msg_dict["_total_remaining"] = total_remaining
                messages.append(msg_dict)

            # Ajouter les métadonnées de pagination au premier élément
            if messages:
                messages[0]["_batch_info"] = {
                    "batch_size": len(batch),
                    "total_remaining": total_remaining,
                    "has_more": total_remaining > max_results,
                    "oldest_uid": int(batch[0]),
                    "newest_uid": int(batch[-1]) if batch else None,
                }

            return messages

        except imaplib.IMAP4.error as e:
            logger.error(f"Erreur IMAP list_messages: {e}")
            raise

    async def list_messages_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Liste les messages par plage de dates via IMAP."""
        start_str = start_date.strftime("%d-%b-%Y")
        end_str = end_date.strftime("%d-%b-%Y")
        query = f"SINCE {start_str} BEFORE {end_str}"
        return await self.list_messages(query=query, max_results=max_results)

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Récupère un message complet par son UID."""
        self._ensure_connected()
        try:
            self._imap.select("INBOX", readonly=True)
            status, msg_data = self._imap.fetch(message_id, "(RFC822)")
            if status != "OK":
                raise RuntimeError(f"Message {message_id} introuvable")

            raw_email = msg_data[0][1]
            parsed = email.message_from_bytes(raw_email)
            return self._msg_to_gmail_dict(int(message_id), parsed)

        except imaplib.IMAP4.error as e:
            logger.error(f"Erreur IMAP get_message {message_id}: {e}")
            raise

    def parse_headers(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Extrait les headers du dict retourné."""
        headers = message.get("payload", {}).get("headers", [])
        return {h["name"]: h["value"] for h in headers}

    def get_body_text(self, message: Dict[str, Any]) -> str:
        """Extrait le corps texte du message depuis le dict retourné."""
        raw_msg = message.get("_raw_msg")
        if raw_msg:
            return self._get_body_text(raw_msg)
        # Fallback : récupérer depuis les parts du dict
        parts = message.get("payload", {}).get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    import base64
                    try:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    except Exception:
                        pass
        return ""

    def get_attachments(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Liste les pièces jointes."""
        return message.get("attachments", [])

    async def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Télécharge une pièce jointe depuis un message IMAP."""
        self._ensure_connected()
        try:
            self._imap.select("INBOX", readonly=True)
            status, msg_data = self._imap.fetch(message_id, "(RFC822)")
            if status != "OK":
                raise RuntimeError(f"Message {message_id} introuvable")

            raw_email = msg_data[0][1]
            parsed = email.message_from_bytes(raw_email)

            for part in parsed.walk():
                if part.get_filename():
                    att_id = str(uuid4())  # On ne peut pas matcher par ID, on prend la première
                    if attachment_id == att_id:
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload
                        break
            # Fallback : retourner la première pièce jointe
            for part in parsed.walk():
                if part.get_filename():
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload
                    break

            raise RuntimeError(f"Pièce jointe {attachment_id} introuvable dans le message {message_id}")

        except imaplib.IMAP4.error as e:
            logger.error(f"Erreur IMAP download_attachment: {e}")
            raise

    async def download_raw_email(self, message_id: str) -> Optional[bytes]:
        """Télécharge le .eml brut d'un message via IMAP, retourne les bytes RFC822."""
        self._ensure_connected()
        try:
            self._imap.select("INBOX", readonly=True)
            status, msg_data = self._imap.fetch(message_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                logger.warning(f"Message {message_id} introuvable pour le téléchargement raw")
                return None
            raw_bytes = msg_data[0][1]
            if isinstance(raw_bytes, str):
                raw_bytes = raw_bytes.encode("utf-8", errors="replace")
            return raw_bytes
        except imaplib.IMAP4.error as e:
            logger.error(f"Erreur IMAP download_raw_email {message_id}: {e}")
            return None


# Factory
def create_gmail_client(refresh_token: str) -> GmailClient:
    """Crée un client Gmail IMAP depuis les variables d'env."""
    email_address = os.getenv("SUREN_GMAIL_RECEPTION_IMAP_ADRESS", "REDACTED_EMAIL")
    app_password = os.getenv("SUREN_GMAIL_RECEPTION_IMAP_MDP", "")
    if not app_password:
        raise RuntimeError("SUREN_GMAIL_RECEPTION_IMAP_MDP non définie")
    return GmailClient(email_address=email_address, app_password=app_password)
