"""
Parse un fichier .eml brut et extrait tous les emails d'une chaîne de forwards.

Gère:
- Messages multipart
- Forwards attachés (message/rfc822)
- Forwards inline dans le body (De:, From:, etc.)
- Chaînes imbriquées de forwards
"""

import email
import re
import tempfile
from email import policy
from email.parser import BytesParser
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_email_chain(raw_eml: bytes) -> List[Dict[str, Any]]:
    """
    Parse un fichier .eml brut et extrait tous les emails d'une chaîne.

    Args:
        raw_eml: Contenu brut du fichier .eml

    Returns:
        Liste d'emails structurés, du plus récent au plus ancien
    """
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw_eml)
    except Exception as e:
        logger.error(f"Erreur parsing .eml: {e}")
        return []

    chain = []

    # 1. Extraire l'email principal (le plus récent)
    chain.append(extract_email_data(msg))

    # 2. Chercher les messages attachés (forward as attachment)
    _extract_attached_messages(msg, chain)

    # 3. Chercher dans le body texte les séparateurs de forward inline
    body_text = get_body_text(msg)
    if body_text:
        inline_emails = _extract_inline_forwards(body_text)
        chain.extend(inline_emails)

    # Dédupliquer par message_id
    seen_ids = set()
    unique_chain = []
    for email_data in chain:
        msg_id = email_data.get("message_id", "")
        if msg_id and msg_id in seen_ids:
            continue
        if msg_id:
            seen_ids.add(msg_id)
        unique_chain.append(email_data)

    logger.info(f"✅ .eml parsé: {len(unique_chain)} emails extraits de la chaîne")
    return unique_chain


def extract_email_data(msg) -> Dict[str, Any]:
    """Extrait les données structurées d'un message email."""
    return {
        "message_id": _clean_msg_id(msg.get("Message-ID", "")),
        "from_email": _parse_address_email(msg.get("From", "")),
        "from_name": _parse_address_name(msg.get("From", "")),
        "to_emails": _parse_addresses(msg.get("To", "")),
        "cc_emails": _parse_addresses(msg.get("Cc", "")),
        "bcc_emails": _parse_addresses(msg.get("Bcc", "")),
        "date": _parse_date(msg.get("Date", "")),
        "subject": msg.get("Subject", ""),
        "body_text": get_body_text(msg),
        "body_html": get_body_html(msg),
        "in_reply_to": _clean_msg_id(msg.get("In-Reply-To", "")),
        "references": _parse_references(msg.get("References", "")),
    }


def get_body_text(msg) -> str:
    """Extrait le body text/plain préférentiellement."""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_content()
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    return _strip_html(part.get_content())
        else:
            return msg.get_content()
    except Exception:
        pass
    return ""


def get_body_html(msg) -> str:
    """Extrait le body text/html."""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    return part.get_content()
        else:
            content = msg.get_content()
            if msg.get_content_type() == "text/html":
                return content
    except Exception:
        pass
    return ""


def _extract_attached_messages(msg, chain: List[Dict[str, Any]]):
    """Cherche les messages attachés (message/rfc822) récursivement."""
    for part in msg.walk():
        try:
            if part.get_content_type() == "message/rfc822":
                embedded = part.get_payload(0)
                if embedded:
                    chain.append(extract_email_data(embedded))
                    _extract_attached_messages(embedded, chain)
        except Exception as e:
            logger.debug(f"Erreur extraction message attaché: {e}")


def _extract_inline_forwards(body: str) -> List[Dict[str, Any]]:
    """
    Détecte et extrait les forwards inline dans le body texte.

    Patterns reconnus:
    - ----- Original Message ----- (avec séparateur)
    - De : ... Envoyé : ... À : ... Objet : ... (sans séparateur, par blocs)
    - From : ... Date : ... To : ... Subject : ... (sans séparateur, par blocs)
    """
    emails = []

    # 1. Essayer d'abord les séparateurs connus
    separators = [
        (r"-----+\s*Original Message\s*-----+", "original"),
        (r"-----+\s*Message transmis\s*-----+", "transmis"),
        (r"_{10,}\s*Original Message\s*_{10,}", "underscore"),
        (r"Begin forwarded message:", "begin_fwd"),
        (r"---+\s*Forwarded message\s*---+\s*", "forwarded"),
    ]

    remaining = body

    for pattern, name in separators:
        parts = re.split(pattern, remaining, maxsplit=1, flags=re.IGNORECASE | re.MULTILINE)
        if len(parts) > 1:
            remaining = parts[0]
            forwarded_content = parts[1]

            email_data = _parse_inline_headers(forwarded_content)
            if email_data:
                emails.append(email_data)

    # 2. Fallback: détecter les blocs De:/From: sans séparateur
    #    On cherche le dernier bloc De:/From: dans le body (le plus ancien forward)
    #    puis on remonte la chaîne
    if not emails:
        emails = _extract_de_from_blocks(body)

    return emails


