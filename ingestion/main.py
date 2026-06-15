#!/usr/bin/env python3
"""
LegalKG TAHAP 1: Production-Ready Ingestion Pipeline Entry Point

Ini adalah main entry point untuk running ingestion pipeline production-ready.

Usage:
    python -m ingestion.main scrape --pages 10 --download-pdf
    python -m ingestion.main extract --pdf-dir ./data/pdf_downloads
    python -m ingestion.main pipeline --full
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from ingestion.pipeline import IngestionPipeline
from ingestion.scrapers import BPKCrawler, PDFProcessor
from ingestion.utils import ScraperConfig, get_logger


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup logging untuk CLI."""
    return get_logger(
        "legalkg.ingestion",
        log_level=log_level,
        log_file="./logs/ingestion_cli.log",
    )


def cmd_scrape(args, logger: logging.Logger) -> int:
    """Command: Scrape regulations dari BPK portal."""
    logger.info("Starting scraping command...")
    
    try:
        config = ScraperConfig()
        config.MAX_PAGES_TO_SCRAPE = args.pages or 100
        
        crawler = BPKCrawler(config=config)
        
        logger.info(f"Scraping {args.pages or 'all'} pages...")
        regulations = crawler.scrape_all_regulations(
            max_pages=args.pages,
            download_pdf=args.download_pdf,
        )
        
        logger.info(f"Successfully scraped {len(regulations)} regulations")
        
        # Save ke file
        output_file = Path(args.output or "./data/scraped_regulations.json")
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
        return 0
    
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        return 1
    
    finally:
        crawler.close()


def cmd_extract(args, logger: logging.Logger) -> int:
    """Command: Extract content dari PDF files."""
    logger.info("Starting extraction command...")
    
    try:
        pdf_dir = Path(args.pdf_dir or "./data/pdf_downloads")
        
        if not pdf_dir.exists():
            logger.error(f"PDF directory not found: {pdf_dir}")
            return 1
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {pdf_dir}")
        
        if not pdf_files:
            logger.warning("No PDF files found")
            return 0
        
        processor = PDFProcessor(method=args.method or "PyMuPDF")
        extracted_content = []
        failed = []
        
        for idx, pdf_file in enumerate(pdf_files, 1):
            try:
                logger.info(f"[{idx}/{len(pdf_files)}] Extracting {pdf_file.name}...")
                
                content = processor.extract(str(pdf_file), pdf_file.stem)
                
                # Validate
                is_valid, issues = processor.validate_extraction(content)
                if issues:
                    logger.warning(f"Extraction issues: {', '.join(issues)}")
                
                extracted_content.append(content)
                logger.info(f"  ✓ Extracted {len(content.all_pasals)} pasals")
            
            except Exception as e:
                logger.error(f"Failed to extract {pdf_file.name}: {e}")
                failed.append({"file": pdf_file.name, "error": str(e)})
        
        # Save results
        output_file = Path(args.output or "./data/extracted_content.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [content.dict(by_alias=True) for content in extracted_content],
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        
        logger.info(f"Extraction completed: {len(extracted_content)} successful, {len(failed)} failed")
        logger.info(f"Results saved to {output_file}")
        
        return 0 if not failed else 1
    
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return 1


def cmd_pipeline(args, logger: logging.Logger) -> int:
    """Command: Run full ingestion pipeline."""
    logger.info("Starting full pipeline...")
    
    try:
        pipeline = IngestionPipeline()
        
        logger.info("Running full pipeline (scrape + extract)...")
        report = pipeline.run_full_pipeline(
            max_pages=args.pages or 10,
            extract_pdf=True,
            skip_existing_pdfs=not args.force,
        )
        
        # Save results
        output_files = pipeline.save_results_to_json(args.output_dir)
        
        logger.info(f"\nPipeline Summary:")
        logger.info(f"  Total scraped: {report['statistics']['total_scraped']}")
        logger.info(f"  Total extracted: {report['statistics']['total_extracted']}")
        logger.info(f"  Failed: {report['statistics']['total_failed']}")
        logger.info(f"  Duration: {report['duration_seconds']:.1f}s")
        
        logger.info(f"\nOutput files:")
        for file_type, file_path in output_files.items():
            logger.info(f"  - {file_type}: {file_path}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


def cmd_cleanup(args, logger: logging.Logger) -> int:
    """Command: Cleanup old files."""
    logger.info("Starting cleanup...")
    
    try:
        pipeline = IngestionPipeline()
        deleted_count = pipeline.cleanup_old_downloads(days_old=args.days)
        
        logger.info(f"Cleaned up {deleted_count} files older than {args.days} days")
        return 0
    
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LegalKG TAHAP 1: Ingestion & Scraping Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ingestion.main scrape --pages 5 --download-pdf
  python -m ingestion.main extract --pdf-dir ./data/pdf_downloads
  python -m ingestion.main pipeline --full
  python -m ingestion.main cleanup --days 30
        """,
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape regulations from BPK portal")
    scrape_parser.add_argument("--pages", type=int, help="Number of pages to scrape")
    scrape_parser.add_argument(
        "--download-pdf",
        action="store_true",
        help="Download PDF files",
    )
    scrape_parser.add_argument(
        "--output",
        help="Output JSON file path",
    )
    scrape_parser.set_defaults(func=cmd_scrape)
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract content from PDFs")
    extract_parser.add_argument(
        "--pdf-dir",
        help="Directory containing PDF files",
    )
    extract_parser.add_argument(
        "--method",
        choices=["PyMuPDF", "PDFPlumber"],
        help="PDF extraction method",
    )
    extract_parser.add_argument(
        "--output",
        help="Output JSON file path",
    )
    extract_parser.set_defaults(func=cmd_extract)
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Run full ingestion pipeline")
    pipeline_parser.add_argument(
        "--pages",
        type=int,
        help="Number of pages to scrape (default: 10)",
    )
    pipeline_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-extraction of existing PDFs",
    )
    pipeline_parser.add_argument(
        "--output-dir",
        help="Output directory for results",
    )
    pipeline_parser.set_defaults(func=cmd_pipeline)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup old PDF files")
    cleanup_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Delete files older than N days (default: 30)",
    )
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args, logger)


if __name__ == "__main__":
    sys.exit(main())
