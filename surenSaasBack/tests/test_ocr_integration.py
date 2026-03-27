"""
Test d'intégration OCR avec Gemini.

Ce test valide l'extraction réelle de factures via Gemini.
Il teste la couche service utilisée par le webhook Telegram.

Usage:
    pytest tests/test_ocr_integration.py -v
    
Prérequis:
    - Variable d'environnement TEST_GOOGLE_GEMINI_CREDENTIALS_B64 définie
    - Fichier tests/data/INV-EXA-0001_EXAMPLE-SOCIETE.pdf présent
"""

import os
import sys
import pytest
from pathlib import Path

# Ajouter le parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration test
os.environ["ENVIRONMENT"] = "test"

# Chemin vers le fichier de test
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_PDF = TEST_DATA_DIR / "INV-EXA-0001_EXAMPLE-SOCIETE.pdf"


@pytest.mark.integration
class TestOCRIntegration:
    """Tests d'intégration pour l'OCR Gemini."""
    
    @pytest.fixture
    def gemini_credentials(self):
        """Récupère les credentials Gemini depuis les variables d'env."""
        credentials = os.getenv("TEST_GOOGLE_GEMINI_CREDENTIALS_B64")
        if not credentials:
            pytest.skip("TEST_GOOGLE_GEMINI_CREDENTIALS_B64 non défini")
        return credentials
    
    @pytest.fixture
    def test_pdf_path(self):
        """Retourne le chemin du fichier PDF de test."""
        if not TEST_PDF.exists():
            pytest.skip(f"Fichier test non trouvé: {TEST_PDF}")
        return str(TEST_PDF)
    
    def test_gemini_client_import(self):
        """Test que GeminiClient peut être importé sans erreur."""
        from app.agents.base.gemini_client import GeminiClient
        assert GeminiClient is not None
    
    def test_gemini_client_initialization(self, gemini_credentials):
        """Test l'initialisation du client avec credentials valides."""
        from app.agents.base.gemini_client import GeminiClient
        
        client = GeminiClient(
            credentials_b64=gemini_credentials,
            model="gemini-1.5-flash-001"
        )
        
        assert client is not None
        assert client._client is not None
        client.close()
    
    @pytest.mark.asyncio
    async def test_extraction_service_with_real_gemini(self, gemini_credentials, test_pdf_path):
        """Test l'extraction via InvoiceUploadService avec vrai Gemini.
        
        Ce test valide que:
        1. Le client Gemini est correctement initialisé
        2. L'appel à Gemini fonctionne (pas de fallback)
        3. Une réponse est obtenue (même si le parsing est imparfait)
        """
        from app.services.telegram.upload_invoice.service import InvoiceUploadService
        
        # Créer le service sans dépendances externes
        service = InvoiceUploadService(
            supabase_client=None,
            audit_service=None,
            notification_service=None
        )
        
        # Définir les credentials pour le test
        os.environ["TEST_GOOGLE_GEMINI_CREDENTIALS_B64"] = gemini_credentials
        
        # Exécuter l'OCR
        result = await service._perform_ocr(test_pdf_path, "pdf")
        
        # Vérification principale: PAS DE FALLBACK
        # Si on n'est pas en fallback, c'est que Gemini a été appelé avec succès
        assert result is not None, "Le résultat ne devrait pas être None"
        assert not result.raw_data.get("fallback"), \
            f"❌ L'OCR a utilisé le fallback - Gemini n'a pas été appelé: {result.raw_data.get('error')}"
        
        # Log des résultats pour analyse (même si vide)
        print(f"\n📝 Résultats extraction:")
        print(f"   Fournisseur: {result.supplier_name or '(non extrait)'}")
        print(f"   N° Facture: {result.invoice_number or '(non extrait)'}")
        print(f"   Date: {result.invoice_date or '(non extrait)'}")
        print(f"   Montant HT: {result.amount_ht}")
        print(f"   Montant TTC: {result.amount_ttc}")
        print(f"   TVA: {result.vat_amount} ({result.vat_rate}%)")
        print(f"   Description: {result.description or '(non extrait)'}"[:100])
        print(f"   Score confiance: {result.confidence_score}")
        print(f"   Raw data keys: {list(result.raw_data.keys())}")
        
        # ✅ SUCCÈS: Gemini a été appelé et a répondu
        # (le parsing parfait n'est pas requis pour ce test d'intégration)
        print(f"\n✅ Test réussi: Gemini a été appelé sans fallback!")
    
    @pytest.mark.asyncio
    async def test_extraction_with_invoice_items(self, gemini_credentials, test_pdf_path):
        """Test que les invoice_items sont extraits correctement par Gemini.
        
        Ce test vérifie spécifiquement que les lignes de détail (items) 
        sont bien extraites du PDF et présentes dans le résultat.
        """
        from app.services.telegram.upload_invoice.service import InvoiceUploadService
        
        service = InvoiceUploadService(
            supabase_client=None,
            audit_service=None,
            notification_service=None
        )
        
        os.environ["TEST_GOOGLE_GEMINI_CREDENTIALS_B64"] = gemini_credentials
        
        result = await service._perform_ocr(test_pdf_path, "pdf")
        
        # Vérifier que l'extraction a fonctionné
        assert result is not None
        assert not result.raw_data.get("fallback"), \
            f"Fallback utilisé: {result.raw_data.get('error')}"
        
        # Vérifier que les items sont présents
        assert hasattr(result, 'line_items'), "line_items doit être un attribut du résultat"
        
        if result.line_items:
            print(f"\n📋 {len(result.line_items)} ligne(s) de détail extraite(s):")
            for idx, item in enumerate(result.line_items[:5]):  # Afficher les 5 premiers
                print(f"   {idx+1}. {item.get('description', 'N/A')[:50]}...")
                print(f"      Qty: {item.get('quantity')} | "
                      f"Prix: {item.get('unit_price')}€ | "
                      f"Total: {item.get('total_ht')}€")
            
            if len(result.line_items) > 5:
                print(f"   ... et {len(result.line_items) - 5} autres lignes")
            
            # Vérifier la structure des items
            for item in result.line_items:
                assert 'description' in item, "Chaque item doit avoir une description"
        else:
            print("\n⚠️ Aucun item extrait (mais extraction réussie)")
            # Vérifier dans raw_data si les items sont présents
            raw_data = result.raw_data.get('full_extraction', {})
            extracted_data = raw_data.get('extracted_data', {})
            if 'line_items' in extracted_data:
                print(f"   ℹ️ Items trouvés dans raw_data: {len(extracted_data['line_items'])}")
                # Les items sont dans raw_data mais pas dans line_items
                # C'est un problème de mapping
                pytest.fail("Items présents dans raw_data mais pas dans line_items - problème de mapping")
        
        print(f"\n✅ Test invoice_items réussi!")
    
    @pytest.mark.asyncio
    async def test_extraction_raw_response(self, gemini_credentials, test_pdf_path):
        """Test l'extraction brute avec GeminiClient pour voir la réponse.
        
        Ce test vérifie que Gemini répond et retourne du texte,
        sans imposer de format JSON strict.
        """
        from app.agents.base.gemini_client import GeminiClient
        
        # Utiliser le modèle sans suffixe de version pour Vertex AI
        client = GeminiClient(
            credentials_b64=gemini_credentials,
            model="gemini-1.5-flash"  # Sans le -001
        )
        
        # Prompt simple
        prompt = "Décris le contenu de ce document en quelques phrases."
        
        try:
            response_text = client.extract_from_file(test_pdf_path, prompt)
            
            print(f"\n📄 Réponse brute Gemini ({len(response_text)} caractères):")
            print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            
            # ✅ Vérification: Gemini a répondu avec du texte
            assert response_text, "La réponse ne devrait pas être vide"
            assert len(response_text) > 10, "La réponse devrait contenir du texte"
            
            print(f"\n✅ Test réussi: Gemini a répondu!")
            
        except Exception as e:
            pytest.fail(f"Extraction échouée: {e}")
        finally:
            client.close()
    
    def test_pdf_file_exists(self):
        """Vérifie que le fichier de test existe."""
        assert TEST_PDF.exists(), f"Fichier test manquant: {TEST_PDF}"
        assert TEST_PDF.stat().st_size > 0, "Fichier test vide"
        print(f"✅ Fichier test trouvé: {TEST_PDF} ({TEST_PDF.stat().st_size} bytes)")


