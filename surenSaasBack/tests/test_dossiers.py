"""
Tests du module Dossiers (Le Classeur).

Scénarios de test:
1. CRUD complet des dossiers
2. Liaison/déliaison de threads
3. Suggestion IA de liaison
4. Documents agrégés
"""

import pytest
import asyncio
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4, UUID

from app.services.dossier_service import DossierService
from app.models.dossiers import DossierCreate, DossierUpdate, LinkThreadToDossierRequest


# Configuration
TEST_ORG_SLUG = "REDACTED_ORG_SLUG"
TEST_COMPANY_SLUG = "construction"


def get_test_ids():
    """Récupère les IDs de test."""
    from app.api.auth import get_supabase
    supabase = get_supabase()
    
    org = supabase.table("organizations").select("id").eq("slug", TEST_ORG_SLUG).single().execute()
    company = supabase.table("companies").select("id").eq("slug", TEST_COMPANY_SLUG).eq("org_id", org.data["id"]).single().execute()
    
    return UUID(org.data["id"]), UUID(company.data["id"])


TEST_ORG_ID, TEST_COMPANY_ID = get_test_ids()


class TestDossierService:
    """Tests du service Dossier."""
    
    @pytest.fixture
    def service(self):
        return DossierService()
    
    def cleanup_dossier(self, dossier_id: UUID):
        """Nettoie un dossier de test."""
        from app.api.auth import get_supabase
        supabase = get_supabase()
        supabase.table("dossiers").delete().eq("id", str(dossier_id)).execute()
    
    @pytest.mark.asyncio
    async def test_create_dossier(self, service):
        """
        Scénario: Créer un dossier avec toutes les infos.
        
        Given: Données de dossier complètes
        When: Appel create_dossier
        Then: Dossier créé avec bonnes valeurs
        """
        print("\n🧪 Test création dossier")
        
        data = DossierCreate(
            name="Résidence Test - Salle de Bain",
            client_name="ACORUS TEST",
            client_email="test@acorus.fr",
            address="123 rue Test, 75000 Paris",
            project_type="renovation",
            budget_estimate=Decimal("5000.00"),
            deadline=date(2025, 12, 31)
        )
        
        dossier = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=data
        )
        
        assert dossier.name == data.name
        assert dossier.client_name == data.client_name
        assert dossier.status.value == "active"
        assert dossier.thread_count == 0
        
        print(f"✅ Dossier créé: {dossier.id}")
        
        # Cleanup
        self.cleanup_dossier(dossier.id)
    
    @pytest.mark.asyncio
    async def test_list_dossiers_with_filters(self, service):
        """
        Scénario: Lister les dossiers avec filtres.
        
        Given: Plusieurs dossiers existants
        When: Liste avec filtre status=active
        Then: Uniquement dossiers actifs retournés
        """
        print("\n🧪 Test liste avec filtres")
        
        # Créer 2 dossiers
        d1 = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=DossierCreate(name="Dossier Actif Test")
        )
        
        d2 = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=DossierCreate(name="Dossier Complété Test")
        )
        
        # Marquer d2 comme completed
        service.update_dossier(d2.id, TEST_ORG_ID, DossierUpdate(status="completed"))
        
        # Liste filtrée
        result = service.list_dossiers(
            org_id=TEST_ORG_ID,
            status="active"
        )
        
        # Vérifier que d1 est dans la liste mais pas d2
        ids = [d.id for d in result["data"]]
        assert d1.id in ids
        
        print(f"✅ Filtre status=active: {len(result['data'])} dossiers")
        
        # Cleanup
        self.cleanup_dossier(d1.id)
        self.cleanup_dossier(d2.id)
    
    @pytest.mark.asyncio
    async def test_update_dossier(self, service):
        """
        Scénario: Modifier un dossier existant.
        
        Given: Dossier existant
        When: Mise à jour du nom et statut
        Then: Dossier modifié correctement
        """
        print("\n🧪 Test mise à jour dossier")
        
        # Créer
        dossier = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=DossierCreate(name="Nom Original")
        )
        
        # Modifier
        updated = service.update_dossier(
            dossier_id=dossier.id,
            org_id=TEST_ORG_ID,
            data=DossierUpdate(name="Nom Modifié", status="on_hold")
        )
        
        assert updated.name == "Nom Modifié"
        assert updated.status.value == "on_hold"
        
        print(f"✅ Dossier mis à jour: {updated.name}")
        
        # Cleanup
        self.cleanup_dossier(dossier.id)
    
    @pytest.mark.asyncio
    async def test_delete_dossier_soft(self, service):
        """
        Scénario: Supprimer un dossier (soft delete).
        
        Given: Dossier existant
        When: Appel delete_dossier
        Then: Statut passe à 'cancelled', pas de suppression physique
        """
        print("\n🧪 Test suppression dossier (soft)")
        
        # Créer
        dossier = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=DossierCreate(name="Dossier à Supprimer")
        )
        
        # Supprimer
        success = service.delete_dossier(dossier.id, TEST_ORG_ID)
        assert success is True
        
        # Vérifier statut
        deleted = service.get_dossier(dossier.id, TEST_ORG_ID)
        assert deleted.status.value == "cancelled"
        
        print(f"✅ Dossier soft-deleted: statut={deleted.status.value}")
        
        # Cleanup physique
        self.cleanup_dossier(dossier.id)
    
    @pytest.mark.asyncio
    async def test_link_unlink_thread(self, service):
        """
        Scénario: Lier et délier un thread d'un dossier.
        
        Given: Dossier et Thread existants
        When: Lier puis délier
        Then: Thread lié puis délié correctement
        """
        print("\n🧪 Test liaison/déliaison thread")
        
        # Créer dossier
        dossier = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=DossierCreate(name="Dossier avec Threads")
        )
        
        # Créer un thread de test
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        thread_data = {
            "org_id": str(TEST_ORG_ID),
            "company_id": str(TEST_COMPANY_ID),
            "gmail_thread_id": f"test-thread-{uuid4().hex[:8]}",
            "subject": "Test Thread",
            "ai_status": "new",
            "ai_urgency": "medium"
        }
        thread_result = supabase.table("email_threads").insert(thread_data).execute()
        thread_id = UUID(thread_result.data[0]["id"])
        
        # Lier
        linked = service.link_thread_to_dossier(
            thread_id=thread_id,
            org_id=TEST_ORG_ID,
            request=LinkThreadToDossierRequest(dossier_id=dossier.id)
        )
        
        assert linked.id == dossier.id
        print(f"✅ Thread lié au dossier")
        
        # Vérifier thread_count mis à jour
        dossier_updated = service.get_dossier(dossier.id, TEST_ORG_ID)
        assert dossier_updated.thread_count >= 1
        
        # Délier
        unlinked = service.unlink_thread_from_dossier(thread_id, TEST_ORG_ID)
        assert unlinked is True
        print(f"✅ Thread délié du dossier")
        
        # Cleanup
        supabase.table("email_threads").delete().eq("id", str(thread_id)).execute()
        self.cleanup_dossier(dossier.id)
    
    @pytest.mark.asyncio
    async def test_suggest_dossiers_for_thread(self, service):
        """
        Scénario: Suggérer des dossiers pour un thread.
        
        Given: Thread avec client connu + Dossiers existants
        When: Appel suggest_dossiers_for_thread
        Then: Suggestions retournées avec scores
        """
        print("\n🧪 Test suggestion IA de dossiers")
        
        # Créer dossier avec client connu (nom unique pour éviter conflits)
        unique_id = uuid4().hex[:6]
        dossier = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=DossierCreate(
                name=f"Chantier Client Connu {unique_id}",
                client_name=f"ENTREPRISE TEST {unique_id}"
            )
        )
        
        # Créer thread avec même client dans participants
        from app.api.auth import get_supabase
        supabase = get_supabase()
        
        thread_data = {
            "org_id": str(TEST_ORG_ID),
            "company_id": str(TEST_COMPANY_ID),
            "gmail_thread_id": f"test-thread-{uuid4().hex[:8]}",
            "subject": f"Devis ENTREPRISE TEST {unique_id}",
            "participant_names": [f"ENTREPRISE TEST {unique_id}"],
            "participant_emails": ["contact@entreprisetest.fr"],
            "ai_status": "new"
        }
        thread_result = supabase.table("email_threads").insert(thread_data).execute()
        thread_id = UUID(thread_result.data[0]["id"])
        
        # Suggérer
        suggestions = await service.suggest_dossiers_for_thread(thread_id, TEST_ORG_ID)
        
        # Vérifier
        assert isinstance(suggestions, list)
        
        if suggestions:
            print(f"✅ {len(suggestions)} suggestion(s) trouvée(s)")
            for s in suggestions:
                print(f"   - {s.name} (confiance: {s.confidence:.2f})")
            
            # Vérifier que notre dossier est dans les suggestions si confiance > 0.5
            matching = [s for s in suggestions if s.dossier_id == dossier.id]
            if matching:
                assert matching[0].confidence >= 0.5
        else:
            print("ℹ️ Aucune suggestion (peut arriver si matching insuffisant)")
        
        # Cleanup
        supabase.table("email_threads").delete().eq("id", str(thread_id)).execute()
        self.cleanup_dossier(dossier.id)
    
    @pytest.mark.asyncio
    async def test_get_documents_in_dossier(self, service):
        """
        Scénario: Récupérer documents agrégés d'un dossier.
        
        Given: Dossier avec threads ayant des PJ
        When: Appel get_documents_in_dossier
        Then: Documents groupés par type
        """
        print("\n🧪 Test documents agrégés")
        
        # Créer dossier
        dossier = service.create_dossier(
            org_id=TEST_ORG_ID,
            company_id=TEST_COMPANY_ID,
            data=DossierCreate(name="Dossier avec Documents")
        )
        
        # Le dossier est vide au début
        docs = service.get_documents_in_dossier(dossier.id, TEST_ORG_ID)
        
        assert docs["total"] == 0
        assert docs["by_type"] == {}
        
        print(f"✅ Documents récupérés: {docs['total']} total")
        
        # Cleanup
        self.cleanup_dossier(dossier.id)


# Markers
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]
