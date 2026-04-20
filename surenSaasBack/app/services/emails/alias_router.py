"""
Service de routing par alias Gmail.

Extrait org_slug et company_slug de l'adresse Delivered-To
REDACTED_EMAIL
"""

import os
import re
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.api.auth import get_supabase


@dataclass
class RoutingResult:
    """Résultat du routing d'un email."""
    org_id: Optional[UUID]
    company_id: Optional[UUID]
    routing_status: str  # 'routed', 'ignored_no_alias', 'ignored_org_mismatch', etc.
    org_slug: Optional[str] = None
    company_slug: Optional[str] = None


class AliasRouter:
    """Route les emails vers la bonne org/company via parsing d'alias."""
    
    def __init__(self):
        self.separator = os.getenv("EMAIL_ALIAS_SEPARATOR", "#")
        self.env_org_slug = getattr(settings, 'org_slug', None)  # TEST_ORG_SLUG ou PROD_ORG_SLUG
        
    def _build_regex(self) -> str:
        """Construit la regex dynamique selon le séparateur configuré."""
        escaped_sep = re.escape(self.separator)
        # Pattern: +{org_slug}{separator}{company_slug}@gmail.com
        return rf"\+([^{escaped_sep}@]+){escaped_sep}([^@]+)@gmail\.com"
    
    def parse_alias(self, delivered_to: str) -> Optional[tuple[str, str]]:
        """
        Parse l'adresse Delivered-To pour extraire org_slug et company_slug.
        
        Args:
            delivered_to: Adresse email (ex: REDACTED_EMAIL)
            
        Returns:
            Tuple (org_slug, company_slug) ou None si pas d'alias
        """
        if not delivered_to:
            return None
            
        pattern = self._build_regex()
        match = re.search(pattern, delivered_to)
        
        if match:
            org_slug = match.group(1)
            company_slug = match.group(2)
            return org_slug, company_slug
        
        return None
    
    async def route(self, delivered_to: str) -> RoutingResult:
        """
        Route l'email vers la bonne org/company.
        
        Args:
            delivered_to: Adresse email Delivered-To
            
        Returns:
            RoutingResult avec org_id, company_id et statut
        """
        if not delivered_to:
            return RoutingResult(
                org_id=None,
                company_id=None,
                routing_status="ignored_no_alias"
            )
        
        # Vérifier s'il y a un signe + (début d'alias)
        has_plus = '+' in delivered_to
        
        # 1. Vérifier s'il y a un alias valide
        parsed = self.parse_alias(delivered_to)
        if not parsed:
            # S'il y a un + mais pas de match, c'est un format invalide
            if has_plus:
                return RoutingResult(
                    org_id=None,
                    company_id=None,
                    routing_status="ignored_invalid_format"
                )
            return RoutingResult(
                org_id=None,
                company_id=None,
                routing_status="ignored_no_alias"
            )
        
        org_slug, company_slug = parsed
        
        # 2. Valider que l'org_slug correspond à l'environnement courant
        if org_slug != self.env_org_slug:
            return RoutingResult(
                org_id=None,
                company_id=None,
                routing_status="ignored_org_mismatch",
                org_slug=org_slug,
                company_slug=company_slug
            )
        
        # 3. Lookup org_id par slug
        supabase = get_supabase()
        org_response = supabase.table("organizations")\
            .select("id")\
            .eq("slug", org_slug)\
            .single()\
            .execute()
        
        if not org_response.data:
            return RoutingResult(
                org_id=None,
                company_id=None,
                routing_status="ignored_org_not_found",
                org_slug=org_slug,
                company_slug=company_slug
            )
        
        org_id = org_response.data["id"]
        
        # 4. Lookup company_id par slug + org_id
        try:
            company_response = supabase.table("companies")\
                .select("id")\
                .eq("slug", company_slug)\
                .eq("org_id", org_id)\
                .single()\
                .execute()
            company_id = company_response.data["id"]
        except Exception:
            # Company not found
            return RoutingResult(
                org_id=org_id,
                company_id=None,
                routing_status="ignored_company_not_found",
                org_slug=org_slug,
                company_slug=company_slug
            )
        
        # 5. Routing OK
        return RoutingResult(
            org_id=org_id,
            company_id=company_id,
            routing_status="routed",
            org_slug=org_slug,
            company_slug=company_slug
        )


# Instance singleton
alias_router = AliasRouter()
