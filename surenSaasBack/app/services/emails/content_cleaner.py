"""
Service d'extraction du mail original et de nettoyage RAG Mail.

Détecte les patterns forward, extrait le mail original,
puis nettoie le contenu (signatures, mentions légales, etc.)
"""

import re
from dataclasses import dataclass
from typing import Optional, List

from app.core.logging import get_logger

logger = get_logger(__name__)


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
    
    # Patterns de détection forward - SÉPARATEURS seulement (ordre de priorité)
    FORWARD_SEPARATOR_PATTERNS = [
        r"-{3,}\s*Forwarded message\s*-{3,}",           # Gmail standard
        r"_+\s*Original Message\s*_+",                  # Outlook
        r"Begin forwarded message:",                    # Apple Mail
        r"-{3,}\s*Original\s*-{3,}",                   # Variante
        r"-{8,}\s*Message transféré\s*-{8,}",          # Thunderbird français
        r"----- Original Message -----",                # Outlook variante
        r"--- Forwarded message ---",                   # Gmail variante
        r"-{5,}\s*Forwarded\s*-{5,}",                  # Autre variante
        # Nouveaux patterns pour forwards sans séparateur explicite
        r"\nDe\s*:\s*.+?<.+?@.+?>\s*\nEnvoyé\s*:\s*.+?\nÀ\s*:\s*.+?\nObjet\s*:\s*.+?\n",  # Pattern français complet
        r"\nFrom\s*:\s*.+?<.+?@.+?>\s*\nDate\s*:\s*.+?\nTo\s*:\s*.+?\nSubject\s*:\s*.+?\n",  # Pattern anglais complet
    ]
    
    # Patterns de headers (pour extraction après avoir trouvé le séparateur)
    HEADER_PATTERNS = [
        r"De\s*:\s*",                             # Format français "De :"
        r"From\s*:\s*",                           # Format anglais "From :"
        r"Envoyé\s*:\s*",                         # Format français "Envoyé :"
        r"Date\s*:\s*",                           # "Date :" souvent au début d'un forward
        r"À\s*:\s*",                              # Format français "À :"
        r"To\s*:\s*",                             # Format anglais "To :"
        r"Objet\s*:\s*",                          # Format français "Objet :"
        r"Subject\s*:\s*",                        # Format anglais "Subject :"
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
        # 1. Vérifier les séparateurs explicites
        for pattern in self.FORWARD_SEPARATOR_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        # 2. Vérifier les forwards sans séparateur 
        # Pattern pour détecter un bloc de headers français complet
        french_header_pattern = r'\nDe\s*:\s*.+?(?:\nEnvoyé\s*:\s*.+?)?(?:\nÀ\s*:\s*.+?)?(?:\nObjet\s*:\s*.+?)\n'
        # Pattern pour détecter un bloc de headers anglais complet  
        english_header_pattern = r'\nFrom\s*:\s*.+?(?:\nDate\s*:\s*.+?)?(?:\nTo\s*:\s*.+?)?(?:\nSubject\s*:\s*.+?)\n'
        
        # Vérifier la présence de plusieurs headers consécutifs (au moins 3)
        header_patterns_to_check = [
            r'De\s*:\s*', r'From\s*:\s*',
            r'Envoyé\s*:\s*', r'Date\s*:\s*',
            r'À\s*:\s*', r'To\s*:\s*',
            r'Objet\s*:\s*', r'Subject\s*:\s*',
        ]
        
        header_count = 0
        for pattern in header_patterns_to_check:
            if re.search(pattern, content, re.IGNORECASE):
                header_count += 1
        
        # Si on trouve au moins 3 headers différents, c'est probablement un forward
        if header_count >= 3:
            return True
        
        # Vérifier les patterns spécifiques de blocs complets
        if re.search(french_header_pattern, content, re.IGNORECASE | re.DOTALL):
            return True
        if re.search(english_header_pattern, content, re.IGNORECASE | re.DOTALL):
            return True
        
        # 3. Vérifier les emails avec "TR:" (Transmis) dans le sujet ET des headers dans le corps
        if "TR:" in content.upper() or "TRANSFÉRÉ" in content.upper() or "TRANSMIS" in content.upper():
            # Vérifier si on a au moins "De :" et "Objet :" dans le corps
            has_de = re.search(r'De\s*:\s*', content, re.IGNORECASE)
            has_objet = re.search(r'(?:Objet|Subject)\s*:\s*', content, re.IGNORECASE)
            if has_de and has_objet:
                return True
        
        return False
    
    def extract_original_headers(self, forwarded_content: str) -> dict:
        """Extrait les headers du mail original."""
        headers = {}
        
        # Patterns pour les headers (anglais et français)
        # Capture jusqu'au prochain header, début du corps, ou max 500 caractères
        # Mots qui marquent le début du corps: Bonjour, Hello, Hi, Cher, Chère, etc.
        body_start_patterns = r"(?:Bonjour|Hello|Hi|Cher|Chère|Madame|Monsieur|Mesdames|Messieurs|Dear|Ladies|Gentlemen)"
        
        header_patterns = [
            # Français
            ("from", r"De\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("from", r"Expéditeur\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("date", r"Envoyé\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("date", r"Date\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("to", r"À\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("to", r"Destinataire\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("subject", r"Objet\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("subject", r"Sujet\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            # Anglais
            ("from", r"From\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("date", r"Date\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("to", r"To\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("subject", r"Subject\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("message_id", r"Message-ID\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
            ("in_reply_to", r"In-Reply-To\s*:\s*([^\n]{1,500}?)(?=\s*(?:À|To|De|From|Envoyé|Date|Objet|Subject|Sujet|Cc|" + body_start_patterns + r"|$|\n))"),
        ]
        
        # Trouver TOUS les séparateurs de forward (même logique que extract_original_body)
        separator_matches = []
        for pattern in self.FORWARD_SEPARATOR_PATTERNS:
            for match in re.finditer(pattern, forwarded_content, re.IGNORECASE):
                separator_matches.append((match.start(), match.end(), match.group()))
        
        if separator_matches:
            # Cas 1: Forward avec séparateur explicite
            # Trier par position (début)
            separator_matches.sort(key=lambda x: x[0])
            
            # Prendre le DERNIER séparateur (le plus récent)
            last_separator_start, last_separator_end, last_separator_pattern = separator_matches[-1]
            
            # Extraire ce qui vient après le DERNIER séparateur
            content_after_last_separator = forwarded_content[last_separator_end:]
            
            # Chercher les headers seulement dans cette section
            search_content = content_after_last_separator
        else:
            # Cas 2: Forward sans séparateur explicite
            search_content = forwarded_content
        
        # Chercher les headers dans la section appropriée
        for key, pattern in header_patterns:
            if key not in headers:  # Ne pas écraser si déjà trouvé
                match = re.search(pattern, search_content, re.IGNORECASE)
                if match:
                    headers[key] = match.group(1).strip()
        
        return headers
    
    def parse_french_date(self, date_str: str) -> str:
        """
        Convertit une date française en format ISO.
        
        Ex: "mardi 21 avril 2026 14:55" -> "2026-04-21T14:55:00"
        Ex: "21 avril 2026 à 10:30" -> "2026-04-21T10:30:00"
        """
        if not date_str:
            return ""
        
        # Noms des mois en français
        french_months = {
            "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
            "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
        }
        
        # Patterns de date françaises
        patterns = [
            # "mardi 21 avril 2026 14:55"
            r"(?:\w+)\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s+(\d{1,2}):(\d{2})",
            # "21 avril 2026 à 10:30"
            r"(\d{1,2})\s+(\w+)\s+(\d{4})\s+à\s+(\d{1,2}):(\d{2})",
            # "21 avril 2026 10:30"
            r"(\d{1,2})\s+(\w+)\s+(\d{4})\s+(\d{1,2}):(\d{2})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                hour = int(match.group(4))
                minute = int(match.group(5))
                
                if month_name in french_months:
                    month = french_months[month_name]
                    # Retourner au format ISO
                    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"
        
        # Si aucun pattern ne match, retourner la chaîne originale
        return date_str
    
    def parse_email_address(self, header_value: str) -> tuple[str, Optional[str]]:
        """
        Parse un header email pour extraire email + nom.
        
        Ex: "Service Commercial ACORUS <contact@acorus.fr>"
            -> ("contact@acorus.fr", "Service Commercial ACORUS")
        Ex: "CAROFF, Enzo" (sans email)
            -> ("", "CAROFF, Enzo")
        """
        # Pattern: Name <email@domain.com>
        match = re.match(r"(.+?)\s*<(.+?)>", header_value)
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return email, name
        
        # Chercher un email dans le texte
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', header_value)
        if email_match:
            email = email_match.group(0)
            # Extraire le nom (tout sauf l'email)
            name = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', header_value).strip()
            name = name.strip('"\'<> ')
            return email, name if name else None
        
        # Pas d'email trouvé, retourner le texte comme nom
        return "", header_value.strip()
    
    def extract_original_body(self, forwarded_content: str) -> str:
        """
        Extrait le corps du mail original d'un forward.
        Gère les chaînes d'emails imbriqués en prenant le PREMIER forward (le plus récent).
        
        Args:
            forwarded_content: Contenu complet du forward
            
        Returns:
            Corps du mail original (le PREMIER forward dans la chaîne)
        """
        # Trouver TOUS les séparateurs de forward
        separator_matches = []
        for pattern in self.FORWARD_SEPARATOR_PATTERNS:
            for match in re.finditer(pattern, forwarded_content, re.IGNORECASE):
                separator_matches.append((match.start(), match.end(), match.group()))
        
        if separator_matches:
            # Cas 1: Forward avec séparateur explicite
            # Trier par position (début)
            separator_matches.sort(key=lambda x: x[0])
            
            # Prendre le DERNIER séparateur (le plus récent)
            last_separator_start, last_separator_end, last_separator_pattern = separator_matches[-1]
            
            # Extraire ce qui vient après le DERNIER séparateur
            content_after_last_separator = forwarded_content[last_separator_end:]
            
            # Maintenant, dans cette section, trouver où commencent les headers
            # Chercher le premier header après le séparateur
            lines = content_after_last_separator.split('\n')
            
            # Trouver la première ligne qui contient un header pattern
            header_start = 0
            for i, line in enumerate(lines):
                for pattern in self.HEADER_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        header_start = i
                        break
                if header_start > 0:
                    break
            
            # Si pas de headers trouvés, retourner tout le contenu après le séparateur
            if header_start == 0:
                return content_after_last_separator.strip()
            
            # Trouver où finissent les headers (première ligne vide après header_start)
            body_start = header_start
            for i in range(header_start, min(header_start + 20, len(lines))):
                if lines[i].strip() == '':
                    body_start = i + 1
                    break
            
            # Si on trouve un autre séparateur avant la fin des headers, c'est une chaîne imbriquée
            # Dans ce cas, prendre tout jusqu'au prochain séparateur
            for i in range(header_start, min(header_start + 20, len(lines))):
                for pattern in self.FORWARD_SEPARATOR_PATTERNS:
                    if re.search(pattern, lines[i], re.IGNORECASE):
                        # C'est un nouveau forward imbriqué, s'arrêter avant
                        body_start = i
                        break
            
            body = '\n'.join(lines[body_start:])
            
            # Nettoyer les "De :", "From :", etc. qui pourraient rester
            body = self.remove_internal_headers(body)
            
            return body.strip()
        else:
            # Cas 2: Forward sans séparateur explicite (ex: "De :" directement dans le corps)
            # Chercher simplement la position de "De :" ou "From :"
            de_match = re.search(r'De\s*:\s*', forwarded_content, re.IGNORECASE)
            from_match = re.search(r'From\s*:\s*', forwarded_content, re.IGNORECASE)
            
            start_pos = -1
            if de_match:
                start_pos = de_match.start()
            elif from_match:
                start_pos = from_match.start()
            
            if start_pos == -1:
                # Pas de headers trouvés, retourner le contenu original
                return forwarded_content
            
            # Extraire le contenu à partir de "De :" ou "From :"
            content_from_de = forwarded_content[start_pos:]
            
            # Maintenant, dans cette section, trouver où se trouve "Objet :" ou "Subject :"
            # et extraire ce qui vient après
            objet_match = re.search(r'Objet\s*:\s*', content_from_de, re.IGNORECASE)
            subject_match = re.search(r'Subject\s*:\s*', content_from_de, re.IGNORECASE)
            
            headers_end = 0
            if objet_match:
                headers_end = objet_match.end()
            elif subject_match:
                headers_end = subject_match.end()
            
            if headers_end == 0:
                # Pas trouvé "Objet :" ou "Subject :", essayer une autre approche
                # Chercher la fin des headers (première ligne vide ou fin des headers typiques)
                lines = content_from_de.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == '':
                        headers_end = sum(len(lines[j]) + 1 for j in range(i))
                        break
                    # Si la ligne contient le début d'un email (ex: "Bonjour")
                    if re.match(r'^(Bonjour|Hello|Hi|Cher|Dear)', line, re.IGNORECASE):
                        headers_end = sum(len(lines[j]) + 1 for j in range(i))
                        break
            
            if headers_end == 0:
                # Toujours pas trouvé, prendre tout après "De :"
                headers_end = len(content_from_de)
            
            # Extraire le contenu après les headers
            content_after_headers = content_from_de[headers_end:]
            
            # Chercher où commence le vrai corps (première ligne non vide)
            lines = content_after_headers.split('\n')
            body_start = 0
            for i, line in enumerate(lines):
                if line.strip() != '':
                    body_start = i
                    break
            
            body = '\n'.join(lines[body_start:])
            
            # Nettoyer les headers internes qui pourraient rester
            body = self.remove_internal_headers(body)
            
            # Nettoyer les chaînes de forwards (supprimer les forwards suivants)
            body = self._remove_forward_chains(body)
            
            return body.strip()
    
    def _remove_forward_chains(self, content: str) -> str:
        """
        Supprime les forwards supplémentaires dans une chaîne.
        Garde seulement le PREMIER bloc de forward.
        
        Args:
            content: Contenu avec potentiellement plusieurs forwards
            
        Returns:
            Contenu avec seulement le premier forward
        """
        # Chercher le DEUXIÈME occurrence de "De :" ou "From :"
        de_patterns = [r'\nDe\s*:\s*', r'\nFrom\s*:\s*']
        
        first_pos = -1
        second_pos = -1
        
        for pattern in de_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if len(matches) >= 2:
                # Premier "De :" ou "From :"
                first_pos = matches[0].start()
                # Deuxième "De :" ou "From :" (début du forward suivant)
                second_pos = matches[1].start()
                break
        
        # Si on a trouvé un deuxième forward, supprimer tout ce qui vient après
        if second_pos > first_pos:
            logger.debug(f"🔍 Chaîne de forwards détectée, suppression après position {second_pos}")
            return content[:second_pos]
        
        return content
    
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
        
        # Convertir la date française en format ISO si nécessaire
        date_str = headers.get("date", "")
        if date_str:
            date_str = self.parse_french_date(date_str)
        
        return ExtractedEmail(
            from_email=from_email,
            from_name=from_name,
            to_emails=to_emails,
            subject=subject.strip(),
            date=date_str,
            body=original_body,
            body_cleaned=cleaned_body,
            message_id=headers.get("message_id"),
            in_reply_to=headers.get("in_reply_to"),
            references=references
        )


# Instance singleton
content_cleaner = ContentCleaner()
