#!/usr/bin/env python3
"""
Tests pour les validateurs de sortie IA (guardrails).

Valide que les données extraites par Gemini sont conformes aux règles métier :
  - avancement_pourcentage entre 0 et 100
  - montant >= 0
  - prix_unitaire >= 0
  - types enum corrects
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai.validators import (
    AvancementSchema,
    OperationSchema,
    DepenseSchema,
    ValidationResult,
)


class TestAvancementSchema:
    def test_valid_avancement(self):
        data = {
            "description": "Enduit facade",
            "quantite": 50.0,
            "unite": "m2",
            "prix_unitaire": 25.0,
            "avancement_pourcentage": 80.0,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.sanitized_data["description"] == "Enduit facade"

    def test_avancement_over_100(self):
        data = {
            "description": "Enduit facade",
            "quantite": 50.0,
            "unite": "m2",
            "prix_unitaire": 25.0,
            "avancement_pourcentage": 150.0,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is False
        assert any("avancement_pourcentage" in e for e in result.errors)

    def test_avancement_negative_prix(self):
        data = {
            "description": "Enduit facade",
            "quantite": 50.0,
            "unite": "m2",
            "prix_unitaire": -25.0,
            "avancement_pourcentage": 80.0,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is False
        assert any("prix_unitaire" in e for e in result.errors)

    def test_avancement_negative_quantite(self):
        data = {
            "description": "Enduit facade",
            "quantite": -10.0,
            "unite": "m2",
            "prix_unitaire": 25.0,
            "avancement_pourcentage": 80.0,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is False

    def test_avancement_missing_description(self):
        data = {
            "quantite": 50.0,
            "prix_unitaire": 25.0,
            "avancement_pourcentage": 80.0,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is False

    def test_avancement_minimal_valid(self):
        data = {
            "description": "Travaux",
            "avancement_pourcentage": 0,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is True

    def test_avancement_null_values_accepted(self):
        data = {
            "description": "Travaux",
            "quantite": None,
            "prix_unitaire": None,
            "avancement_pourcentage": None,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is True

    def test_sanitized_data_rounds_percentage(self):
        data = {
            "description": "Test",
            "avancement_pourcentage": 99.999,
        }
        result = AvancementSchema.validate(data)
        assert result.is_valid is True
        assert result.sanitized_data["avancement_pourcentage"] == 100.0


class TestOperationSchema:
    def test_valid_operation(self):
        data = {
            "description": "Pose de fenetres",
            "type": "pose_bso",
            "montant": 5000.0,
            "quantite": 10.0,
            "unite": "u",
        }
        result = OperationSchema.validate(data)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_operation_invalid_type(self):
        data = {
            "description": "Pose",
            "type": "informatique",
            "montant": 100.0,
            "quantite": 1.0,
        }
        result = OperationSchema.validate(data)
        assert result.is_valid is False

    def test_operation_negative_montant(self):
        data = {
            "description": "Pose",
            "type": "demolition",
            "montant": -100.0,
            "quantite": 1.0,
        }
        result = OperationSchema.validate(data)
        assert result.is_valid is False

    def test_operation_minimal(self):
        data = {
            "description": "Pose",
            "type": "autre",
        }
        result = OperationSchema.validate(data)
        assert result.is_valid is True


class TestDepenseSchema:
    def test_valid_depense(self):
        data = {
            "fournisseur": "SARL Batimat",
            "montant": 1500.0,
            "description": "Achat ciment",
            "categorie": "fournisseur",
        }
        result = DepenseSchema.validate(data)
        assert result.is_valid is True

    def test_depense_invalid_categorie(self):
        data = {
            "fournisseur": "Test",
            "montant": 500.0,
            "description": "Test",
            "categorie": "client",
        }
        result = DepenseSchema.validate(data)
        assert result.is_valid is False

    def test_depense_negative_montant(self):
        data = {
            "fournisseur": "Test",
            "montant": -100.0,
            "description": "Test",
            "categorie": "sous_traitant",
        }
        result = DepenseSchema.validate(data)
        assert result.is_valid is False

    def test_depense_minimal(self):
        data = {
            "description": "Depense test",
            "categorie": "autre",
        }
        result = DepenseSchema.validate(data)
        assert result.is_valid is True


class TestValidationResult:
    def test_validation_result_creation(self):
        result = ValidationResult(is_valid=True, errors=[], sanitized_data={"key": "val"})
        assert result.is_valid is True
        assert result.sanitized_data["key"] == "val"

    def test_validation_result_failure(self):
        result = ValidationResult(is_valid=False, errors=["montant négatif"], sanitized_data={"key": "val"})
        assert result.is_valid is False
        assert "montant négatif" in result.errors

    def test_validation_result_passes_guardrail_check(self):
        result = ValidationResult(is_valid=False, errors=["error"], sanitized_data={"key": "val"})
        assert result.guardrail_issues == ["error"]
