"""
Service d'extraction du mail original et de nettoyage RAG Mail.

Détecte les patterns forward, extrait le mail original,
puis nettoie le contenu (signatures, mentions légales, etc.)
"""

import re
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ExtractedEmail:
    """Email original extrait d'un forward."""
    from_email: str
    from_name: Optional[str]
    to_emails: List[str]
    subject: str
    date: str
    body: str
    body_cleaned: str
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[List[str]] = None


class ContentCleaner:
    """Extrait le mail original d'un forward et nettoie le contenu."""
    
    # Patterns de détection forward (ordre de priorité)
    FORWARD_PATTERNS = [
        r"-+\s*Forwarded message\s*-+",           # Gmail standard (lenient dash count)
        r"_+\s*Original Message\s*_+",            # Outlook (lenient underscore count)
        r"Begin forwarded message:",               # Apple Mail
        r"-{3,}\s*Original\s*-{3,}",              # Variante
    ]
    
    # Patterns pour extraire les headers originaux
    HEADER_PATTERNS = {
        "from": r"(?:From|De)\s*:\s*(.+?)(?:\n|$)",
        "to": r"(?:To|À)\s*:\s*(.+?)(?:\n|$)",
        "date": r"(?:Date)\s*:\s*(.+?)(?:\n|$)",
        "subject": r"(?:Subject|Objet)\s*:\s*(.+?)(?:\n|$)",
        "message_id": r"Message-ID\s*:\s*(.+?)(?:\n|$)",
        "in_reply_to": r"In-Reply-To\s*:\s*(.+?)(?:\n|$)",
        "references": r"References\s*:\s*(.+?)(?:\n|$)",
    }
    
    # Signatures patterns
    SIGNATURE_PATTERNS = [
        r"\n--\s*\n.*",  # --
        r"\n-{2,}\s*\n.*",  # ---
        r"\n\s*Cordialement,?\s*\n.*",
        r"\n\s*Bien à vous,?\s*\n.*",
        r"\n\s*Meilleures salutations,?\s*\n.*",
        r"\n\s*Kind regards,?\s*\n.*",
        r"\n\s*Sincèrement,?\s*\n.*",
        r"\n\s*Cdlt,?\s*\n.*",
        r"\n\s*Cdt,?\s*\n.*",
    ]
    
    # Mentions légales patterns
    LEGAL_PATTERNS = [
        r"Ce message et toutes les pièces jointes sont confidentiels.*",
        r"This message and any attachments are confidential.*",
        r"Si vous avez reçu ce message par erreur.*",
        r"If you have received this message in error.*",
        r"La diffusion, la distribution ou la copie de ce message.*",
        r"Disclaimer:.*",
        r"Avertissement:.*",
    ]
    
    # Headers internes à supprimer
    INTERNAL_HEADER_PATTERNS = [
        r"Forwarded by.*",
        r"Forwarded from.*",
        r"De\s*:\s*.*",
        r"À\s*:\s*.*",
        r"Date\s*:\s*.*",
        r"Objet\s*:\s*.*",
        r"Expéditeur\s*:\s*.*",
    ]
    
    def detect_forward(self, content: str) -> bool:
        """Détecte si le contenu contient un forward."""
        for pattern in self.FORWARD_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False
    
    def extract_original_headers(self, forwarded_content: str) -> dict:
        """Extrait les headers du mail original."""
        headers = {}
        
        # Patterns simplifiés et plus robustes
        header_patterns = {
            "from": r"From:\s*([^\n]+)",
            "to": r"To:\s*([^\n]+)",
            "date": r"Date:\s*([^\n]+)",
            "subject": r"Subject:\s*([^\n]+)",
            "message_id": r"Message-ID:\s*([^\n]+)",
            "in_reply_to": r"In-Reply-To:\s*([^\n]+)",
        }
        
        for key, pattern in header_patterns.items():
            match = re.search(pattern, forwarded_content, re.IGNORECASE)
            if match:
                headers[key] = match.group(1).strip()
        
        return headers
    
    def parse_email_address(self, header_value: str) -> tuple[str, Optional[str]]:
        """
        Parse un header email pour extraire email + nom.
        
        Ex: "Service Commercial ACORUS <contact@acorus.fr>"
            -> ("contact@acorus.fr", "Service Commercial ACORUS")
        """
        # Pattern: Name <email@domain.com>
        match = re.match(r"(.+?)\s*<(.+?)>", header_value)
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return email, name
        
        # Juste l'email
        return header_value.strip(), None
    
    def extract_original_body(self, forwarded_content: str) -> str:
        """Extrait le corps original du mail forwardé."""
        # Trouver où commence le forward
        forward_start = None
        for pattern in self.FORWARD_PATTERNS:
            match = re.search(pattern, forwarded_content, re.IGNORECASE)
            if match:
                forward_start = match.end()
                break
        
        if forward_start is None:
            return forwarded_content
        
        # Extraire ce qui vient après le marker forward
        content_after_marker = forwarded_content[forward_start:]
        
        # Supprimer les headers originaux (ils sont sur les premières lignes)
        lines = content_after_marker.split('\n')
        body_start = 0
        
        for i, line in enumerate(lines):
            # Si ligne vide après headers, c'est le début du body
            if line.strip() == '' and i > 0:
                body_start = i + 1
                break
            # Si on a dépassé 10 lignes de headers, on arrête
            if i > 10:
                body_start = i
                break
        
        body = '\n'.join(lines[body_start:])
        return body.strip()
    
    def remove_signature(self, text: str) -> str:
        """Supprime la signature de l'email."""
        for pattern in self.SIGNATURE_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)
        return text.strip()
    
    def remove_legal_mentions(self, text: str) -> str:
        """Supprime les mentions légales."""
        for pattern in self.LEGAL_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        return text.strip()
    
    def remove_internal_headers(self, text: str) -> str:
        """Supprime les headers internes restants."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            skip = False
            for pattern in self.INTERNAL_HEADER_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    skip = True
                    break
            if not skip:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def clean_content(self, text: str) -> str:
        """
        Nettoie le contenu avec la logique RAG Mail.
        
        1. Suppression signatures
        2. Suppression mentions légales
        3. Suppression headers internes
        4. Nettoyage espaces superflus
        """
        text = self.remove_signature(text)
        text = self.remove_legal_mentions(text)
        text = self.remove_internal_headers(text)
        
        # Nettoyage espaces multiples
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text
    
    def extract_original(self, raw_content: str, raw_subject: str) -> ExtractedEmail:
        """
        Extrait le mail original d'un forward complet.
        
        Args:
            raw_content: Contenu brut du forward
            raw_subject: Sujet brut (avec potentiellement "Fwd:")
            
        Returns:
            ExtractedEmail avec les données originales
        """
        is_forward = self.detect_forward(raw_content)
        
        if not is_forward:
            # Pas un forward, retourner tel quel (nettoyé)
            cleaned = self.clean_content(raw_content)
            return ExtractedEmail(
                from_email="",  # À remplir par l'appelant
                from_name=None,
                to_emails=[],
                subject=raw_subject.replace("Fwd:", "").replace("FW:", "").strip(),
                date="",
                body=raw_content,
                body_cleaned=cleaned
            )
        
        # C'est un forward, extraire les infos
        headers = self.extract_original_headers(raw_content)
        original_body = self.extract_original_body(raw_content)
        cleaned_body = self.clean_content(original_body)
        
        # Parse From
        from_header = headers.get("from", "")
        from_email, from_name = self.parse_email_address(from_header)
        
        # Parse To
        to_header = headers.get("to", "")
        to_emails = [email.strip() for email in to_header.split(",")]
        
        # Parse Subject (retirer Re: et Fwd:)
        subject = headers.get("subject", raw_subject)
        subject = re.sub(r"^(Re:|Fwd:|FW:|RE:|FWD:)\s*", "", subject, flags=re.IGNORECASE)
        
        # Parse References
        references = None
        if "references" in headers:
            references = [ref.strip() for ref in headers["references"].split()]
        
        return ExtractedEmail(
            from_email=from_email,
            from_name=from_name,
            to_emails=to_emails,
            subject=subject.strip(),
            date=headers.get("date", ""),
            body=original_body,
            body_cleaned=cleaned_body,
            message_id=headers.get("message_id"),
            in_reply_to=headers.get("in_reply_to"),
            references=references
        )


# Instance singleton
content_cleaner = ContentCleaner()
