#!/usr/bin/env python3
"""
Tests unitaires pour l'agent d'extraction Gemini.

Ces tests couvrent :
1. Client Gemini (connexion, extraction)
2. File Processor (téléchargement, optimisation)
3. Extracteur générique (extraction complète)
4. Conversion des données

Note: Ces tests utilisent des mocks pour éviter les appels API réels.
"""

import sys
import os
import json
import base64
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration test
os.environ["ENVIRONMENT"] = "test"
os.environ["TEST_GOOGLE_GEMINI_CREDENTIALS_B64"] = base64.b64encode(b"test_api_key").decode()


# ==================== FIXTURES ====================

@pytest.fixture
def sample_invoice_response():
    """Réponse JSON type d'une facture."""
    return {
        "document_type": "invoice",
        "extracted_data": {
            "supplier": {
                "name": "Matériaux Pro SARL",
                "address": "45 Rue des Fournisseurs, 75001 Paris",
                "siret": "12345678901234"
            },
            "invoice": {
                "number": "FAC-2024-001",
                "date": "2024-01-15",
                "due_date": "2024-02-15"
            },
            "amounts": {
                "ht": 1000.00,
                "ttc": 1200.00,
                "vat": 200.00,
                "vat_rate": 20.0
            },
            "line_items": [
                {
                    "description": "Ciment sac 35kg",
                    "quantity": 10,
                    "unit_price": 50.00,
                    "total_ht": 500.00,
                    "vat_rate": 20.0
                },
                {
                    "description": "Sable fin m3",
                    "quantity": 2,
                    "unit_price": 250.00,
                    "total_ht": 500.00,
                    "vat_rate": 20.0
                }
            ]
        },
        "metadata": {
            "confidence": "high",
            "pages_count": 1,
            "issues": []
        }
    }


@pytest.fixture
def mock_gemini_response():
    """Mock de réponse Gemini."""
    mock = Mock()
    mock.text = json.dumps({
        "document_type": "invoice",
        "extracted_data": {
            "supplier": {"name": "Test Supplier"},
            "amounts": {"ht": 100, "ttc": 120, "vat": 20}
        },
        "metadata": {"confidence": "high"}
    })
    return mock


# ==================== TESTS CLIENT GEMINI ====================

class TestGeminiClient:
    """Tests pour le client Gemini."""
    
    def test_client_initialization(self):
        """Test 1: Initialisation du client avec clé API."""
        from app.agents.base.gemini_client import GeminiClient
        
        client = GeminiClient(api_key="test_key", model="gemini-1.5-flash")
        
        assert client.api_key == "test_key"
        assert client.model_name == "gemini-1.5-flash"
        assert client.temperature == 0.1
    
    def test_client_initialization_with_base64_key(self):
        """Test 1a: Initialisation avec clé encodée en base64."""
        from app.agents.base.gemini_client import GeminiClient
        
        encoded_key = base64.b64encode(b"my_secret_key").decode()
        client = GeminiClient(api_key=encoded_key)
        
        assert client.api_key == "my_secret_key"
    
    def test_client_initialization_without_key_raises_error(self):
        """Test 1b: Erreur si pas de clé API."""
        from app.agents.base.gemini_client import GeminiClient
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GeminiClient()
            
            assert "Clé API Gemini non trouvée" in str(exc_info.value)
    
    def test_get_mime_type(self):
        """Test 1c: Détection type MIME depuis extension."""
        from app.agents.base.gemini_client import GeminiClient
        
        client = GeminiClient(api_key="test")
        
        assert client._get_mime_type(".pdf") == "application/pdf"
        assert client._get_mime_type(".jpg") == "image/jpeg"
        assert client._get_mime_type(".png") == "image/png"
        assert client._get_mime_type(".unknown") == "application/octet-stream"


# ==================== TESTS FILE PROCESSOR ====================