def _extract_de_from_blocks(body: str) -> List[Dict[str, Any]]:
    """
    Extrait les forwards inline qui commencent par De: ou From: sans séparateur explicite.

    Découpe le body en blocs à chaque occurrence de 'De :' ou 'From :' en début de ligne,
    puis parse chaque bloc.
    """
    lines = body.split("\n")

    blocks = []
    current_block = []
    in_block = False

    for line in lines:
        if re.match(r"^\s*(De|From)\s*:", line, re.IGNORECASE):
            if current_block:
                blocks.append("\n".join(current_block))
            current_block = [line]
            in_block = True
        elif in_block:
            current_block.append(line)

    if current_block:
        blocks.append("\n".join(current_block))

    emails = []
    for block_text in blocks:
        # Un vrai forward inline a au moins 2 headers reconnus
        # (De: + Envoyé:/Date: ou De: + Objet:/Subject:)
        header_count = len(re.findall(
            r"^(?:From|De|To|À|Date|Envoyé|Subject|Objet|Cc)\s*:",
            block_text, re.IGNORECASE | re.MULTILINE
        ))
        if header_count < 2:
            continue

        # Vérifier que le bloc contient bien un email dans le De:
        has_email = bool(re.search(r"@", block_text[:200]))
        if not has_email:
            continue

        email_data = _parse_inline_headers(block_text)
        if email_data and email_data.get("from_email"):
            emails.append(email_data)

    return emails


def _normalize_header(line: str) -> str:
    """
    Nettoie et traduit une ligne de header pour le parser RFC 5322.

    1. Supprime l'espace avant ':' (ex: 'De :' → 'De:')
    2. Traduit les noms français → anglais
    """
    stripped = line.strip()
    header_map = {
        "De": "From",
        "Objet": "Subject",
        "Envoyé": "Date",
        "À": "To",
    }
    m = re.match(r"^(\w[\w\xc0-\xff]*)\s*:", stripped)
    if m:
        name = m.group(1)
        translated = header_map.get(name, header_map.get(name.lower(), None))
        if translated:
            return re.sub(r"^.+?(?=:)", translated, stripped)
        # Pas de traduction mais garder le header normalisé (sans espace avant ':')
        return re.sub(r"\s*:", ":", stripped)
    return line


def _build_pseudo_email(block_text: str) -> Optional[str]:
    """
    Extrait un bloc inline (De:/From: ... Objet:) et reconstruit
    un pseudo-email RFC 5322 valide pour parsing par email.parser.

    Gère:
    - Blocs De: ... Objet: ... seguido de body
    - Séparateurs ----- Original Message -----
    - Outlook multiline (continuation lines)
    """
    lines = block_text.split("\n")

    # Trouver la première ligne qui est un header reconnu
    start_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^(From|De|To|À|Date|Envoyé|Subject|Objet|Cc|Bcc)\s*:", line.strip(), re.IGNORECASE):
            start_idx = i
            break

    if start_idx is None:
        return None

    # Extraire les lignes headers (connues) jusqu'à la première ligne non-header
    header_lines = []
    body_lines = []
    in_headers = True

    for line in lines[start_idx:]:
        stripped = line.strip()
        if in_headers:
            if re.match(r"^(From|De|To|À|Date|Envoyé|Subject|Objet|Cc|Bcc)\s*:", stripped, re.IGNORECASE):
                header_lines.append(_normalize_header(line))
            elif stripped == "":
                in_headers = False
            elif stripped.startswith(" ") or stripped.startswith("\t"):
                # Continuation line Outlook (wrapping)
                if header_lines:
                    header_lines[-1] += " " + stripped
            else:
                in_headers = False
                body_lines.append(line)
        else:
            body_lines.append(line)

    if not header_lines:
        return None

    pseudo_email = "\n".join(header_lines) + "\n\n" + "\n".join(body_lines)
    return pseudo_email


