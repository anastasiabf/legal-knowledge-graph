"""
Konfigurasi global untuk ingestion pipeline.
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class ScraperConfig:
    """Konfigurasi untuk BPK Scraper."""
    
    # Target Portal
    BASE_URL: str = "https://peraturan.bpk.go.id"
    SEARCH_ENDPOINT: str = "/Documents/Search"
    
    # Direktori Output
    DOWNLOAD_DIR: str = os.getenv("LEGAL_KG_DOWNLOAD_DIR", "./data/pdf_downloads")
    EXTRACTION_DIR: str = os.getenv("LEGAL_KG_EXTRACTION_DIR", "./data/extracted_content")
    
    # Rate Limiting
    REQUEST_TIMEOUT: int = 30
    RETRY_ATTEMPTS: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5
    MIN_REQUEST_INTERVAL: float = 1.0  # seconds between requests
    
    # Scraping Parameters
    MAX_PAGES_TO_SCRAPE: int = 100
    ITEMS_PER_PAGE: int = 25
    
    # PDF Download
    MAX_PDF_SIZE_MB: int = 50
    CHUNK_SIZE: int = 8192  # bytes
    VERIFY_SSL: bool = True
    
    # Headers untuk HTTP request
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Ekstraksi PDF
    PDF_PROCESSOR_METHOD: str = "PyMuPDF"  # atau "PDFPlumber"
    
    # Parallel Processing
    MAX_CONCURRENT_DOWNLOADS: int = 3
    MAX_CONCURRENT_EXTRACTIONS: int = 2
    
    def __post_init__(self) -> None:
        """Ensure directories exist."""
        Path(self.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.EXTRACTION_DIR).mkdir(parents=True, exist_ok=True)


# Global config instance
_config: Optional[ScraperConfig] = None


def get_config() -> ScraperConfig:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = ScraperConfig()
    return _config


def set_config(config: ScraperConfig) -> None:
    """Override global config (untuk testing)."""
    global _config
    _config = config