class TestFileProcessor:
    """Tests pour le processeur de fichiers."""
    
    @pytest.mark.asyncio
    async def test_download_from_url(self):
        """Test 2: Téléchargement depuis URL."""
        from app.agents.processors import FileProcessor
        
        processor = FileProcessor()
        
        # Mock la réponse HTTP
        mock_response = Mock()
        mock_response.content = b"PDF content here"
        mock_response.raise_for_status = Mock()
        
        with patch.object(processor.client, 'get', return_value=mock_response):
            data = await processor.download_from_url("https://example.com/facture.pdf")
            
            assert data == b"PDF content here"
        
        await processor.close()
    
    @pytest.mark.asyncio
    async def test_download_large_file_raises_error(self):
        """Test 2a: Erreur si fichier trop gros."""
        from app.agents.processors import FileProcessor
        
        processor = FileProcessor()
        processor.MAX_FILE_SIZE = 100  # 100 bytes pour le test
        
        mock_response = Mock()
        mock_response.content = b"x" * 200  # 200 bytes
        mock_response.raise_for_status = Mock()
        
        with patch.object(processor.client, 'get', return_value=mock_response):
            with pytest.raises(ValueError) as exc_info:
                await processor.download_from_url("https://example.com/huge.pdf")
            
            assert "trop gros" in str(exc_info.value)
        
        await processor.close()
    
    def test_encode_decode_base64(self):
        """Test 2b: Encodage/décodage base64."""
        from app.agents.processors import FileProcessor
        
        processor = FileProcessor()
        original = b"Hello World"
        
        encoded = processor.encode_base64(original)
        decoded = processor.decode_base64(encoded)
        
        assert isinstance(encoded, str)
        assert decoded == original
    
    def test_validate_file(self):
        """Test 2c: Validation de fichier."""
        from app.agents.processors import FileProcessor
        
        processor = FileProcessor()
        
        # Créer un fichier temporaire
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"test")
            temp_path = f.name
        
        try:
            is_valid, message, mime_type = processor.validate_file(temp_path)
            
            assert is_valid is True
            assert message == "OK"
            assert mime_type == "application/pdf"
        finally:
            os.unlink(temp_path)
    
    def test_validate_nonexistent_file(self):
        """Test 2d: Validation fichier inexistant."""
        from app.agents.processors import FileProcessor
        
        processor = FileProcessor()
        
        is_valid, message, mime_type = processor.validate_file("/nonexistent/file.pdf")
        
        assert is_valid is False
        assert "non trouvé" in message


# ==================== TESTS EXTRACTEUR GÉNÉRIQUE ====================

