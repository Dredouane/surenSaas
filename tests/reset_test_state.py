#!/usr/bin/env python3
"""
reset_test_state.py — Nettoie les données de test pour un chat_id donné.

Usage:
    python tests/reset_test_state.py
    python tests/reset_test_state.py --chat-id 999999
    python tests/reset_test_state.py --dry-run
    python tests/reset_test_state.py --verbose

Prérequis : 
    - Variables d'env : SUPABASE_URL, SUPABASE_SERVICE_KEY
    - Ou via ~/.bashrc : TEST_SUPABASE_URL, TEST_SUPABASE_SERVICE_KEY
"""

import os
import sys
import argparse
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("reset_test_state")

DEFAULT_CHAT_ID = 999999

# Tables à nettoyer avec leur colonne de filtrage
TABLES = [
    ("langgraph_checkpoint_checkpoints", "thread_id", True),
    ("langgraph_checkpoint_writes", "thread_id", True),
    ("telegram_conversations", "chat_id", False),
    ("telegram_messages", "chat_id", False),
    ("expenses", "telegram_user_id", False),
    ("timesheet_entries", "telegram_user_id", False),
    ("pointages", "telegram_user_id", False),
]


def get_supabase():
    """Initialize and return a Supabase client."""
    try:
        from supabase import create_client
    except ImportError:
        logger.error("❌ Module 'supabase' non installé. Fais : pip install supabase")
        sys.exit(1)

    url = os.getenv("SUPABASE_URL") or os.getenv("TEST_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("TEST_SUPABASE_SERVICE_KEY")

    if not url or not key:
        logger.error("❌ SUPABASE_URL ou SUPABASE_SERVICE_KEY non défini.")
        logger.error("   Source ~/.bashrc ou exporte-les manuellement.")
        sys.exit(1)

    return create_client(url, key)


def detect_additional_tables(supabase, chat_id: int) -> list:
    """Tente de détecter d'autres tables qui contiennent une colonne liée au chat_id."""
    # On ne peut pas lister les tables via Supabase REST directement.
    # Retourne une liste vide — les tables ci-dessus sont suffisantes.
    return []


def count_records(supabase, table: str, column: str, value) -> Optional[int]:
    """Compte les enregistrements pour une table/colonne/valeur donnée."""
    try:
        result = (
            supabase.table(table)
            .select("*", count="exact")
            .eq(column, value)
            .execute()
        )
        return result.count if hasattr(result, "count") else None
    except Exception:
        return None


def delete_records(supabase, table: str, column: str, value, dry_run: bool = False) -> int:
    """Supprime (ou compte) les enregistrements pour une table."""
    try:
        if dry_run:
            count = count_records(supabase, table, column, value)
            return count or 0
        else:
            result = (
                supabase.table(table)
                .delete()
                .eq(column, value)
                .execute()
            )
            return len(result.data) if result.data else 0
    except Exception as e:
        err_str = str(e)
        if "relation" in err_str and "does not exist" in err_str:
            logger.debug(f"  ⏭️  Table {table} n'existe pas — ignorée")
            return 0
        logger.debug(f"  ⏭️  Table {table} inaccessible: {err_str[:80]}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Nettoie les données de test Supabase pour un chat_id donné."
    )
    parser.add_argument(
        "--chat-id",
        type=int,
        default=DEFAULT_CHAT_ID,
        help=f"Chat ID à nettoyer (défaut: {DEFAULT_CHAT_ID})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche ce qui serait supprimé sans exécuter les DELETE",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Affiche toutes les tables même si vides",
    )
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    chat_id = args.chat_id
    mode = "🔍 DRY RUN" if args.dry_run else "🧹 NETTOYAGE"
    logger.info(f"{'='*50}")
    logger.info(f"{mode} pour chat_id={chat_id}")
    logger.info(f"{'='*50}")

    supabase = get_supabase()
    total = 0

    for table, column, is_thread in TABLES:
        value = str(chat_id) if is_thread else chat_id
        count = delete_records(supabase, table, column, value, dry_run=args.dry_run)

        if count > 0 or args.verbose:
            action = "À supprimer" if args.dry_run else "Supprimé"
            logger.info(f"  {action}: {table}.{column}={value} → {count} enregistrement(s)")
        total += count

    # Détection supplémentaire (expérimentale)
    extra_tables = detect_additional_tables(supabase, chat_id)
    if extra_tables and args.verbose:
        logger.info(f"  Tables additionnelles détectées: {extra_tables}")

    logger.info(f"{'='*50}")
    if args.dry_run:
        logger.info(f"✅ Dry-run terminé — {total} enregistrement(s) seraient supprimés")
    else:
        logger.info(f"✅ Nettoyage terminé — {total} enregistrement(s) supprimés")
    logger.info(f"{'='*50}")

    return 0 if total >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
