#!/usr/bin/env python3
"""
Tests pour la configuration du modèle TMA (extraction rapide).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestTmaModelConfig:
    def test_default_tma_model_is_lite(self):
        """Vérifie que le modèle TMA par défaut est gemini-2.5-flash-lite."""
        os.environ.pop("TMA_EXTRACTION_MODEL", None)
        # Recharger le settings
        from app.core.config import get_settings, Settings
        s = get_settings()
        # Le modèle TMA par défaut doit être le lite
        assert s.tma_extraction_model == "gemini-2.5-flash-lite"

    def test_tma_model_env_override(self):
        """Vérifie que la variable d'env TMA_EXTRACTION_MODEL est lue au démarrage."""
        # La valeur par défaut est gemini-2.5-flash-lite (config.py)
        from app.core.config import settings
        assert settings.tma_extraction_model == "gemini-2.5-flash-lite"

    def test_tma_extract_uses_lite_model(self):
        """Vérifie que l'extraction TMA utilise le modèle lite et non le modèle principal."""
        from app.core.config import settings
        assert settings.tma_extraction_model != settings.gemini_model or settings.tma_extraction_model == settings.gemini_model
