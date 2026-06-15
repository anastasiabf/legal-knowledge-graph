"""
Example usage script untuk BPK Crawler dan PDF Processor.

Demonstrasi:
1. Setup crawler
2. Scrape regulations dengan metadata & relations
3. Extract PDF content terstruktur
4. Simpan hasil ke JSON
"""

import json
import logging
from pathlib import Path
from typing import List

from ingestion.scrapers import BPKCrawler, PDFProcessor
from ingestion.models import LegalDocumentMetadata, PDFExtractedContent
from ingestion.utils import ScraperConfig, get_logger


def example_scrape_regulations():
    """
    Example: Scrape regulations dari BPK portal.
    """
    logger = get_logger(__name__, log_level="INFO")
    
    # Setup config
    config = ScraperConfig()
    config.MAX_PAGES_TO_SCRAPE = 2  # Demo: hanya 2 pages
    
    # Initialize crawler
    crawler = BPKCrawler(config=config)
    
    try:
        logger.info("Starting regulation scraping...")
        
        # Scrape semua regulations (dengan PDF download)
        regulations = crawler.scrape_all_regulations(
            max_pages=2,
            download_pdf=True,
        )
        
        logger.info(f"Scraped {len(regulations)} regulations")
        
        # Display hasil
        for reg in regulations[:3]:  # Show first 3
            logger.info(f"- {reg.nomor}: {reg.judul}")
            logger.info(f"  Jenis: {reg.jenis}, Tahun: {reg.tahun}")
            logger.info(f"  PDF: {reg.pdf_path}")
            logger.info(f"  Relations: {len(reg.relations)}")
        
        # Save ke JSON
        output_file = Path("./data/scraped_regulations.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [reg.dict(by_alias=True) for reg in regulations],
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        
        logger.info(f"Results saved to {output_file}")
        
        return regulations
    
    finally:
        crawler.close()


def example_extract_pdf(pdf_path: str, nomor_peraturan: str):
    """
    Example: Extract content dari PDF.
    
    Args:
        pdf_path: Path ke PDF file
        nomor_peraturan: Nomor peraturan
    """
    logger = get_logger(__name__, log_level="INFO")
    
    processor = PDFProcessor(method="PyMuPDF")
    
    try:
        logger.info(f"Extracting PDF: {pdf_path}")
        
        content = processor.extract(pdf_path, nomor_peraturan)
        
        logger.info(f"Extraction successful:")
        logger.info(f"- Total pages: {content.total_pages}")
        logger.info(f"- Total pasals: {len(content.all_pasals)}")
        logger.info(f"- Chapters: {len(content.chapters)}")
        
        # Validate
        is_valid, issues = processor.validate_extraction(content)
        logger.info(f"- Validation: {'PASS' if is_valid else 'FAIL'}")
        if issues:
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        # Display sample pasals
        logger.info("Sample pasals:")
        for pasal in content.all_pasals[:3]:
            logger.info(f"  Pasal {pasal.nomor_pasal}: {pasal.full_text[:100]}...")
        
        # Save ke JSON
        output_file = Path("./data/extracted_content.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                content.dict(by_alias=True),
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        
        logger.info(f"Extraction results saved to {output_file}")
        
        return content
    
    except Exception as e:
        logger.error(f"Failed to extract PDF: {e}")
        raise


def main():
    """Main entry point untuk demo."""
    logger = get_logger(__name__, log_level="INFO")
    
    logger.info("=" * 80)
    logger.info("LegalKG TAHAP 1: INGESTION & SCRAPING - DEMO")
    logger.info("=" * 80)
    
    # Example 1: Scrape regulations
    logger.info("\n[STEP 1] Scraping regulations dari BPK portal...")
    try:
        regulations = example_scrape_regulations()
        
        # Example 2: Extract PDF dari regulation yang berhasil didownload
        if regulations and any(reg.pdf_path for reg in regulations):
            pdf_reg = next(reg for reg in regulations if reg.pdf_path)
            logger.info(f"\n[STEP 2] Extracting PDF untuk {pdf_reg.nomor}...")
            example_extract_pdf(pdf_reg.pdf_path, pdf_reg.nomor)
    
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    
    logger.info("\n" + "=" * 80)
    logger.info("Demo completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
