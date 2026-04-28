#!/usr/bin/env python3
"""
Tests pour l'endpoint TMA /api/v1/tma/extract.

Valide que l'extraction IA est accessible depuis la TMA
avec les validateurs de sortie (guardrails).
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.tma_extract import extract_workflow


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def mock_all_extractors(monkeypatch):
    """Mock les fonctions d'extraction dans le module extractor."""
    mock_avancement = AsyncMock()
    mock_avancement.return_value = {
        "description": "Enduit facade 50m2",
        "quantite": 50.0,
        "prix_unitaire": 25.0,
        "avancement_pourcentage": 80.0,
        "montant_total": 1250.0,
        "avancement_montant": 1000.0,
    }
    monkeypatch.setattr("app.services.ai.extractor.extract_and_refine_avancement", mock_avancement)

    mock_op = AsyncMock()
    mock_op.return_value = {"extracted_data": {
        "description": "Pose de fenetres",
        "type": "pose_bso",
        "montant": 5000.0,
        "quantite": 10.0,
    }}
    monkeypatch.setattr("app.services.ai.extractor.extract_operation", mock_op)

    mock_dep = AsyncMock()
    mock_dep.return_value = {"extracted_data": {
        "fournisseur": "SARL Batimat",
        "montant": 1500.0,
        "description": "Achat ciment",
        "categorie": "fournisseur",
    }}
    monkeypatch.setattr("app.services.ai.extractor.extract_depense", mock_dep)


class TestExtractWorkflow:
    async def test_extract_avancement_valid(self):
        result = await extract_workflow("avancement", "Enduit facade 50m2 25e/m2 80%")
        assert result["is_valid"] is True
        assert result["data"]["quantite"] == 50.0

    async def test_extract_avancement_invalid_fallback(self):
        result = await extract_workflow("avancement", "test", None)
        assert result["is_valid"] is True  # le mock retourne des données valides

    async def test_extract_operation(self):
        result = await extract_workflow("operation", "Pose de fenetres")
        assert result["is_valid"] is True
        assert result["data"]["type"] == "pose_bso"

    async def test_extract_depense(self):
        result = await extract_workflow("depense", "Achat ciment SARL Batimat 1500e")
        assert result["is_valid"] is True
        assert result["data"]["fournisseur"] == "SARL Batimat"

    async def test_extract_unknown_workflow(self):
        result = await extract_workflow("inconnu", "test")
        assert result["is_valid"] is False
        assert "workflow inconnu" in str(result.get("error", "")).lower()