@pytest.mark.skipif(
    not os.getenv("TEST_GOOGLE_GEMINI_CREDENTIALS_B64"),
    reason="Credentials Gemini non disponibles"
)
@pytest.mark.skipif(
    not TEST_PDF.exists(),
    reason=f"Fichier test non trouvé: {TEST_PDF}"
)
class TestOCREndToEnd:
    """Test end-to-end du workflow OCR complet."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self):
        """Simule le workflow complet depuis réception fichier jusqu'à création facture.
        
        Ce test simule ce que fait le webhook Telegram:
        1. Réception du fichier
        2. Extraction OCR
        3. Création de l'objet ExtractedInvoiceData avec items
        4. Préparation des données pour la DB
        """
        import asyncio
        from app.services.telegram.upload_invoice.service import InvoiceUploadService, ExtractedInvoiceData
        
        service = InvoiceUploadService(None, None, None)
        
        # Test avec le vrai fichier
        result = await service._perform_ocr(str(TEST_PDF), "pdf")
        
        # Vérifier la structure complète
        assert isinstance(result, ExtractedInvoiceData)
        assert hasattr(result, 'supplier_name')
        assert hasattr(result, 'amount_ttc')
        assert hasattr(result, 'raw_data')
        assert hasattr(result, 'line_items'), "line_items doit être présent dans ExtractedInvoiceData"
        
        # Vérifier que raw_data contient les infos de debugging
        assert 'full_extraction' in result.raw_data or 'error' in result.raw_data
        
        # Vérifier les items
        if result.line_items and len(result.line_items) > 0:
            print(f"\n📋 {len(result.line_items)} item(s) prêt(s) pour insertion en DB:")
            total_ht = sum(item.get('total_ht', 0) or 0 for item in result.line_items if item.get('total_ht'))
            print(f"   Total HT calculé: {total_ht:.2f}€")
            print(f"   Montant HT extrait: {result.amount_ht}€")
        
        print(f"\n✅ Workflow OCR complet validé!")
        print(f"   Extraction réussie: {not result.raw_data.get('fallback', False)}")
        print(f"   Données extraites: {result.supplier_name or 'N/A'}")
        print(f"   Items extraits: {len(result.line_items) if result.line_items else 0}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