def _parse_inline_headers(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse les headers inline (De:/From:/To:/À:/Objet:) en reconstruisant
    un pseudo-email RFC 5322 parsé par la lib standard email.parser.
    """
    if not text or len(text.strip()) < 10:
        return None

    pseudo = _build_pseudo_email(text)
    if not pseudo:
        return None

    from email.parser import Parser
    msg = Parser().parsestr(pseudo)

    headers = {}

    from_val = msg.get("From", "")
    if from_val:
        headers["from_email"] = _parse_address_email(from_val)
        headers["from_name"] = _parse_address_name(from_val)

    to_val = msg.get("To", "")
    if to_val:
        headers["to_emails"] = _split_emails(to_val)

    cc_val = msg.get("Cc", "")
    if cc_val:
        headers["cc_emails"] = _split_emails(cc_val)

    date_val = msg.get("Date", "")
    if date_val:
        headers["date"] = date_val

    subj_val = msg.get("Subject", "")
    if subj_val:
        headers["subject"] = subj_val

    body = msg.get_payload()
    if body and isinstance(body, str) and body.strip():
        headers["body_text"] = body.strip()

    if not headers:
        return None

    return headers


def _clean_msg_id(msg_id: str) -> str:
    """Nettoie un Message-ID (enlève les < >)."""
    return msg_id.strip("<>").strip() if msg_id else ""


def _parse_address(addr: str) -> Tuple[str, str]:
    """Parse une adresse 'Nom <email>' → (email, nom)."""
    if not addr:
        return ("", "")
    # Nettoyer les mailto: URLs (Outlook wrapping)
    cleaned = re.sub(r'<mailto:[^>]+>', '', addr)
    match = re.match(r'[^<]*<([^>]+)>', cleaned)
    if match:
        name = re.sub(r'\s*<[^>]+>', '', cleaned).strip()
        email = match.group(1).strip().rstrip('>')
        return (email, name.strip().strip('"'))
    return (cleaned.strip(), "")


def _parse_address_email(addr: str) -> str:
    """Extrait l'email d'une adresse 'Nom <email>'."""
    return _parse_address(addr)[0]


def _parse_address_name(addr: str) -> str:
    """Extrait le nom d'une adresse 'Nom <email>'."""
    return _parse_address(addr)[1]


def _parse_addresses(addrs: str) -> List[str]:
    """Parse une liste d'adresses séparées par des virgules."""
    if not addrs:
        return []
    emails = []
    for part in addrs.split(","):
        email_addr = _parse_address_email(part.strip())
        if email_addr:
            emails.append(email_addr)
    return emails


def _split_emails(text: str) -> List[str]:
    """Sépare une chaîne d'emails/virgules en liste."""
    if not text:
        return []
    emails = []
    for part in re.split(r"[;,]", text):
        part = part.strip()
        if part:
            email_addr = _parse_address_email(part)
            if email_addr:
                emails.append(email_addr)
            else:
                emails.append(part)
    return emails


def _parse_date(date_str: str) -> str:
    """Parse une date RFC 2822 ou française en ISO 8601."""
    if not date_str:
        return ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        pass
    try:
        from datetime import datetime
        months_fr = {
            "janvier": 1, "février": 2, "fevrier": 2, "mars": 3,
            "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
            "août": 8, "aout": 8, "septembre": 9, "octobre": 10,
            "novembre": 11, "décembre": 12, "decembre": 12,
        }
        for fr_name, num in months_fr.items():
            if fr_name in date_str.lower():
                match = re.search(
                    r"(\d{1,2})\s+" + fr_name[0].upper() + fr_name[1:].replace("é", "[éèe]") + r"\s*(\d{4})\s+(\d{1,2}):(\d{2})",
                    date_str, re.IGNORECASE
                )
                if not match:
                    match = re.search(
                        r"(\d{1,2})\s+" + fr_name + r"\s*(\d{4})\s+(\d{1,2}):(\d{2})",
                        date_str, re.IGNORECASE
                    )
                if match:
                    day, year, hour, minute = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                    dt = datetime(year, num, day, hour, minute)
                    return dt.isoformat()
    except Exception:
        pass
    return date_str


def _parse_references(refs: str) -> List[str]:
    """Parse les References en liste."""
    if not refs:
        return []
    return [_clean_msg_id(r) for r in refs.split() if r.strip()]


def _strip_html(html: str) -> str:
    """Enlève le HTML pour ne garder que le texte."""
    from html.parser import HTMLParser

    class HTMLTextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []
            self.skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self.skip = False
            if tag in ("p", "br", "div", "tr"):
                self.text.append("\n")

        def handle_data(self, data):
            if not self.skip:
                self.text.append(data)

    extractor = HTMLTextExtractor()
    extractor.feed(html)
    return "".join(extractor.text).strip()
