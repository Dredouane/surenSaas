#!/usr/bin/env python3
"""
Tests d'intégration AI — extracteur + validateur.

Mocke l'extracteur Gemini (WorkflowExtractor) mais utilise le vrai validateur Pydantic.
Valide que :
  - Les données extraites passent le validateur
  - Les données aberrantes sont détectées
  - Le fallback fonctionne
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai.extractor import extract_avancement, extract_and_refine_avancement, extract_operation, extract_depense
from app.services.ai.validators import (
    AvancementSchema,
    OperationSchema,
    DepenseSchema,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

MOCK_AVANCEMENT_VALID = {
    "description": "Enduit facade sur 50m2",
    "quantite": 50.0,
    "unite": "m2",
    "prix_unitaire": 25.0,
    "avancement_pourcentage": 80.0,
}

MOCK_AVANCEMENT_INVALID = {
    "description": "Test",
    "quantite": 50.0,
    "prix_unitaire": 25.0,
    "avancement_pourcentage": 150.0,
}

MOCK_OPERATION_VALID = {
    "description": "Pose de fenetres",
    "type": "pose_bso",
    "montant": 5000.0,
    "quantite": 10.0,
}

MOCK_DEPENSE_VALID = {
    "fournisseur": "SARL Batimat",
    "montant": 1500.0,
    "description": "Achat ciment",
    "categorie": "fournisseur",
}


# ---------------------------------------------------------------------------
# Tests unitaires : extracteur + validateur
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio


class TestExtractAndValidateAvancement:
    @patch("app.services.ai.extractor._get_extractor")
    @pytest.mark.asyncio
    async def test_extract_then_validate_valid(self, mock_get_extractor):
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = {"extracted_data": MOCK_AVANCEMENT_VALID, "_fallback": False}
        mock_get_extractor.return_value = mock_extractor

        result = await extract_and_refine_avancement("Enduit facade 50m2 25e/m2 80%")

        validation = AvancementSchema.validate(result)
        assert validation.is_valid is True
        assert result["montant_total"] == 1250.0
        assert result["avancement_montant"] == 1000.0

    @patch("app.services.ai.extractor._get_extractor")
    @pytest.mark.asyncio
    async def test_extract_then_validate_invalid(self, mock_get_extractor):
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = {"extracted_data": MOCK_AVANCEMENT_INVALID, "_fallback": False}
        mock_get_extractor.return_value = mock_extractor

        raw = await extract_and_refine_avancement("Test 150%")
        validation = AvancementSchema.validate(raw)
        assert validation.is_valid is False
        assert any("avancement_pourcentage" in e for e in validation.errors)

    @patch("app.services.ai.extractor._get_extractor")
    @pytest.mark.asyncio
    async def test_fallback_returns_raw(self, mock_get_extractor):
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = {"_fallback": True, "description": "Test fallback"}
        mock_get_extractor.return_value = mock_extractor

        result = await extract_and_refine_avancement("Test fallback")
        assert result.get("_fallback") is True


class TestExtractAndValidateOperation:
    @patch("app.services.ai.extractor._get_extractor")
    @pytest.mark.asyncio
    async def test_extract_then_validate_valid(self, mock_get_extractor):
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = {"extracted_data": MOCK_OPERATION_VALID, "_fallback": False}
        mock_get_extractor.return_value = mock_extractor

        result = await extract_operation("Pose de fenetres")
        extracted = result.get("extracted_data") or result
        validation = OperationSchema.validate(extracted)
        assert validation.is_valid is True

    @patch("app.services.ai.extractor._get_extractor")
    @pytest.mark.asyncio
    async def test_extract_invalid_type(self, mock_get_extractor):
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = {
            "extracted_data": {"description": "Test", "type": "informatique", "montant": 100.0},
            "_fallback": False,
        }
        mock_get_extractor.return_value = mock_extractor

        result = await extract_operation("Test")
        extracted = result.get("extracted_data") or result
        validation = OperationSchema.validate(extracted)
        assert validation.is_valid is False


class TestExtractAndValidateDepense:
    @patch("app.services.ai.extractor._get_extractor")
    @pytest.mark.asyncio
    async def test_extract_then_validate_valid(self, mock_get_extractor):
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = {"extracted_data": MOCK_DEPENSE_VALID, "_fallback": False}
        mock_get_extractor.return_value = mock_extractor

        result = await extract_depense("Achat ciment SARL Batimat 1500e")
        extracted = result.get("extracted_data") or result
        validation = DepenseSchema.validate(extracted)
        assert validation.is_valid is True

    @patch("app.services.ai.extractor._get_extractor")
    @pytest.mark.asyncio
    async def test_extract_negative_montant(self, mock_get_extractor):
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = {
            "extracted_data": {"fournisseur": "Test", "montant": -100.0, "description": "Test", "categorie": "fournisseur"},
            "_fallback": False,
        }
        mock_get_extractor.return_value = mock_extractor

        result = await extract_depense("Test -100e")
        extracted = result.get("extracted_data") or result
        validation = DepenseSchema.validate(extracted)
        assert validation.is_valid is False
