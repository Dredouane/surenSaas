#!/usr/bin/env python3
"""
Hermès Email Sync — Point d'entrée autonome pour le cron job Linux.

Usage:
    python scripts/hermes_email_sync.py
    python scripts/hermes_email_sync.py --account-id <UUID>
    python scripts/hermes_email_sync.py --mode historical --start 2025-01-01 --end 2025-06-01

Cron (toutes les 5 min):
    */5 * * * * /usr/bin/python3 /app/scripts/hermes_email_sync.py >> /var/log/hermes_sync.log 2>&1
"""

import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from dotenv import load_dotenv
    for env_file in [".env.prod", ".env.test", ".env"]:
        full_path = os.path.join(project_root, env_file)
        if os.path.exists(full_path):
            load_dotenv(full_path, override=False)
            break
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HERMES] %(levelname)s %(name)s \u2014 %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("hermes_sync")


async def run_sync(account_id: str | None, mode: str, start_date: str | None, end_date: str | None):
    try:
        from app.services.emails.sync_service import sync_service
        from app.api.auth import get_supabase
    except ImportError as e:
        logger.error(f"Erreur d'importation : {e}")
        return

    sb = get_supabase()

    query = sb.table("email_accounts").select("id, email_address").eq("is_active", True)
    if account_id:
        query = query.eq("id", account_id)

    try:
        accounts_resp = query.execute()
        accounts = accounts_resp.data or []
    except Exception as e:
        logger.error(f"Erreur Supabase: {e}")
        return

    if not accounts:
        logger.warning("Aucun compte email actif trouvé.")
        return

    logger.info(f"Synchronisation de {len(accounts)} compte(s) email \u2014 mode={mode}")

    total_stats = {"synced": 0, "ignored": 0, "errors": 0}

    for account in accounts:
        acc_id = account["id"]
        acc_email = account.get("email_address", acc_id)
        logger.info(f"\u2192 Traitement du compte: {acc_email}")

        try:
            date_range = None
            if mode == "historical" and start_date and end_date:
                date_range = {"start_date": start_date, "end_date": end_date}

            stats = await sync_service.sync_account(
                account_id=acc_id,
                sync_mode=mode,
                date_range=date_range,
            )

            logger.info(
                f"  \u2713 {acc_email} \u2014 synced={stats.get('synced', 0)} "
                f"ignored={stats.get('ignored', 0)} errors={stats.get('errors', 0)} "
                f"duration={stats.get('duration_seconds', 0)}s"
            )
            for k in ("synced", "ignored", "errors"):
                total_stats[k] += stats.get(k, 0)

        except Exception as e:
            logger.error(f"  \u2717 \u00c9chec synchronisation {acc_email}: {e}", exc_info=True)
            total_stats["errors"] += 1

    logger.info(
        f"Synchronisation termin\u00e9e \u2014 "
        f"synced={total_stats['synced']} "
        f"ignored={total_stats['ignored']} "
        f"errors={total_stats['errors']}"
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Herm\u00e8s Email Sync \u2014 Cron entrypoint")
    parser.add_argument("--account-id", help="UUID du compte email sp\u00e9cifique")
    parser.add_argument("--mode", choices=["incremental", "historical"], default="incremental")
    parser.add_argument("--start", help="Date de d\u00e9but pour mode historical (YYYY-MM-DD)")
    parser.add_argument("--end", help="Date de fin pour mode historical (YYYY-MM-DD)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start_ts = datetime.utcnow()
    logger.info(f"=== Herm\u00e8s Email Sync d\u00e9marr\u00e9 \u00e0 {start_ts.isoformat()} ===")

    try:
        import google.generativeai as genai
        from langchain_google_genai import ChatGoogleGenerativeAI
        from supabase import create_client
    except ImportError as e:
        logger.error(f"D\u00e9pendance manquante critique : {e}")
        sys.exit(1)

    asyncio.run(run_sync(
        account_id=args.account_id,
        mode=args.mode,
        start_date=args.start,
        end_date=args.end,
    ))

    elapsed = (datetime.utcnow() - start_ts).total_seconds()
    logger.info(f"=== Termin\u00e9 en {elapsed:.1f}s ===")
