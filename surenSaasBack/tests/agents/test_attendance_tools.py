"""Tests unitaires sur vraie DB Supabase — match_resources + upsert_attendance.

Couvre R10 (ressources existantes dans l'orga) et R13 (unicité, pas de doublon).
Utilise les vraies données Supabase test.
"""

from datetime import date, timedelta

import pytest

from app.agents.tools.attendance_tools import (
    _match_resources_internal,
    _upsert_attendance_internal,
)

pytestmark = pytest.mark.agents


# ─── Helpers ───────────────────────────────────────────────────────────

def _find_first(supabase, org_id, nom_partiel):
    """Cherche une ressource par substring dans la DB."""
    res = supabase.table("chantier_ressources").select("id, nom, type").eq("org_id", org_id).execute()
    for r in res.data or []:
        if nom_partiel.lower() in (r.get("nom") or "").lower():
            return r
    return None


# ─── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def rachid(supabase, org_id):
    """Ressource 'BOUAZIZ Rabie' dans la DB test."""
    r = _find_first(supabase, org_id, "BOUAZIZ Rabie")
    if not r:
        pytest.skip("BOUAZIZ Rabie introuvable en DB — checker les fixtures")
    return r


@pytest.fixture
def jean(supabase, org_id):
    """Ressource 'JACQUET Jean Enol' dans la DB test."""
    r = _find_first(supabase, org_id, "JACQUET Jean Enol")
    if not r:
        pytest.skip("JACQUET Jean Enol introuvable")
    return r


@pytest.fixture
def mohamed(supabase, org_id):
    """Ressource 'GUIRAT Mohamed' dans la DB test."""
    r = _find_first(supabase, org_id, "GUIRAT Mohamed")
    if not r:
        pytest.skip("GUIRAT Mohamed introuvable")
    return r


@pytest.fixture
def pt_date():
    return date.today().isoformat()


# ─── match_resources : R10 + fuzzy matching ──────────────────────────

class TestMatchResources:
    """match_resources : fuzzy matching sur les vrais noms DB."""

    def test_match_by_full_nom(self, supabase, org_id, chantier_id, rachid):
        """R10 : Une recherche par nom complet trouve la ressource."""
        result = _match_resources_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            query="BOUAZIZ Rabie",
            _supabase=supabase,
        )
        assert result["success"] is True
        assert result["count"] >= 1
        ids = [r["id"] for r in result["data"]]
        assert rachid["id"] in ids, "BOUAZIZ Rabie non trouvé malgré existence DB"

    def test_match_by_prenom_partiel(self, supabase, org_id, chantier_id, rachid):
        """R10 : Un prénom partiel trouve la ressource (score >= 0.8)."""
        result = _match_resources_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            query="Rabie",
            _supabase=supabase,
        )
        assert result["success"] is True
        assert result["count"] >= 1
        ids = [r["id"] for r in result["data"]]
        assert rachid["id"] in ids

    def test_match_jean_trouve_jean_enol(self, supabase, org_id, chantier_id, jean):
        """R10 : 'Jean' trouve JACQUET Jean Enol."""
        result = _match_resources_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            query="Jean",
            _supabase=supabase,
        )
        assert result["success"] is True
        assert result["count"] >= 1
        ids = [r["id"] for r in result["data"]]
        assert jean["id"] in ids

    def test_match_returns_top5(self, supabase, org_id, chantier_id):
        """R10 : Au max 5 résultats retournés."""
        result = _match_resources_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            query="a",
            _supabase=supabase,
        )
        assert result["success"] is True
        assert len(result["data"]) <= 5

    def test_match_unknown_returns_empty(self, supabase, org_id, chantier_id):
        """R10 : Un nom inexistant retourne 0 résultat."""
        result = _match_resources_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            query="XxYyZzUnknown",
            _supabase=supabase,
        )
        assert result["success"] is True
        assert result["count"] == 0

    def test_match_respects_org_id(self, supabase, chantier_id):
        """R10 : Les ressources d'une org_id inexistante retournent 0."""
        fake_org = "00000000-0000-0000-0000-000000000000"
        result = _match_resources_internal(
            org_id=fake_org,
            chantier_id=chantier_id,
            query="Rabie",
            _supabase=supabase,
        )
        assert result["success"] is True
        assert result["count"] == 0


# ─── upsert_attendance : R13 + accumulation session ───────────────────

