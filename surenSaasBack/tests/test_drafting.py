"""
Tests du Drafting Sandbox.

Scénarios de test:
1. Génération de draft initial
2. Itération sur draft (Petit Prompt)
3. Application de Smart Chips
4. Fallback si Gemini échoue
"""

import pytest
import asyncio
from uuid import UUID

from app.services.drafting_service import DraftingService
from app.models.dossiers import (
    DraftGenerationRequest, DraftIterationRequest, DraftSmartChipAction
)


# Configuration
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"
TEST_THREAD_ID = None  # Sera défini dynamiquement


def get_test_org_id():
    """Récupère l'ID de test."""
    from app.api.auth import get_supabase
    supabase = get_supabase()
    org = supabase.table("organizations").select("id").eq("slug", TEST_ORG_SLUG).single().execute()
    return UUID(org.data["id"])


TEST_ORG_ID = get_test_org_id()


def get_existing_thread():
    """Récupère un thread existant pour les tests."""
    from app.api.auth import get_supabase
    supabase = get_supabase()
    
    thread = supabase.table("email_threads")\
        .select("id")\
        .eq("org_id", str(TEST_ORG_ID))\
        .limit(1)\
        .execute()
    
    if thread.data:
        return UUID(thread.data[0]["id"])
    return None


@pytest.fixture
def service():
    return DraftingService()


@pytest.fixture
def test_thread_id():
    """Fixture pour récupérer un thread de test."""
    thread_id = get_existing_thread()
    if not thread_id:
        pytest.skip("Pas de thread existant pour les tests")
    return thread_id


