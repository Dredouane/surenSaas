"""
Validateurs Pydantic pour les sorties IA (guardrails).

Chaque schéma définit les règles métier :
  - avancement_pourcentage : 0-100
  - montant, prix_unitaire, quantite : >= 0
  - types enum valides
"""

from typing import Optional, List
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# ValidationResult — structure de retour pour tous les validateurs
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    sanitized_data: dict = field(default_factory=dict)

    @property
    def guardrail_issues(self) -> List[str]:
        return self.errors


# ---------------------------------------------------------------------------
# Schémas métier
# ---------------------------------------------------------------------------

class AvancementPydantic(BaseModel):
    description: str = Field(..., min_length=1)
    quantite: Optional[float] = Field(default=None, ge=0)
    unite: Optional[str] = None
    prix_unitaire: Optional[float] = Field(default=None, ge=0)
    avancement_pourcentage: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator("avancement_pourcentage")
    @classmethod
    def round_percentage(cls, v):
        if v is not None:
            return round(min(v, 100.0))
        return v


OPERATION_TYPES = {"demolition", "nettoyage", "pose_bso", "commande", "achat_materiel", "sous_traitance", "autre"}


class OperationPydantic(BaseModel):
    description: str = Field(..., min_length=1)
    type: str = Field(...)
    montant: Optional[float] = Field(default=None, ge=0)
    quantite: Optional[float] = Field(default=None, ge=0)
    unite: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in OPERATION_TYPES:
            raise ValueError(f"Type invalide: {v}. Choisir parmi {OPERATION_TYPES}")
        return v


DEPENSE_CATEGORIES = {"sous_traitant", "fournisseur", "autre"}


class DepensePydantic(BaseModel):
    fournisseur: Optional[str] = None
    montant: Optional[float] = Field(default=None, ge=0)
    description: str = Field(..., min_length=1)
    categorie: str = Field(...)

    @field_validator("categorie")
    @classmethod
    def validate_categorie(cls, v):
        if v not in DEPENSE_CATEGORIES:
            raise ValueError(f"Catégorie invalide: {v}. Choisir parmi {DEPENSE_CATEGORIES}")
        return v


# ---------------------------------------------------------------------------
# Validateurs avec interface unifiée
# ---------------------------------------------------------------------------

class AvancementSchema:
    @staticmethod
    def validate(data: dict) -> ValidationResult:
        errors = []
        sanitized = dict(data)
        try:
            obj = AvancementPydantic(**data)
            sanitized = obj.model_dump()
        except Exception as e:
            errors.extend(_extract_errors(e))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, sanitized_data=sanitized)


class OperationSchema:
    @staticmethod
    def validate(data: dict) -> ValidationResult:
        errors = []
        sanitized = dict(data)
        try:
            obj = OperationPydantic(**data)
            sanitized = obj.model_dump()
        except Exception as e:
            errors.extend(_extract_errors(e))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, sanitized_data=sanitized)


class DepenseSchema:
    @staticmethod
    def validate(data: dict) -> ValidationResult:
        errors = []
        sanitized = dict(data)
        try:
            obj = DepensePydantic(**data)
            sanitized = obj.model_dump()
        except Exception as e:
            errors.extend(_extract_errors(e))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, sanitized_data=sanitized)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_errors(exception: Exception) -> List[str]:
    msg = str(exception)
    try:
        from pydantic import ValidationError
        if isinstance(exception, ValidationError):
            return [f"{e['loc'][0]}: {e['msg']}" for e in exception.errors()]
    except ImportError:
        pass
    return [msg]
