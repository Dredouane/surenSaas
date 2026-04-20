"""
Module Emails - Services pour l'ingestion et la vectorisation des emails.
"""

from app.services.emails.gmail_client import GmailClient, create_gmail_client
from app.services.emails.alias_router import AliasRouter, alias_router, RoutingResult
from app.services.emails.content_cleaner import ContentCleaner, content_cleaner, ExtractedEmail
from app.services.emails.sync_service import SyncService, sync_service
from app.services.emails.embedding_service import EmbeddingService, embedding_service

__all__ = [
    # Gmail Client
    "GmailClient",
    "create_gmail_client",
    # Alias Router
    "AliasRouter",
    "alias_router",
    "RoutingResult",
    # Content Cleaner
    "ContentCleaner",
    "content_cleaner",
    "ExtractedEmail",
    # Sync Service
    "SyncService",
    "sync_service",
    # Embedding Service
    "EmbeddingService",
    "embedding_service",
]