class TestDraftingService:
    """Tests du service Drafting."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow  # Appel réel à Gemini (~0.001€)
    async def test_generate_draft_basic(self, service, test_thread_id):
        """
        Scénario: Générer un draft basique.
        
        Given: Thread existant
        When: Appel generate_draft avec contexte minimal
        Then: Draft généré avec contenu HTML
        """
        print("\n🧪 Test génération draft (peut coûter ~0.001€)")
        
        request = DraftGenerationRequest(
            context_level="minimal",
            tone="professional"
        )
        
        draft = await service.generate_draft(
            thread_id=test_thread_id,
            org_id=TEST_ORG_ID,
            request=request
        )
        
        # Vérifications
        assert draft.draft_id.startswith("draft-")
        assert len(draft.content) > 0
        assert "<p>" in draft.content or "<div>" in draft.content  # HTML
        assert len(draft.plain_text) > 0
        assert len(draft.suggestions) > 0
        
        print(f"✅ Draft généré: {len(draft.content)} caractères")
        print(f"   Suggestions: {', '.join(draft.suggestions[:3])}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_generate_draft_with_full_context(self, service, test_thread_id):
        """
        Scénario: Générer un draft avec contexte complet.
        
        Given: Thread avec historique
        When: context_level="full"
        Then: Draft plus contextualisé
        """
        print("\n🧪 Test génération avec contexte complet")
        
        request = DraftGenerationRequest(
            context_level="full",
            tone="formal"
        )
        
        draft = await service.generate_draft(
            thread_id=test_thread_id,
            org_id=TEST_ORG_ID,
            request=request
        )
        
        assert draft.content is not None
        assert draft.model_used == "gemini-2.5-flash-lite"
        
        print(f"✅ Draft généré avec contexte complet")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_iterate_draft(self, service, test_thread_id):
        """
        Scénario: Itérer sur un draft (Petit Prompt).
        
        Given: Draft existant
        When: Instruction de modification
        Then: Draft modifié avec résumé des changements
        """
        print("\n🧪 Test itération draft (Petit Prompt)")
        
        # D'abord générer un draft
        initial = await service.generate_draft(
            thread_id=test_thread_id,
            org_id=TEST_ORG_ID,
            request=DraftGenerationRequest()
        )
        
        # Itérer
        iteration = await service.iterate_draft(
            DraftIterationRequest(
                current_content=initial.content,
                instruction="Rendre plus court et direct",
                action="iterate"
            )
        )
        
        assert iteration.content is not None
        # Le contenu devrait être différent (mais pas garanti)
        
        print(f"✅ Draft itéré")
        if iteration.changes_summary:
            print(f"   Changements: {iteration.changes_summary}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_apply_smart_chip_shorten(self, service, test_thread_id):
        """
        Scénario: Appliquer Smart Chip "Plus court".
        
        Given: Draft existant
        When: chip_id="shorten"
        Then: Draft raccourci
        """
        print("\n🧪 Test Smart Chip: Plus court")
        
        # Générer draft
        initial = await service.generate_draft(
            thread_id=test_thread_id,
            org_id=TEST_ORG_ID,
            request=DraftGenerationRequest()
        )
        
        initial_length = len(initial.content)
        
        # Appliquer chip
        result = await service.apply_smart_chip(
            DraftSmartChipAction(
                chip_id="shorten",
                current_content=initial.content
            )
        )
        
        assert result.content is not None
        # Le texte devrait être plus court (mais pas garanti avec l'IA)
        
        print(f"✅ Smart chip 'shorten' appliqué")
        print(f"   Avant: {initial_length} caractères")
        print(f"   Après: {len(result.content)} caractères")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_apply_smart_chip_formal(self, service, test_thread_id):
        """
        Scénario: Appliquer Smart Chip "Plus formel".
        
        Given: Draft existant
        When: chip_id="formal"
        Then: Draft plus formel
        """
        print("\n🧪 Test Smart Chip: Plus formel")
        
        initial = await service.generate_draft(
            thread_id=test_thread_id,
            org_id=TEST_ORG_ID,
            request=DraftGenerationRequest()
        )
        
        result = await service.apply_smart_chip(
            DraftSmartChipAction(
                chip_id="formal",
                current_content=initial.content
            )
        )
        
        assert result.content is not None
        
        print(f"✅ Smart chip 'formal' appliqué")
    
    def test_build_thread_context_minimal(self, service, test_thread_id):
        """
        Scénario: Construire contexte minimal.
        
        Given: Thread existant
        When: context_level="minimal"
        Then: Contexte basique sans emails
        """
        print("\n🧪 Test construction contexte minimal")
        
        context = asyncio.run(service._build_thread_context(
            thread_id=test_thread_id,
            org_id=TEST_ORG_ID,
            context_level="minimal"
        ))
        
        assert "thread_id" in context
        assert "subject" in context
        assert "participants" in context
        # Pas d'emails en mode minimal
        assert "emails" not in context
        
        print(f"✅ Contexte minimal construit")
    
    def test_build_thread_context_full(self, service, test_thread_id):
        """
        Scénario: Construire contexte complet.
        
        Given: Thread existant
        When: context_level="full"
        Then: Contexte avec emails et PJ
        """
        print("\n🧪 Test construction contexte complet")
        
        context = asyncio.run(service._build_thread_context(
            thread_id=test_thread_id,
            org_id=TEST_ORG_ID,
            context_level="full"
        ))
        
        assert "thread_id" in context
        assert "emails" in context or "error" in context
        
        if "emails" in context:
            print(f"✅ Contexte complet construit: {len(context['emails'])} email(s)")
        else:
            print(f"⚠️ Contexte: {context.get('error', 'Unknown')}")
    
    def test_html_to_text_conversion(self, service):
        """
        Scénario: Conversion HTML vers texte.
        
        Given: HTML avec paragraphes
        When: Appel _html_to_text
        Then: Texte brut formaté
        """
        print("\n🧪 Test conversion HTML vers texte")
        
        html = "<p>Bonjour,</p><p>Merci pour votre message.</p><p>Cordialement,</p>"
        text = service._html_to_text(html)
        
        assert "<p>" not in text
        assert "Bonjour" in text
        assert "Cordialement" in text
        
        print(f"✅ Conversion: {len(html)} chars HTML → {len(text)} chars texte")


# Markers
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.slow,  # Tous les tests font appel à Gemini
]