class TestGenericExtractor:
    """Tests pour l'extracteur générique."""
    
    @pytest.mark.asyncio
    async def test_extract_invoice(self, sample_invoice_response, mock_gemini_response):
        """Test 3: Extraction complète d'une facture."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        
        # Mock le client Gemini
        with patch('app.agents.generic_extractor.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.model_name = "gemini-1.5-flash"
            mock_client.extract_from_pdf.return_value = json.dumps(sample_invoice_response)
            mock_client_class.return_value = mock_client
            
            # Mock le file processor
            with patch('app.agents.generic_extractor.FileProcessor') as mock_processor_class:
                mock_processor = AsyncMock()
                mock_processor.prepare_for_extraction.return_value = (b"pdf_data", "application/pdf")
                mock_processor.close = AsyncMock()
                mock_processor_class.return_value = mock_processor
                
                extractor = GenericDocumentExtractor(document_type="invoice")
                result = await extractor.extract("facture.pdf")
                
                assert result.status.value == "success"
                assert result.document_type == "invoice"
                assert "extracted_data" in result.raw_data
                assert result.raw_data["extracted_data"]["supplier"]["name"] == "Matériaux Pro SARL"
    
    @pytest.mark.asyncio
    async def test_extract_invoice_multi_page(self, sample_invoice_response):
        """Test 3b: Extraction d'une facture multi-pages."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        
        # Mock le client Gemini
        with patch('app.agents.generic_extractor.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.model_name = "gemini-1.5-flash"
            mock_client.extract_from_pdf_pages.return_value = [
                {
                    "page_number": 1,
                    "response_text": json.dumps(sample_invoice_response),
                    "status": "success"
                },
                {
                    "page_number": 2,
                    "response_text": json.dumps({
                        "document_type": "invoice",
                        "extracted_data": {
                            "additional_info": {
                                "notes": "Page 2 notes",
                                "terms": "Payment terms"
                            }
                        },
                        "metadata": {"confidence": "high"}
                    }),
                    "status": "success"
                }
            ]
            mock_client_class.return_value = mock_client
            
            # Mock le file processor
            with patch('app.agents.generic_extractor.FileProcessor') as mock_processor_class:
                mock_processor = AsyncMock()
                mock_processor.prepare_for_extraction.return_value = (b"pdf_data", "application/pdf")
                mock_processor.close = AsyncMock()
                mock_processor_class.return_value = mock_processor
                
                # Test avec extraction par pages
                extractor = GenericDocumentExtractor(
                    document_type="invoice",
                    extract_by_pages=True,
                    page_range=(1, 2)
                )
                result = await extractor.extract("facture_multi.pdf")
                
                assert result.status.value == "success"
                assert result.document_type == "invoice"
                assert len(result.page_results) == 2
                assert result.pages_extracted == 2
                assert result.pages_failed == 0
                assert result.page_range_extracted == "1-2"
                
                # Vérifier les données consolidées
                assert "extracted_data" in result.raw_data
                assert "additional_info" in result.raw_data["extracted_data"]
    
    @pytest.mark.asyncio
    async def test_extract_invoice_multi_page_with_fallback(self):
        """Test 3c: Extraction multi-pages avec fallback sur erreur."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        
        # Mock le client Gemini
        with patch('app.agents.generic_extractor.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.model_name = "gemini-1.5-flash"
            mock_client.extract_from_pdf_pages.return_value = [
                {
                    "page_number": 1,
                    "response_text": json.dumps({
                        "document_type": "invoice",
                        "extracted_data": {"supplier": {"name": "Test"}},
                        "metadata": {"confidence": "high"}
                    }),
                    "status": "success"
                },
                {
                    "page_number": 2,
                    "response_text": "",
                    "status": "error",
                    "error": "API error"
                }
            ]
            mock_client_class.return_value = mock_client
            
            # Mock le file processor
            with patch('app.agents.generic_extractor.FileProcessor') as mock_processor_class:
                mock_processor = AsyncMock()
                mock_processor.prepare_for_extraction.return_value = (b"pdf_data", "application/pdf")
                mock_processor.close = AsyncMock()
                mock_processor_class.return_value = mock_processor
                
                # Test avec fallback activé
                extractor = GenericDocumentExtractor(
                    document_type="invoice",
                    extract_by_pages=True,
                    fallback_on_page_error=True
                )
                result = await extractor.extract("facture_error.pdf")
                
                assert result.status.value == "success"  # Global success malgré une page en erreur
                assert len(result.page_results) == 2
                assert result.pages_extracted == 1
                assert result.pages_failed == 1
                
                # Vérifier que la page 1 a réussi
                page1 = result.get_page_data(1)
                assert page1 is not None
                assert page1.get("extracted_data", {}).get("supplier", {}).get("name") == "Test"
    
    @pytest.mark.asyncio
    async def test_extraction_with_error(self):
        """Test 3a: Gestion des erreurs d'extraction."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        
        with patch('app.agents.generic_extractor.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.extract_from_pdf.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client
            
            with patch('app.agents.generic_extractor.FileProcessor') as mock_processor_class:
                mock_processor = AsyncMock()
                mock_processor.prepare_for_extraction.return_value = (b"pdf", "application/pdf")
                mock_processor.close = AsyncMock()
                mock_processor_class.return_value = mock_processor
                
                extractor = GenericDocumentExtractor(document_type="invoice")
                result = await extractor.extract("facture.pdf")
                
                assert result.status.value == "error"
                assert len(result.errors) > 0
                assert "API Error" in result.errors[0]
    
    def test_parse_response_json(self):
        """Test 3b: Parsing réponse JSON."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        
        extractor = GenericDocumentExtractor(document_type="invoice")
        
        # Test avec markdown
        response = "```json\n{\"key\": \"value\"}\n```"
        result = extractor._parse_response(response)
        
        assert result == {"key": "value"}
    
    def test_parse_response_invalid_json(self):
        """Test 3c: Gestion réponse non-JSON."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        
        extractor = GenericDocumentExtractor(document_type="invoice")
        
        response = "Texte simple sans JSON"
        result = extractor._parse_response(response)
        
        assert "raw_text" in result
        assert result["raw_text"] == response
    
    def test_validate_extraction_invoice(self):
        """Test 3d: Validation des données facture."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        from app.agents.models import ExtractionResult, ExtractionStatus
        
        extractor = GenericDocumentExtractor(document_type="invoice")
        
        # Données avec TVA cohérente
        result = ExtractionResult(
            document_type="invoice",
            extraction_timestamp=datetime.now(),
            source_file="test.pdf",
            model_used="gemini",
            raw_data={
                "extracted_data": {
                    "amounts": {"ht": 100, "ttc": 120, "vat": 20},
                    "supplier": {"name": "Test"}
                }
            },
            status=ExtractionStatus.SUCCESS
        )
        
        validation = extractor.validate_extraction(result)
        
        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
    
    def test_validate_extraction_with_vat_error(self):
        """Test 3e: Détection incohérence TVA."""
        from app.agents.generic_extractor import GenericDocumentExtractor
        from app.agents.models import ExtractionResult, ExtractionStatus
        
        extractor = GenericDocumentExtractor(document_type="invoice")
        
        # Données avec TVA incohérente (100 + 20 ≠ 150)
        result = ExtractionResult(
            document_type="invoice",
            extraction_timestamp=datetime.now(),
            source_file="test.pdf",
            model_used="gemini",
            raw_data={
                "extracted_data": {
                    "amounts": {"ht": 100, "ttc": 150, "vat": 20},
                    "supplier": {"name": "Test"}
                }
            },
            status=ExtractionStatus.SUCCESS
        )
        
        validation = extractor.validate_extraction(result)
        
        assert len(validation["warnings"]) > 0
        assert "Incohérence TVA" in validation["warnings"][0]


# ==================== TESTS CONSTRUCTION INVOICE AGENT ====================

class TestConstructionInvoiceAgent:
    """Tests pour l'agent factures construction."""
    
    @pytest.mark.asyncio
    async def test_extract_and_convert(self, sample_invoice_response):
        """Test 4: Extraction et conversion vers format Invoice."""
        from app.agents.construction_invoice_agent import ConstructionInvoiceAgent
        
        agent = ConstructionInvoiceAgent()
        
        # Mock l'extracteur
        with patch.object(agent.extractor, 'extract', new_callable=AsyncMock) as mock_extract:
            from app.agents.models import ExtractionResult, ExtractionStatus
            
            mock_extract.return_value = ExtractionResult(
                document_type="invoice",
                extraction_timestamp=datetime.now(),
                source_file="test.pdf",
                model_used="gemini",
                raw_data=sample_invoice_response,
                status=ExtractionStatus.SUCCESS
            )
            
            result = await agent.extract_from_document("test.pdf", "pdf")
            
            assert result.supplier_name == "Matériaux Pro SARL"
            assert result.amount_ttc == 1200.00
            assert result.amount_ht == 1000.00
            assert len(result.line_items) == 2
            assert result.extraction_method == "gemini_flash"
    
    @pytest.mark.asyncio
    async def test_validate_invoice_data(self):
        """Test 4a: Validation des données facture."""
        from app.agents.construction_invoice_agent import ConstructionInvoiceAgent, ExtractedInvoiceData
        
        agent = ConstructionInvoiceAgent()
        
        # Données valides
        data = ExtractedInvoiceData(
            supplier_name="Test",
            amount_ttc=120,
            amount_ht=100,
            vat_amount=20,
            invoice_date="2024-01-15"
        )
        
        validation = await agent.validate_extraction(data)
        
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_invoice_with_errors(self):
        """Test 4b: Détection erreurs validation."""
        from app.agents.construction_invoice_agent import ConstructionInvoiceAgent, ExtractedInvoiceData
        
        agent = ConstructionInvoiceAgent()
        
        # Données invalides
        data = ExtractedInvoiceData(
            supplier_name="",
            amount_ttc=-100,
            amount_ht=100,
            vat_amount=20
        )
        
        validation = await agent.validate_extraction(data)
        
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        assert any("fournisseur" in e.lower() for e in validation["errors"])
        assert any("TTC" in e for e in validation["errors"])


# ==================== TESTS NOUVEAUX MODÈLES ====================

class TestMultiPageModels:
    """Tests pour les nouveaux modèles multi-pages."""
    
    def test_page_extraction_result(self):
        """Test 6: Création PageExtractionResult."""
        from app.agents.models import PageExtractionResult, PageExtractionStatus
        
        page_result = PageExtractionResult(
            page_number=1,
            extracted_data={"key": "value"},
            status=PageExtractionStatus.SUCCESS,
            confidence=0.9,
            errors=[],
            warnings=["warning1"]
        )
        
        assert page_result.page_number == 1
        assert page_result.extracted_data["key"] == "value"
        assert page_result.status == PageExtractionStatus.SUCCESS
        assert page_result.confidence == 0.9
        assert len(page_result.warnings) == 1
        
        # Test conversion en dict
        page_dict = page_result.to_dict()
        assert page_dict["page_number"] == 1
        assert page_dict["status"] == "success"
    
    def test_extraction_result_multi_page(self):
        """Test 6a: ExtractionResult avec données multi-pages."""
        from app.agents.models import ExtractionResult, ExtractionStatus, PageExtractionResult, PageExtractionStatus
        from datetime import datetime
        
        page_results = [
            PageExtractionResult(
                page_number=1,
                extracted_data={"supplier": "Test1"},
                status=PageExtractionStatus.SUCCESS,
                confidence=0.8
            ),
            PageExtractionResult(
                page_number=2,
                extracted_data={"amount": 100},
                status=PageExtractionStatus.SUCCESS,
                confidence=0.9
            )
        ]
        
        result = ExtractionResult(
            document_type="invoice",
            extraction_timestamp=datetime.now(),
            source_file="test.pdf",
            model_used="gemini",
            raw_data={"extracted_data": {"consolidated": "data"}},
            page_results=page_results,
            pages_processed=2,
            pages_extracted=2,
            pages_failed=0,
            page_range_extracted="1-2"
        )
        
        assert result.document_type == "invoice"
        assert len(result.page_results) == 2
        assert result.pages_extracted == 2
        assert result.pages_failed == 0
        assert result.page_range_extracted == "1-2"
        
        # Test méthodes utilitaires
        successful_pages = result.get_successful_pages()
        assert len(successful_pages) == 2
        
        page1_data = result.get_page_data(1)
        assert page1_data["supplier"] == "Test1"
        
        page_confidence = result.get_page_confidence_score()
        assert 0.8 <= page_confidence <= 0.9
        
        # Test conversion en dict
        result_dict = result.to_dict()
        assert result_dict["pages_extracted"] == 2
        assert "page_results" in result_dict
        assert len(result_dict["page_results"]) == 2


# ==================== TESTS HELPERS ====================

class TestExtractorHelpers:
    """Tests pour les fonctions helper."""
    
    def test_create_invoice_extractor(self):
        """Test 5: Création extracteur factures."""
        from app.agents.generic_extractor import create_invoice_extractor
        
        extractor = create_invoice_extractor()
        
        assert extractor.document_type == "invoice"
    
    def test_create_invoice_extractor_multi_page(self):
        """Test 5b: Création extracteur factures multi-pages."""
        from app.agents.generic_extractor import create_invoice_extractor
        
        extractor = create_invoice_extractor(
            page_range=(1, 3),
            extract_by_pages=True,
            max_pages=5,
            fallback_on_page_error=True
        )
        
        assert extractor.document_type == "invoice"
        assert extractor.page_range == (1, 3)
        assert extractor.extract_by_pages is True
        assert extractor.max_pages == 5
        assert extractor.fallback_on_page_error is True
    
    def test_create_receipt_extractor(self):
        """Test 5a: Création extracteur tickets."""
        from app.agents.generic_extractor import create_receipt_extractor
        
        extractor = create_receipt_extractor()
        
        assert extractor.document_type == "receipt"
    
    def test_create_custom_extractor(self):
        """Test 5c: Création extracteur personnalisé."""
        from app.agents.generic_extractor import create_custom_extractor
        
        extractor = create_custom_extractor(
            document_type="delivery_note",
            fields={
                "order_number": "Numéro commande",
                "items": "Articles"
            },
            instructions="Extrais aussi le transporteur"
        )
        
        assert extractor.document_type == "delivery_note"
        assert "delivery_note" in extractor.system_prompt
    
    def test_create_custom_extractor_multi_page(self):
        """Test 5d: Création extracteur personnalisé multi-pages."""
        from app.agents.generic_extractor import create_custom_extractor
        
        extractor = create_custom_extractor(
            document_type="report",
            fields={"title": "Titre", "sections": "Sections"},
            instructions="Analyse complète",
            extract_by_pages=True,
            page_range=(1, 10)
        )
        
        assert extractor.document_type == "report"
        assert extractor.extract_by_pages is True
        assert extractor.page_range == (1, 10)


# ==================== EXÉCUTION ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
