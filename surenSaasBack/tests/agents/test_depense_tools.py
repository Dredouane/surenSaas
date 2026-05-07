"""Tests unitaires sur vraie DB Supabase — create_depense.

Couvre R1 (chantier courant) et R5 (pas de date future).
Utilise la vraie base de test — cleanup après chaque test.

Note: La table chantier_depenses a DEUX colonnes de statut :
  - `statut` : enum PostgreSQL (valeur par défaut 'validee')
  - `status` : colonne text libre pour le workflow ('en_attente_validation', etc.)
Le tool écrit toujours dans `status` pour ne pas violer l'enum.
"""

from datetime import date, timedelta

import pytest

from app.agents.tools.depense_tools import _create_depense_internal

pytestmark = pytest.mark.agents


class TestCreateDepense:
    """create_depense : persistance + règles R1, R5."""

    # ─── R1 : chantier présent ────────────────────────────────────

    def test_creates_with_chantier_id(self, supabase, org_id, chantier_id):
        """R1 : Une dépense est créée avec le bon chantier_id."""
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Test dépense R1",
            montant=100.0,
            fournisseur="TestFournisseur",
            categorie="fournisseur",
            _supabase=supabase,
        )
        assert result["success"] is True, f"Erreur: {result.get('error')}"
        dep_id = result["data"]["id"]
        assert dep_id is not None, "Aucun ID retourné après insert"

        # Vérification réelle en DB
        row = supabase.table("chantier_depenses").select("*").eq("id", dep_id).execute()
        assert len(row.data) == 1, "La ligne insérée n'existe pas en DB"
        assert row.data[0]["chantier_id"] == chantier_id
        assert row.data[0]["org_id"] == org_id

        # Cleanup
        supabase.table("chantier_depenses").delete().eq("id", dep_id).execute()

    def test_default_status_is_en_attente_validation(self, supabase, org_id, chantier_id):
        """Le tool écrit dans 'status' (colonne text) = 'en_attente_validation'."""
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Test status",
            montant=50.0,
            _supabase=supabase,
        )
        assert result["success"] is True
        dep_id = result["data"]["id"]

        row = supabase.table("chantier_depenses").select("status, statut").eq("id", dep_id).execute()
        assert row.data[0]["status"] == "en_attente_validation", (
            f"Le tool doit écrire status='en_attente_validation', obtenu: {row.data[0]['status']}"
        )
        # 'statut' (enum) garde sa valeur par défaut 'validee'
        assert row.data[0]["statut"] == "validee"

        supabase.table("chantier_depenses").delete().eq("id", dep_id).execute()

    def test_accepts_today_date(self, supabase, org_id, chantier_id):
        """R5 : La date du jour est acceptée."""
        today = date.today().isoformat()
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Test date today",
            montant=50.0,
            date_depense=today,
            _supabase=supabase,
        )
        assert result["success"] is True, f"Erreur: {result.get('error')}"
        dep_id = result["data"]["id"]

        row = supabase.table("chantier_depenses").select("date").eq("id", dep_id).execute()
        assert row.data[0]["date"] == today

        supabase.table("chantier_depenses").delete().eq("id", dep_id).execute()

    def test_accepts_past_date(self, supabase, org_id, chantier_id):
        """R5 : Une date passée est acceptée."""
        past = (date.today() - timedelta(days=5)).isoformat()
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Test date passée",
            montant=50.0,
            date_depense=past,
            _supabase=supabase,
        )
        assert result["success"] is True
        dep_id = result["data"]["id"]
        supabase.table("chantier_depenses").delete().eq("id", dep_id).execute()

    # ─── R5 : date future refusée ─────────────────────────────────

    def test_rejects_future_date(self, supabase, org_id, chantier_id):
        """R5 (impitoyable) : Une date future est refusée avec un message clair."""
        future = (date.today() + timedelta(days=3)).isoformat()
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Test date future",
            montant=50.0,
            date_depense=future,
            _supabase=supabase,
        )
        assert result["success"] is False
        assert "futur" in result.get("error", "").lower()

    # ─── Format date invalide ─────────────────────────────────────

    def test_rejects_invalid_date_format(self, supabase, org_id, chantier_id):
        """R5 : Un format de date invalide est refusé."""
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Bad date",
            montant=50.0,
            date_depense="pas-une-date",
            _supabase=supabase,
        )
        assert result["success"] is False
        assert "format" in result.get("error", "").lower()

    # ─── R1 : org_id correct ──────────────────────────────────────

    def test_creates_with_correct_org_id(self, supabase, org_id, chantier_id):
        """R1 : L'org_id est bien celui passé."""
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Test org_id",
            montant=75.0,
            _supabase=supabase,
        )
        assert result["success"] is True
        dep_id = result["data"]["id"]

        row = supabase.table("chantier_depenses").select("org_id").eq("id", dep_id).execute()
        assert row.data[0]["org_id"] == org_id

        supabase.table("chantier_depenses").delete().eq("id", dep_id).execute()

    # ─── Colonne 'statut' vs 'status' ────────────────────────────

    def test_uses_status_column_for_workflow(self, supabase, org_id, chantier_id):
        """Convention : le tool écrit dans 'status' (text), pas 'statut' (enum DB)."""
        result = _create_depense_internal(
            org_id=org_id,
            chantier_id=chantier_id,
            description="Test colonne status",
            montant=30.0,
            _supabase=supabase,
        )
        assert result["success"] is True
        dep_id = result["data"]["id"]

        row = supabase.table("chantier_depenses").select("status, statut").eq("id", dep_id).execute()
        # 'status' (text) est 'en_attente_validation' — workflow
        assert row.data[0]["status"] == "en_attente_validation"
        # 'statut' (enum) reste 'validee' — valeur par défaut de la DB
        assert row.data[0]["statut"] == "validee"

        supabase.table("chantier_depenses").delete().eq("id", dep_id).execute()
