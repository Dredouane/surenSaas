"""Configuration Pytest pour les tests agents.

Connexion directe à la vraie base Supabase TEST.
Pas de mock — on valide comportement réel.
Utilise SUPABASE_URL + SUPABASE_SERVICE_KEY depuis l'environnement.
"""

import pytest
import os
from supabase import create_client


# ─── Identifiants de test ───────────────────────────────────────────────
ORG_ID = "REDACTEDORG"
CHANTIER_ALPHA_ID = "d02e9843-a3a5-46f3-a2d2-5a9bc9c31fb5"  # "Magasin Commercial"
CHANTIER_ALPHA_NOM = "Magasin Commercial"


@pytest.fixture(scope="session")
def supabase():
    """Client Supabase connecté à la vraie DB test."""
    url = os.environ.get(
        "SUPABASE_URL",
        "https://REDACTED.supabase.co",
    )
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("TEST_SUPABASE_SERVICE_KEY")
    )
    if not key:
        pytest.fail("SUPABASE_SERVICE_KEY introuvable dans l'environnement")
    return create_client(url, key)


@pytest.fixture
def org_id():
    return ORG_ID


@pytest.fixture
def chantier_id():
    return CHANTIER_ALPHA_ID


@pytest.fixture
def chantier_nom():
    return CHANTIER_ALPHA_NOM
