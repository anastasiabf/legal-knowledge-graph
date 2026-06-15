# LegalKG TAHAP 1: Quick Reference Guide

## 🚀 Quick Start (2 minutes)

```bash
# 1. Install
pip install -r requirements_ingestion.txt

# 2. Setup env (optional)
cp .env.example .env

# 3. Run
python -m ingestion.main pipeline --pages 2
```

---

## 📖 Common Tasks

### Task 1: Scrape regulations
```python
from ingestion.scrapers import BPKCrawler

crawler = BPKCrawler()
regulations = crawler.scrape_all_regulations(max_pages=5, download_pdf=True)
```

### Task 2: Extract PDF content
```python
from ingestion.scrapers import PDFProcessor

processor = PDFProcessor()
content = processor.extract("/path/to/uu_11_2008.pdf", "UU No. 11 Tahun 2008")

# Get specific pasal
pasal_27 = processor.extract_pasal_by_number(content, "27")
```

### Task 3: Run full pipeline
```python
from ingestion.pipeline import IngestionPipeline

pipeline = IngestionPipeline()
report = pipeline.run_full_pipeline(max_pages=10, extract_pdf=True)
pipeline.save_results_to_json()
```

### Task 4: Custom configuration
```python
from ingestion.utils import ScraperConfig
from ingestion.scrapers import BPKCrawler

config = ScraperConfig()
config.MAX_PAGES_TO_SCRAPE = 20
config.REQUEST_TIMEOUT = 60
config.MIN_REQUEST_INTERVAL = 2.0

crawler = BPKCrawler(config=config)
```

---

## 🔧 CLI Commands

```bash
# Scrape regulations (2 pages, download PDFs)
python -m ingestion.main scrape --pages 2 --download-pdf

# Extract PDFs from directory
python -m ingestion.main extract --pdf-dir ./data/pdf_downloads

# Run full pipeline
python -m ingestion.main pipeline --pages 10 --force --output-dir ./results

# Cleanup old files (older than 30 days)
python -m ingestion.main cleanup --days 30

# With custom log level
python -m ingestion.main --log-level DEBUG pipeline --pages 5
```

---

## 📊 Output Files

| File | Location | Purpose |
|------|----------|---------|
| `scraped_regulations.json` | `./data/` | Metadata + relations |
| `extracted_content.json` | `./data/` | Structured pasals/ayat |
| `pipeline_report.json` | `./data/` | Statistics + errors |
| Logs | `./logs/` | Execution logs |
| PDFs | `./data/pdf_downloads/` | Downloaded files |

---

## 🐛 Debugging

```python
# Enable debug logging
from ingestion.utils import get_logger

logger = get_logger(__name__, log_level="DEBUG")

# Check raw PDF text
processor = PDFProcessor()
content = processor.extract(pdf_path, nomor)
print(content.raw_full_text[:1000])

# Validate extraction
is_valid, issues = processor.validate_extraction(content)
print(f"Valid: {is_valid}, Issues: {issues}")
```

---

## 📈 Configuration Reference

```python
ScraperConfig():
  BASE_URL = "https://peraturan.bpk.go.id"
  DOWNLOAD_DIR = "./data/pdf_downloads"
  EXTRACTION_DIR = "./data/extracted_content"
  REQUEST_TIMEOUT = 30  # seconds
  RETRY_ATTEMPTS = 3
  RETRY_BACKOFF_FACTOR = 1.5
  MIN_REQUEST_INTERVAL = 1.0  # seconds
  MAX_PDF_SIZE_MB = 50
  PDF_PROCESSOR_METHOD = "PyMuPDF"  # or "PDFPlumber"
  MAX_CONCURRENT_DOWNLOADS = 3
  MAX_CONCURRENT_EXTRACTIONS = 2
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/test_ingestion.py -v

# Run specific test
pytest tests/test_ingestion.py::TestBPKCrawler -v

# With coverage
pytest tests/test_ingestion.py --cov=ingestion --cov-report=html
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| [INGESTION_README.md](INGESTION_README.md) | Comprehensive documentation |
| [TAHAP_1_SUMMARY.md](TAHAP_1_SUMMARY.md) | Implementation overview |
| [.env.example](.env.example) | Configuration template |
| Code Comments | Detailed docstrings in each module |

---

## ⚡ Performance Tips

- Use `PDFPlumber` untuk dokumen kompleks
- Adjust `MAX_CONCURRENT_*` sesuai hardware
- Increase `MIN_REQUEST_INTERVAL` jika rate limited
- Monitor log files untuk troubleshoot

---

## 🔗 Next Phase: TAHAP 2

Output dari TAHAP 1 → Input untuk TAHAP 2 (LLM-powered extraction)

```python
# TAHAP 2 akan menggunakan:
import json

with open("extracted_content.json") as f:
    content = json.load(f)

# Extract KonsepHukum, MERUJUK_KE relations, dll
```

---

**Last Updated**: June 15, 2026
**Version**: 1.0.0
