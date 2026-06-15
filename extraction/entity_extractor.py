"""
Entity Extractor untuk mengorkestrasikan extraction dari entities dan references.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

from extraction.models import (
    LegalEntity,
    PasalReference,
    KonsepHukum,
    EnrichedPasalContent,
    EnrichedDocumentContent,
)
from extraction.llm_extractor import GeminiLLMExtractor
from ingestion.models import PDFExtractedContent, PasalContent
from ingestion.utils import get_logger


class EntityEnricher:
    """
    Orchestrator untuk enriching pasal content dengan entities dan references.
    """
    
    def __init__(self, llm_extractor: GeminiLLMExtractor):
        """
        Initialize enricher.
        
        Args:
            llm_extractor: GeminiLLMExtractor instance
        """
        self.llm = llm_extractor
        self.logger = get_logger(__name__)
    
    def enrich_pasal(
        self,
        nomor_peraturan: str,
        pasal: PasalContent,
    ) -> EnrichedPasalContent:
        """
        Enrich single pasal dengan entities dan references.
        
        Args:
            nomor_peraturan: Nomor peraturan
            pasal: PasalContent dari ekstraksi PDF
            
        Returns:
            EnrichedPasalContent
        """
        self.logger.info(f"Enriching Pasal {pasal.nomor_pasal}...")
        
        warnings = []
        
        # Extract entities
        entities, entity_warnings = self.llm.extract_entities_from_pasal(
            pasal.nomor_pasal,
            pasal.full_text,
        )
        warnings.extend(entity_warnings)
        
        # Extract references
        references, ref_warnings = self.llm.extract_pasal_references(
            pasal.nomor_pasal,
            pasal.full_text,
        )
        warnings.extend(ref_warnings)
        
        # Extract konsep hukum dari text pasal (local extraction tanpa LLM untuk efficiency)
        konsep_hukum = self._extract_konsep_from_entities(entities, pasal.nomor_pasal)
        
        # Create enriched pasal
        enriched = EnrichedPasalContent(
            nomor_pasal=pasal.nomor_pasal,
            full_text=pasal.full_text,
            ayat=pasal.ayat,
            entities=entities,
            references=references,
            konsep_hukum=konsep_hukum,
            extraction_warnings=warnings,
        )
        
        self.logger.info(
            f"Pasal {pasal.nomor_pasal} enriched: "
            f"{len(entities)} entities, {len(references)} references"
        )
        
        return enriched
    
    def enrich_document(
        self,
        extracted_content: PDFExtractedContent,
    ) -> EnrichedDocumentContent:
        """
        Enrich entire document dengan entities, references, dan concepts.
        
        Args:
            extracted_content: PDFExtractedContent dari TAHAP 1
            
        Returns:
            EnrichedDocumentContent
        """
        nomor_peraturan = extracted_content.nomor_peraturan
        self.logger.info(f"Starting document enrichment for {nomor_peraturan}...")
        
        start_time = datetime.utcnow()
        enrichment_started = start_time
        
        # Enrich semua pasal
        enriched_pasals = []
        all_entities = []
        all_references = []
        
        for pasal in extracted_content.all_pasals:
            enriched = self.enrich_pasal(nomor_peraturan, pasal)
            enriched_pasals.append(enriched)
            
            # Collect global entities dan references
            all_entities.extend(enriched.entities)
            all_references.extend(enriched.references)
        
        # Extract global legal concepts
        document_text = "\n\n".join(pasal.full_text for pasal in extracted_content.all_pasals)
        konsep_hukum_list, concept_warnings = self.llm.extract_legal_concepts(
            nomor_peraturan,
            document_text,
        )
        
        # Deduplicate dan enrich concepts dengan reference info
        konsep_hukum_list = self._deduplicate_and_enrich_concepts(
            konsep_hukum_list,
            all_references,
        )
        
        end_time = datetime.utcnow()
        
        # Create enriched document
        enriched_doc = EnrichedDocumentContent(
            nomor_peraturan=nomor_peraturan,
            pdf_path=extracted_content.pdf_path,
            enriched_pasals=enriched_pasals,
            all_entities=all_entities,
            all_references=all_references,
            konsep_hukum_list=konsep_hukum_list,
            total_entities=len(all_entities),
            total_references=len(all_references),
            total_konsep=len(konsep_hukum_list),
            enrichment_started_at=enrichment_started,
            enrichment_completed_at=end_time,
            total_tokens_used=self.llm.total_tokens_used,
        )
        
        duration = (end_time - start_time).total_seconds()
        self.logger.info(
            f"Document enrichment completed in {duration:.1f}s: "
            f"{len(all_entities)} entities, {len(all_references)} references, "
            f"{len(konsep_hukum_list)} concepts"
        )
        
        return enriched_doc
    
    def _extract_konsep_from_entities(
        self,
        entities: List[LegalEntity],
        pasal_nomor: str,
    ) -> List[KonsepHukum]:
        """
        Extract KonsepHukum dari entities (local processing).
        
        Args:
            entities: List of entities
            pasal_nomor: Nomor pasal
            
        Returns:
            List of KonsepHukum
        """
        konsep_list = []
        
        # Filter hanya entities yang tipe "Konsep"
        konsep_entities = [e for e in entities if "Konsep" in e.entity_type or "hukum" in e.entity_type.lower()]
        
        for entity in konsep_entities:
            konsep = KonsepHukum(
                nama=entity.text,
                definisi=entity.context,
                pasal_utama=pasal_nomor,
                frequency=1,
                confidence=entity.confidence,
            )
            konsep_list.append(konsep)
        
        return konsep_list
    
    def _deduplicate_and_enrich_concepts(
        self,
        concepts: List[KonsepHukum],
        references: List[PasalReference],
    ) -> List[KonsepHukum]:
        """
        Deduplicate concepts dan enrich dengan reference information.
        
        Args:
            concepts: List of concepts
            references: List of references
            
        Returns:
            Deduplicated dan enriched concepts
        """
        # Group concepts by name
        concept_dict = {}
        
        for concept in concepts:
            key = concept.nama.lower()
            
            if key in concept_dict:
                # Increment frequency dan take higher confidence
                concept_dict[key].frequency += 1
                concept_dict[key].confidence = max(
                    concept_dict[key].confidence,
                    concept.confidence
                )
            else:
                concept_dict[key] = concept
        
        # Enrich dengan related references
        for concept in concept_dict.values():
            related_refs = [
                ref for ref in references
                if ref.source_pasal == concept.pasal_utama
            ]
            concept.terkait_pasals = list(set(
                [ref.target_pasal for ref in related_refs]
            ))
        
        return list(concept_dict.values())
    
    def get_llm_stats(self) -> Dict:
        """Get LLM usage statistics."""
        return self.llm.get_stats()


class BatchEnricher:
    """Batch processing untuk enriching multiple documents."""
    
    def __init__(self, llm_extractor: GeminiLLMExtractor):
        """Initialize batch enricher."""
        self.enricher = EntityEnricher(llm_extractor)
        self.logger = get_logger(__name__)
    
    def enrich_documents_batch(
        self,
        extracted_contents: List[PDFExtractedContent],
        batch_size: int = 1,
    ) -> List[EnrichedDocumentContent]:
        """
        Enrich multiple documents dalam batch.
        
        Args:
            extracted_contents: List of PDFExtractedContent
            batch_size: Batch size (default: 1 karena API rate limits)
            
        Returns:
            List of EnrichedDocumentContent
        """
        enriched_docs = []
        
        for idx, content in enumerate(extracted_contents, 1):
            try:
                self.logger.info(f"[{idx}/{len(extracted_contents)}] Processing {content.nomor_peraturan}...")
                
                enriched = self.enricher.enrich_document(content)
                enriched_docs.append(enriched)
            
            except Exception as e:
                self.logger.error(
                    f"Failed to enrich {content.nomor_peraturan}: {e}",
                    exc_info=True
                )
                continue
        
        return enriched_docs
