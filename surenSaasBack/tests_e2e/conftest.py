import sys
import os
import uuid as _uuid
import pytest
import pytest_asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.auth import get_supabase

TEST_ORG_SLUG = os.getenv("TEST_ORG_SLUG", "REDACTED_ORG_SLUG")
TEST_COMPANY_SLUG = "construction"


@pytest.fixture(scope="session")
def supabase():
    return get_supabase()


@pytest.fixture(scope="session")
def org_id(supabase) -> str:
    result = supabase.table("organizations").select("id").eq("slug", TEST_ORG_SLUG).single().execute()
    if not result.data:
        raise ValueError(f"Organization {TEST_ORG_SLUG} not found in DB")
    return result.data["id"]


@pytest.fixture(scope="session")
def company_id(supabase, org_id) -> str:
    result = supabase.table("companies").select("id").eq("slug", TEST_COMPANY_SLUG).eq("org_id", org_id).single().execute()
    if not result.data:
        raise ValueError(f"Company {TEST_COMPANY_SLUG} not found in DB for org {org_id}")
    return result.data["id"]


@pytest.fixture(scope="session")
def db_validator(supabase, org_id):
    from tests_e2e.validators.db_validator import DBValidator
    return DBValidator(supabase=supabase, org_id=org_id)


@pytest.fixture(scope="session")
def bot_token() -> str:
    token = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN")
    if not token:
        raise ValueError(
            "SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN is not set. "
            "Define it in ~/.bashrc or .env.test.local"
        )
    return token


@pytest.fixture(scope="session")
def bot_api_url() -> str:
    url = os.getenv("SUREN_TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_URL", "")
    if not url or "t.me" in url or "telegram.org" not in url:
        return "https://api.telegram.org"
    return url


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest_asyncio.fixture(scope="session")
async def tg_user(bot_token, bot_api_url):
    from tests_e2e.sim.telegram_user_sim import TelegramUserSim
    sim = TelegramUserSim(bot_token=bot_token, api_url=bot_api_url)
    await sim.start()
    yield sim
    await sim.stop()
