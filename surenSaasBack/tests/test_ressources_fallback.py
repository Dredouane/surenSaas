#!/usr/bin/env python3
"""
Tests pour le fallback org-wide des ressources.

Quand un chantier n'a pas de ressources, l'endpoint doit retourner
les ressources org-wide (comportement du bot Telegram).
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException
from app.api.chantiers import list_ressources
from app.services.tma_auth_service import TmaAuthService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_supabase():
    """Mock Supabase pour simuler différents scénarios de données."""
    sb = MagicMock()

    def _table(name):
        t = MagicMock()
        if name == "chantier_ressources":
            # Par défaut, pas de résultat pour un chantier spécifique
            t.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            # Pour org-wide (sans chantier_id), retourner des données
            t.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {"id": "r1", "nom": "Jean", "type": "homme", "org_id": "org-1", "chantier_id": None},
                {"id": "r2", "nom": "Pierre", "type": "homme", "org_id": "org-1", "chantier_id": None},
                {"id": "r3", "nom": "Pelle mécanique", "type": "machine", "org_id": "org-1", "chantier_id": None},
            ]
        if name == "chantiers":
            t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": "chantier-uuid"}
            ]
        return t
    sb.table.side_effect = _table
    return sb


class TestRessourcesList:
    @patch("app.api.chantiers.get_supabase")
    @patch("app.api.chantiers.check_user_org_access")
    async def test_list_ressources_with_chantier_filter(self, mock_check, mock_get_sb, mock_supabase):
        """Vérifie que l'endpoint filtre d'abord par chantier_id."""
        mock_check.return_value = {"org_id": "org-1", "email": "test@test.com"}
        mock_get_sb.return_value = mock_supabase

        class MockRequest:
            class _H:
                def get(self, k, d=None): return ""
            headers = _H()

        result = await list_ressources(MockRequest(), org_id="org-1", chantier_id="chantier-uuid")

        # 3 ressources org-wide retournées (fallback)
        assert len(result) == 3

    @patch("app.api.chantiers.get_supabase")
    @patch("app.api.chantiers.check_user_org_access")
    async def test_list_ressources_with_chantier_has_data(self, mock_check, mock_get_sb):
        """Vérifie que si le chantier a ses propres ressources, on les utilise."""
        mock_check.return_value = {"org_id": "org-1", "email": "test@test.com"}

        sb = MagicMock()

        def _table(name):
            t = MagicMock()
            if name == "chantier_ressources":
                # retour par chantier_id prioritaire
                t.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    {"id": "r1", "nom": "Dupont", "type": "homme", "org_id": "org-1", "chantier_id": "chantier-uuid"},
                ]
                # org-wide ne doit pas être appelé
                t.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            if name == "chantiers":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": "chantier-uuid"}
                ]
            return t
        sb.table.side_effect = _table
        mock_get_sb.return_value = sb

        class MockRequest:
            class _H:
                def get(self, k, d=None): return ""
            headers = _H()

        result = await list_ressources(MockRequest(), org_id="org-1", chantier_id="chantier-uuid")
        assert len(result) == 1
        assert result[0]["nom"] == "Dupont"

    @patch("app.api.chantiers.get_supabase")
    @patch("app.api.chantiers.check_user_org_access")
    async def test_list_ressources_type_filter(self, mock_check, mock_get_sb):
        """Vérifie le filtre par type de ressource."""
        mock_check.return_value = {"org_id": "org-1", "email": "test@test.com"}

        sb = MagicMock()
        def _table(name):
            t = MagicMock()
            if name == "chantier_ressources":
                # Premier appel (chantier_id) → vide → fallback
                select_chain = MagicMock()
                select_chain.eq.return_value.eq.return_value.order.return_value.eq.return_value.execute.return_value.data = []
                select_chain.eq.return_value.eq.return_value.order.return_value.eq.return_value.execute.return_value.data = []
                # Deuxième appel (org-wide) → data
                select_chain.eq.return_value.order.return_value.eq.return_value.execute.return_value.data = [
                    {"id": "r3", "nom": "Pelle", "type": "machine", "org_id": "org-1"},
                ]
                t.select.return_value = select_chain
            if name == "chantiers":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "chantier-uuid"}]
            return t
        sb.table.side_effect = _table
        mock_get_sb.return_value = sb

        class MockRequest:
            class _H:
                def get(self, k, d=None): return ""
            headers = _H()

        result = await list_ressources(MockRequest(), org_id="org-1", chantier_id="chantier-uuid", type_ressource="machine")
        assert len(result) == 1
        assert result[0]["type"] == "machine"
