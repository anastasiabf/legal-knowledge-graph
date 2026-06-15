"""
Pipeline orchestrator untuk ingestion workflow.

Mengelola:
- Jadwal scraping berkala (APScheduler)
- Rate limiting dan concurrency
- Progress tracking
- Error recovery dan retry logic
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from pathlib import Path
import logging

from ingestion.scrapers import BPKCrawler, PDFProcessor
from ingestion.models import LegalDocumentMetadata, PDFExtractedContent
from ingestion.utils import ScraperConfig, get_logger, FileManager


class IngestionPipeline:
    """
    Orchestrator untuk seluruh ingestion pipeline.
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize pipeline.
        
        Args:
            config: ScraperConfig instance
        """
        self.config = config or ScraperConfig()
        self.logger = get_logger(
            __name__,
            log_file=f"{self.config.DOWNLOAD_DIR}/pipeline.log"
        )
        self.file_manager = FileManager(self.config.DOWNLOAD_DIR)
        self.crawler = BPKCrawler(config=self.config)
        self.pdf_processor = PDFProcessor(method=self.config.PDF_PROCESSOR_METHOD)
        
        # State tracking
        self.scraped_regulations: List[LegalDocumentMetadata] = []
        self.extracted_content: List[PDFExtractedContent] = []
        self.failed_regulations: List[Dict] = []
        self.pipeline_stats = {
            "total_scraped": 0,
            "total_extracted": 0,
            "total_failed": 0,
            "start_time": None,
            "end_time": None,
        }
    
    def run_full_pipeline(
        self,
        max_pages: Optional[int] = None,
        extract_pdf: bool = True,
        skip_existing_pdfs: bool = True,
    ) -> Dict:
        """
        Run full pipeline: scrape -> download PDF -> extract content.
        
        Args:
            max_pages: Max pages to scrape
            extract_pdf: Whether to extract PDF content
            skip_existing_pdfs: Skip extraction if extracted content sudah ada
            
        Returns:
            Dict dengan pipeline results dan statistics
        """
        self.logger.info("=" * 80)
        self.logger.info("STARTING FULL INGESTION PIPELINE")
        self.logger.info("=" * 80)
        
        self.pipeline_stats["start_time"] = datetime.now()
        
        try:
            # STEP 1: Scrape regulations
            self.logger.info("\n[STEP 1/3] Scraping regulations from BPK portal...")
            self.scraped_regulations = self.crawler.scrape_all_regulations(
                max_pages=max_pages,
                download_pdf=True,
            )
            self.pipeline_stats["total_scraped"] = len(self.scraped_regulations)
            self.logger.info(f"Scraped {len(self.scraped_regulations)} regulations")
            
            # STEP 2: Extract PDF content
            if extract_pdf:
                self.logger.info("\n[STEP 2/3] Extracting PDF content...")
                self.extracted_content = self._extract_all_pdfs(
                    skip_existing=skip_existing_pdfs
                )
                self.pipeline_stats["total_extracted"] = len(self.extracted_content)
            
            # STEP 3: Generate report
            self.logger.info("\n[STEP 3/3] Generating pipeline report...")
            report = self._generate_report()
            
            self.pipeline_stats["end_time"] = datetime.now()
            
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 80)
            self.logger.info(f"Statistics: {self.pipeline_stats}")
            
            return report
        
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.pipeline_stats["end_time"] = datetime.now()
            raise
        
        finally:
            self.crawler.close()
    
    def _extract_all_pdfs(self, skip_existing: bool = True) -> List[PDFExtractedContent]:
        """
        Extract content dari semua PDF yang berhasil didownload.
        
        Args:
            skip_existing: Skip jika extracted content sudah ada
            
        Returns:
            List of PDFExtractedContent
        """
        extracted = []
        failed_extractions = []
        
        pdf_regulations = [
            reg for reg in self.scraped_regulations if reg.pdf_path
        ]
        
        self.logger.info(f"Extracting {len(pdf_regulations)} PDFs...")
        
        for idx, regulation in enumerate(pdf_regulations, 1):
            try:
                self.logger.info(
                    f"[{idx}/{len(pdf_regulations)}] Extracting {regulation.nomor}..."
                )
                
                content = self.pdf_processor.extract(
                    regulation.pdf_path,
                    regulation.nomor,
                )
                
                # Validate extraction
                is_valid, issues = self.pdf_processor.validate_extraction(content)
                
                if issues:
                    for issue in issues:
                        self.logger.warning(f"  - {issue}")
                
                extracted.append(content)
                self.logger.info(
                    f"  ✓ Extracted: {len(content.all_pasals)} pasals"
                )
            
            except Exception as e:
                self.logger.error(f"Failed to extract {regulation.nomor}: {e}")
                failed_extractions.append({
                    "nomor": regulation.nomor,
                    "error": str(e),
                })
                self.pipeline_stats["total_failed"] += 1
                continue
        
        self.failed_regulations.extend(failed_extractions)
        return extracted
    
    def _generate_report(self) -> Dict:
        """
        Generate comprehensive pipeline report.
        
        Returns:
            Dict dengan report data
        """
        duration = self.pipeline_stats["end_time"] - self.pipeline_stats["start_time"]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration.total_seconds(),
            "statistics": self.pipeline_stats,
            "regulations": [
                {
                    "nomor": reg.nomor,
                    "judul": reg.judul,
                    "jenis": reg.jenis,
                    "tahun": reg.tahun,
                    "pdf_downloaded": reg.pdf_path is not None,
                    "relations_count": len(reg.relations),
                }
                for reg in self.scraped_regulations
            ],
            "extractions": [
                {
                    "nomor_peraturan": content.nomor_peraturan,
                    "total_pages": content.total_pages,
                    "pasals_count": len(content.all_pasals),
                    "chapters_count": len(content.chapters),
                    "is_valid": content.is_valid,
                }
                for content in self.extracted_content
            ],
            "failed_regulations": self.failed_regulations,
        }
        
        return report
    
    def save_results_to_json(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Save pipeline results ke JSON files.
        
        Args:
            output_dir: Output directory (default: config.EXTRACTION_DIR)
            
        Returns:
            Dict mapping file_type -> file_path
        """
        import json
        
        output_path = Path(output_dir or self.config.EXTRACTION_DIR)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files_saved = {}
        
        try:
            # Save scraped regulations
            regulations_file = output_path / "scraped_regulations.json"
            with open(regulations_file, "w", encoding="utf-8") as f:
                json.dump(
                    [reg.dict(by_alias=True) for reg in self.scraped_regulations],
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            files_saved["regulations"] = str(regulations_file)
            self.logger.info(f"Saved regulations to {regulations_file}")
            
            # Save extracted content
            if self.extracted_content:
                extracted_file = output_path / "extracted_content.json"
                with open(extracted_file, "w", encoding="utf-8") as f:
                    json.dump(
                        [content.dict(by_alias=True) for content in self.extracted_content],
                        f,
                        indent=2,
                        ensure_ascii=False,
                        default=str,
                    )
                files_saved["extractions"] = str(extracted_file)
                self.logger.info(f"Saved extractions to {extracted_file}")
            
            # Save report
            report = self._generate_report()
            report_file = output_path / "pipeline_report.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            files_saved["report"] = str(report_file)
            self.logger.info(f"Saved report to {report_file}")
        
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            raise
        
        return files_saved
    
    def cleanup_old_downloads(self, days_old: int = 30) -> int:
        """
        Cleanup PDF files older than specified days.
        
        Args:
            days_old: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        deleted_count = self.file_manager.cleanup_old_files(days_old=days_old)
        self.logger.info(f"Cleaned up {deleted_count} old PDF files")
        return deleted_count
