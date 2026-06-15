"""
Example usage untuk TAHAP 2: LLM-Powered Extraction.

Demonstrasi:
1. Load hasil TAHAP 1 (extracted_content.json)
2. Enrich dengan LLM (entities, references, concepts)
3. Save hasil ke enriched_content.json
"""

import json
import os
from pathlib import Path
from typing import Optional

from extraction.enrichment_pipeline import EnrichmentPipeline
from ingestion.utils import get_logger


def example_enrich_document_simple():
    """
    Example: Enrich single document.
    """
    logger = get_logger(__name__, log_level="INFO")
    
    # Get API key dari environment
    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        logger.error("GOOGLE_GEMINI_API_KEY environment variable not set")
        return
    
    # Initialize pipeline
    pipeline = EnrichmentPipeline(gemini_api_key=api_key)
    
    try:
        # Check if extracted_content.json exists
        input_file = "./data/extracted_content.json"
        if not Path(input_file).exists():
            logger.warning(f"Input file not found: {input_file}")
            logger.info("Run TAHAP 1 first: python -m ingestion.main pipeline --pages 2")
            return
        
        # Run enrichment pipeline
        report = pipeline.run_enrichment_pipeline(
            extracted_content_file=input_file,
            output_dir="./data",
        )
        
        # Display report
        logger.info("\n" + "=" * 80)
        logger.info("ENRICHMENT RESULTS")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {report['timestamp']}")
        logger.info(f"Duration: {report['duration_seconds']:.1f}s")
        logger.info(f"\nStatistics:")
        for key, value in report['statistics'].items():
            logger.info(f"  {key}: {value}")
        
        logger.info(f"\nOutput files:")
        for file_type, file_path in report['output_files'].items():
            logger.info(f"  {file_type}: {file_path}")
        
        # Display sample enrichment
        if report['documents']:
            first_doc = report['documents'][0]
            logger.info(f"\nFirst document ({first_doc['nomor_peraturan']}):")
            logger.info(f"  Entities: {first_doc['entities_count']}")
            logger.info(f"  References: {first_doc['references_count']}")
            logger.info(f"  Concepts: {first_doc['concepts_count']}")
    
    except Exception as e:
        logger.error(f"Enrichment failed: {e}", exc_info=True)


def example_display_enriched_entities():
    """
    Example: Display enriched entities.
    """
    logger = get_logger(__name__, log_level="INFO")
    
    entities_file = "./data/extracted_entities.json"
    
    if not Path(entities_file).exists():
        logger.warning(f"Entities file not found: {entities_file}")
        return
    
    logger.info(f"Loading entities from {entities_file}...")
    
    with open(entities_file, "r", encoding="utf-8") as f:
        entities = json.load(f)
    
    logger.info(f"Total entities: {len(entities)}")
    
    # Display top entities by confidence
    entities_sorted = sorted(entities, key=lambda e: e.get('confidence', 0), reverse=True)
    
    logger.info("\nTop 10 entities:")
    for idx, entity in enumerate(entities_sorted[:10], 1):
        logger.info(
            f"{idx}. [{entity['pasal_nomor']}] {entity['text']} "
            f"({entity['entity_type']}, confidence: {entity['confidence']:.2f})"
        )


def example_display_enriched_references():
    """
    Example: Display enriched references.
    """
    logger = get_logger(__name__, log_level="INFO")
    
    references_file = "./data/extracted_references.json"
    
    if not Path(references_file).exists():
        logger.warning(f"References file not found: {references_file}")
        return
    
    logger.info(f"Loading references from {references_file}...")
    
    with open(references_file, "r", encoding="utf-8") as f:
        references = json.load(f)
    
    logger.info(f"Total references: {len(references)}")
    
    # Display sample references
    logger.info("\nSample references (first 10):")
    for idx, ref in enumerate(references[:10], 1):
        logger.info(
            f"{idx}. Pasal {ref['source_pasal']} → Pasal {ref['target_pasal']} "
            f"(confidence: {ref['confidence']:.2f})"
        )
        logger.info(f"   Text: {ref['reference_text'][:80]}...")


def example_display_legal_concepts():
    """
    Example: Display extracted legal concepts.
    """
    logger = get_logger(__name__, log_level="INFO")
    
    concepts_file = "./data/legal_concepts.json"
    
    if not Path(concepts_file).exists():
        logger.warning(f"Concepts file not found: {concepts_file}")
        return
    
    logger.info(f"Loading concepts from {concepts_file}...")
    
    with open(concepts_file, "r", encoding="utf-8") as f:
        concepts = json.load(f)
    
    logger.info(f"Total concepts: {len(concepts)}")
    
    # Display concepts sorted by frequency
    concepts_sorted = sorted(concepts, key=lambda c: c.get('frequency', 0), reverse=True)
    
    logger.info("\nLegal concepts (sorted by frequency):")
    for idx, concept in enumerate(concepts_sorted, 1):
        logger.info(
            f"{idx}. {concept['nama']} "
            f"(Pasal {concept['pasal_utama']}, "
            f"frequency: {concept['frequency']}, confidence: {concept['confidence']:.2f})"
        )
        if concept.get('definisi'):
            logger.info(f"   Definisi: {concept['definisi'][:100]}...")


def main():
    """Main entry point untuk demo."""
    logger = get_logger(__name__, log_level="INFO")
    
    logger.info("=" * 80)
    logger.info("LegalKG TAHAP 2: LLM-POWERED EXTRACTION - DEMO")
    logger.info("=" * 80)
    
    # Check API key
    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        logger.error("\n❌ GOOGLE_GEMINI_API_KEY environment variable not set!")
        logger.info("\nSetup instructions:")
        logger.info("1. Get API key from: https://makersuite.google.com/app/apikey")
        logger.info("2. Set environment variable:")
        logger.info("   export GOOGLE_GEMINI_API_KEY=your_api_key_here")
        return
    
    logger.info("✅ API key configured\n")
    
    # Run enrichment
    logger.info("[STEP 1] Running enrichment pipeline...")
    example_enrich_document_simple()
    
    # Display results
    logger.info("\n[STEP 2] Displaying enriched entities...")
    example_display_enriched_entities()
    
    logger.info("\n[STEP 3] Displaying enriched references...")
    example_display_enriched_references()
    
    logger.info("\n[STEP 4] Displaying legal concepts...")
    example_display_legal_concepts()
    
    logger.info("\n" + "=" * 80)
    logger.info("Demo completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
