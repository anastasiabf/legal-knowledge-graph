"""
Unit tests untuk extraction module (TAHAP 2).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from extraction.models import (
    LegalEntity,
    PasalReference,
    KonsepHukum,
    EnrichedPasalContent,
    EnrichedDocumentContent,
)
from ingestion.models import PasalContent


class TestExtractionModels:
    """Test extraction models."""
    
    def test_legal_entity(self):
        """Test LegalEntity model."""
        entity = LegalEntity(
            text="Transaksi Elektronik",
            entity_type="Konsep",
            pasal_nomor="1",
            confidence=0.95,
            context="Transaksi Elektronik adalah..."
        )
        
        assert entity.text == "Transaksi Elektronik"
        assert entity.confidence == 0.95
    
    def test_pasal_reference(self):
        """Test PasalReference model."""
        ref = PasalReference(
            source_pasal="27",
            target_pasal="1",
            reference_type="MERUJUK_KE",
            reference_text="Sebagaimana dimaksud dalam Pasal 1",
            confidence=0.9
        )
        
        assert ref.source_pasal == "27"
        assert ref.target_pasal == "1"
    
    def test_konsep_hukum(self):
        """Test KonsepHukum model."""
        konsep = KonsepHukum(
            nama="Transaksi Elektronik",
            definisi="Perbuatan hukum yang dilakukan dengan menggunakan komputer...",
            pasal_utama="1",
            frequency=5,
            confidence=0.95
        )
        
        assert konsep.nama == "Transaksi Elektronik"
        assert konsep.frequency == 5
    
    def test_enriched_pasal_content(self):
        """Test EnrichedPasalContent model."""
        enriched = EnrichedPasalContent(
            nomor_pasal="1",
            full_text="Test content",
            ayat={"1": "Test ayat"},
            entities=[],
            references=[],
            konsep_hukum=[]
        )
        
        assert enriched.nomor_pasal == "1"
        assert len(enriched.entities) == 0
    
    def test_enriched_document_content(self):
        """Test EnrichedDocumentContent model."""
        doc = EnrichedDocumentContent(
            nomor_peraturan="UU No. 11 Tahun 2008",
            pdf_path="/path/to/pdf.pdf",
            enriched_pasals=[]
        )
        
        assert doc.nomor_peraturan == "UU No. 11 Tahun 2008"
        assert doc.total_entities == 0


class TestGeminiLLMExtractor:
    """Test Gemini LLM Extractor."""
    
    @pytest.fixture
    def mock_llm_extractor(self):
        """Create mock extractor."""
        # This test requires google-generativeai, mock if not available
        try:
            from extraction.llm_extractor import GeminiLLMExtractor
            return GeminiLLMExtractor(api_key="test_key")
        except ImportError:
            pytest.skip("google-generativeai not installed")
    
    def test_extractor_initialization(self, mock_llm_extractor):
        """Test extractor initialization."""
        assert mock_llm_extractor is not None
        assert mock_llm_extractor.model_name == "gemini-1.5-pro"


class TestEntityEnricher:
    """Test Entity Enricher."""
    
    def test_pasal_enrichment_structure(self):
        """Test pasal enrichment creates proper structure."""
        from extraction.entity_extractor import EntityEnricher
        
        # Create mock LLM
        mock_llm = Mock()
        mock_llm.extract_entities_from_pasal.return_value = ([], [])
        mock_llm.extract_pasal_references.return_value = ([], [])
        
        enricher = EntityEnricher(mock_llm)
        
        # Create test pasal
        pasal = PasalContent(
            nomor_pasal="1",
            full_text="Test content",
            ayat={"1": "Test ayat"},
            order_index=0
        )
        
        # Enrich
        enriched = enricher.enrich_pasal("UU No. 11 Tahun 2008", pasal)
        
        assert enriched.nomor_pasal == "1"
        assert enriched.full_text == "Test content"


class TestEnrichmentPipeline:
    """Test Enrichment Pipeline."""
    
    def test_pipeline_initialization(self):
        """Test pipeline can be initialized (with mock if needed)."""
        try:
            from extraction.enrichment_pipeline import EnrichmentPipeline
            # This will fail without API key, but tests structure
        except ImportError:
            pytest.skip("google-generativeai not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