class TestUpsertAttendance:
    """upsert_attendance : création, upsert, verrouillage."""

    def _delete_pointage(self, supabase, pt_id):
        """Nettoie les lignes pointage après un test."""
        supabase.table("chantier_pointage_ressources").delete().eq("pointage_id", pt_id).execute()
        supabase.table("chantier_pointages").delete().eq("id", pt_id).execute()

    def test_creates_attendance_for_one_ressource(
        self, supabase, org_id, chantier_id, rachid, pt_date
    ):
        """R13 : Crée un pointage pour une seule ressource."""
        result = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=pt_date,
            ressources=[{"ressource_id": rachid["id"], "present": True, "nom": rachid["nom"]}],
            _supabase=supabase,
        )
        assert result["success"] is True, f"Erreur: {result.get('error')}"
        pt_id = result["data"]["pointage_id"]
        assert pt_id is not None

        # Vérification : une ligne dans chantier_pointage_ressources
        lines = (
            supabase.table("chantier_pointage_ressources")
            .select("id, ressource_id, presence")
            .eq("pointage_id", pt_id)
            .execute()
        )
        assert len(lines.data) == 1
        assert lines.data[0]["ressource_id"] == rachid["id"]
        assert lines.data[0]["presence"] is True

        self._delete_pointage(supabase, pt_id)

    def test_creates_attendance_for_multiple_ressources(
        self, supabase, org_id, chantier_id, rachid, jean, mohamed, pt_date
    ):
        """R13 : Crée un pointage pour 3 ressources simultanément."""
        ressources = [
            {"ressource_id": rachid["id"], "present": True, "nom": rachid["nom"]},
            {"ressource_id": jean["id"], "present": True, "nom": jean["nom"]},
            {"ressource_id": mohamed["id"], "present": False, "nom": mohamed["nom"]},
        ]
        result = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=pt_date,
            ressources=ressources,
            _supabase=supabase,
        )
        assert result["success"] is True
        pt_id = result["data"]["pointage_id"]

        lines = (
            supabase.table("chantier_pointage_ressources")
            .select("id, ressource_id, presence")
            .eq("pointage_id", pt_id)
            .execute()
        )
        assert len(lines.data) == 3

        self._delete_pointage(supabase, pt_id)

    def test_upsert_same_resource_does_not_duplicate(
        self, supabase, org_id, chantier_id, rachid, pt_date
    ):
        """R13 : Upsert du même ressource ne crée pas de doublon."""
        # Premier appel
        r1 = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=pt_date,
            ressources=[{"ressource_id": rachid["id"], "present": True, "nom": rachid["nom"]}],
            _supabase=supabase,
        )
        assert r1["success"] is True
        pt_id = r1["data"]["pointage_id"]

        # Deuxième appel (update : présent → False)
        r2 = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=pt_date,
            ressources=[{"ressource_id": rachid["id"], "present": False, "nom": rachid["nom"]}],
            _supabase=supabase,
        )
        assert r2["success"] is True
        assert r2["data"]["pointage_id"] == pt_id  # Même pointage

        # Vérification : toujours 1 ligne, presence=False
        lines = (
            supabase.table("chantier_pointage_ressources")
            .select("id, ressource_id, presence")
            .eq("pointage_id", pt_id)
            .execute()
        )
        assert len(lines.data) == 1, "Doublon créé au lieu d'upsert"
        assert lines.data[0]["presence"] is False

        self._delete_pointage(supabase, pt_id)

    def test_rejects_future_date(self, supabase, org_id, chantier_id):
        """R13 : Une date future est refusée."""
        future = (date.today() + timedelta(days=3)).isoformat()
        result = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=future,
            ressources=[],
            _supabase=supabase,
        )
        assert result["success"] is False
        assert "futur" in result.get("error", "").lower()

    def test_default_status_is_brouillon(self, supabase, org_id, chantier_id, rachid, pt_date):
        """R13 : Le pointage parent a le status 'brouillon' par défaut (colonne = 'status')."""
        result = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=pt_date,
            ressources=[{"ressource_id": rachid["id"], "present": True, "nom": rachid["nom"]}],
            _supabase=supabase,
        )
        assert result["success"] is True
        pt_id = result["data"]["pointage_id"]

        pt = supabase.table("chantier_pointages").select("status").eq("id", pt_id).execute()
        assert pt.data[0]["status"] == "brouillon"

        self._delete_pointage(supabase, pt_id)

    def test_rejects_already_validated_or_pending(
        self, supabase, org_id, chantier_id, rachid, pt_date
    ):
        """R13 : Un pointage déjà 'en_attente_validation' ou 'valide' est refusé."""
        # Créer un pointage avec status 'brouillon'
        r1 = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=pt_date,
            ressources=[{"ressource_id": rachid["id"], "present": True, "nom": rachid["nom"]}],
            _supabase=supabase,
        )
        pt_id = r1["data"]["pointage_id"]

        # Forcer le status à 'en_attente_validation' en DB (simule une validation HITL)
        supabase.table("chantier_pointages").update({"status": "en_attente_validation"}).eq("id", pt_id).execute()

        # Tentative de modifier
        r2 = _upsert_attendance_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            date_pointage=pt_date,
            ressources=[{"ressource_id": rachid["id"], "present": False, "nom": rachid["nom"]}],
            _supabase=supabase,
        )
        assert r2["success"] is False
        msg = (r2.get("error") or "") + (r2.get("suggestion") or "")
        assert "déjà" in msg.lower(), f"Message d'erreur non pertinent: {r2.get('error')}"

        self._delete_pointage(supabase, pt_id)
