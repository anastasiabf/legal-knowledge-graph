"""
Enrichment Pipeline untuk TAHAP 2: LLM-Powered Extraction.

Mengorkestrasikan:
1. Load hasil TAHAP 1 (extracted_content.json)
2. LLM extraction (entities, references, concepts)
3. Save hasil ke enriched_content.json
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

from extraction.entity_extractor import EntityEnricher, BatchEnricher
from extraction.llm_extractor import GeminiLLMExtractor
from extraction.models import EnrichedDocumentContent
from ingestion.models import PDFExtractedContent
from ingestion.utils import get_logger


class EnrichmentPipeline:
    """
    Pipeline untuk enrichment dokumen dengan LLM-powered extraction.
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Initialize enrichment pipeline.
        
        Args:
            gemini_api_key: Google Gemini API key
        """
        self.logger = get_logger(
            __name__,
            log_file="./logs/enrichment_pipeline.log"
        )
        
        # Initialize LLM
        self.llm = GeminiLLMExtractor(api_key=gemini_api_key)
        self.enricher = EntityEnricher(self.llm)
        self.batch_enricher = BatchEnricher(self.llm)
        
        # Statistics
        self.stats = {
            "total_documents": 0,
            "successful_enrichments": 0,
            "failed_enrichments": 0,
            "start_time": None,
            "end_time": None,
        }
    
    def load_extracted_content(self, json_file: str) -> List[PDFExtractedContent]:
        """
        Load extracted content dari JSON file (output TAHAP 1).
        
        Args:
            json_file: Path ke extracted_content.json
            
        Returns:
            List of PDFExtractedContent
        """
        json_path = Path(json_file)
        
        if not json_path.exists():
            raise FileNotFoundError(f"File not found: {json_file}")
        
        self.logger.info(f"Loading extracted content from {json_file}...")
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Parse JSON to PDFExtractedContent objects
        extracted_contents = []
        
        for doc_data in data:
            try:
                content = PDFExtractedContent(**doc_data)
                extracted_contents.append(content)
            except Exception as e:
                self.logger.warning(f"Failed to parse extracted content: {e}")
                continue
        
        self.logger.info(f"Loaded {len(extracted_contents)} documents")
        return extracted_contents
    
    def run_enrichment_pipeline(
        self,
        extracted_content_file: str,
        output_dir: str = "./data",
    ) -> Dict:
        """
        Run full enrichment pipeline.
        
        Args:
            extracted_content_file: Path ke extracted_content.json
            output_dir: Output directory untuk hasil enrichment
            
        Returns:
            Dict dengan pipeline report
        """
        self.logger.info("=" * 80)
        self.logger.info("STARTING ENRICHMENT PIPELINE (TAHAP 2)")
        self.logger.info("=" * 80)
        
        self.stats["start_time"] = datetime.utcnow()
        
        try:
            # Load extracted content
            extracted_contents = self.load_extracted_content(extracted_content_file)
            self.stats["total_documents"] = len(extracted_contents)
            
            # Run enrichment
            self.logger.info("\nEnriching documents with LLM...")
            enriched_docs = self.batch_enricher.enrich_documents_batch(extracted_contents)
            self.stats["successful_enrichments"] = len(enriched_docs)
            self.stats["failed_enrichments"] = len(extracted_contents) - len(enriched_docs)
            
            # Save results
            self.logger.info("\nSaving enriched content...")
            output_files = self.save_enrichment_results(enriched_docs, output_dir)
            
            # Generate report
            report = self._generate_report(enriched_docs, output_files)
            
            self.stats["end_time"] = datetime.utcnow()
            
            self.logger.info("\n" + "=" * 80)
            self.logger.info("ENRICHMENT PIPELINE COMPLETED")
            self.logger.info("=" * 80)
            
            return report
        
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.stats["end_time"] = datetime.utcnow()
            raise
    
    def save_enrichment_results(
        self,
        enriched_docs: List[EnrichedDocumentContent],
        output_dir: str = "./data",
    ) -> Dict[str, str]:
        """
        Save enrichment results ke JSON files.
        
        Args:
            enriched_docs: List of enriched documents
            output_dir: Output directory
            
        Returns:
            Dict mapping file_type -> file_path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files_saved = {}
        
        try:
            # Save enriched documents
            enriched_file = output_path / "enriched_content.json"
            with open(enriched_file, "w", encoding="utf-8") as f:
                json.dump(
                    [doc.dict(by_alias=True) for doc in enriched_docs],
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            files_saved["enriched_documents"] = str(enriched_file)
            self.logger.info(f"Saved enriched documents to {enriched_file}")
            
            # Save entities summary
            all_entities = []
            for doc in enriched_docs:
                all_entities.extend(doc.all_entities)
            
            entities_file = output_path / "extracted_entities.json"
            with open(entities_file, "w", encoding="utf-8") as f:
                json.dump(
                    [e.dict() for e in all_entities],
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            files_saved["entities"] = str(entities_file)
            self.logger.info(f"Saved entities to {entities_file}")
            
            # Save references summary
            all_references = []
            for doc in enriched_docs:
                all_references.extend(doc.all_references)
            
            references_file = output_path / "extracted_references.json"
            with open(references_file, "w", encoding="utf-8") as f:
                json.dump(
                    [r.dict() for r in all_references],
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            files_saved["references"] = str(references_file)
            self.logger.info(f"Saved references to {references_file}")
            
            # Save legal concepts
            all_concepts = []
            for doc in enriched_docs:
                all_concepts.extend(doc.konsep_hukum_list)
            
            concepts_file = output_path / "legal_concepts.json"
            with open(concepts_file, "w", encoding="utf-8") as f:
                json.dump(
                    [c.dict() for c in all_concepts],
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            files_saved["concepts"] = str(concepts_file)
            self.logger.info(f"Saved concepts to {concepts_file}")
            
            # Save LLM statistics
            llm_stats = self.llm.get_stats()
            stats_file = output_path / "llm_statistics.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(llm_stats, f, indent=2)
            files_saved["llm_stats"] = str(stats_file)
            self.logger.info(f"Saved LLM stats to {stats_file}")
        
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            raise
        
        return files_saved
    
    def _generate_report(
        self,
        enriched_docs: List[EnrichedDocumentContent],
        output_files: Dict[str, str],
    ) -> Dict:
        """Generate enrichment report."""
        duration = self.stats["end_time"] - self.stats["start_time"]
        
        # Aggregate statistics
        total_entities = sum(doc.total_entities for doc in enriched_docs)
        total_references = sum(doc.total_references for doc in enriched_docs)
        total_concepts = sum(doc.total_konsep for doc in enriched_docs)
        total_tokens = sum(doc.total_tokens_used for doc in enriched_docs)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_type": "Enrichment (TAHAP 2)",
            "duration_seconds": duration.total_seconds(),
            "statistics": {
                "total_documents": self.stats["total_documents"],
                "successful_enrichments": self.stats["successful_enrichments"],
                "failed_enrichments": self.stats["failed_enrichments"],
                "total_entities": total_entities,
                "total_references": total_references,
                "total_concepts": total_concepts,
                "total_tokens_used": total_tokens,
            },
            "output_files": output_files,
            "documents": [
                {
                    "nomor_peraturan": doc.nomor_peraturan,
                    "entities_count": doc.total_entities,
                    "references_count": doc.total_references,
                    "concepts_count": doc.total_konsep,
                    "enrichment_time": (
                        doc.enrichment_completed_at - doc.enrichment_started_at
                    ).total_seconds() if doc.enrichment_completed_at else 0,
                }
                for doc in enriched_docs
            ],
        }
        
        # Save report
        report_file = Path(list(output_files.values())[0]).parent / "enrichment_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Saved report to {report_file}")
        
        return report
