"""
BPK Crawler - Scraper untuk https://peraturan.bpk.go.id

Mengekstrak:
- Metadata peraturan (Judul, Nomor, Tahun, Jenis, Tanggal)
- Tabel status hubungan hukum (Mengubah, Mencabut, Dasar Delegasi)
- Download file PDF peraturan secara aman dengan retry logic
"""

import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlencode
from datetime import datetime
import logging

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models import (
    LegalDocumentMetadata,
    LegalDocumentRelation,
    LegalDocumentStatusEnum,
)
from ..utils import ScraperConfig, get_logger, FileManager


class BPKCrawler:
    """
    Scraper untuk portal BPK (peraturan.bpk.go.id).
    
    Fitur:
    - Automated metadata extraction
    - PDF download dengan retry & rate limiting
    - Legal relationship extraction (mencabut, mengubah, dasar delegasi)
    - Comprehensive error handling & logging
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize BPK Crawler.
        
        Args:
            config: ScraperConfig instance. Jika None, use default config.
        """
        self.config = config or ScraperConfig()
        self.logger = get_logger(
            __name__,
            log_file=f"{self.config.DOWNLOAD_DIR}/bpk_crawler.log"
        )
        self.file_manager = FileManager(self.config.DOWNLOAD_DIR)
        
        # Setup HTTP session dengan retry logic
        self.session = self._create_session()
        self.last_request_time = 0.0
    
    def _create_session(self) -> requests.Session:
        """
        Create requests.Session dengan retry strategy.
        
        Returns:
            Configured requests.Session
        """
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=self.config.RETRY_ATTEMPTS,
            backoff_factor=self.config.RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers
        session.headers.update({
            "User-Agent": self.config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9",
        })
        
        return session
    
    def _rate_limit(self) -> None:
        """Apply rate limiting antara requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.MIN_REQUEST_INTERVAL:
            time.sleep(self.config.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()
    
    def fetch_regulation_list(self, page: int = 1) -> Tuple[List[Dict], int]:
        """
        Fetch list of regulations dari search page BPK.
        
        Args:
            page: Page number untuk pagination
            
        Returns:
            Tuple of (list of regulation data dicts, total_pages)
        """
        try:
            self._rate_limit()
            
            params = {
                "page": page,
                "pageSize": self.config.ITEMS_PER_PAGE,
            }
            
            url = urljoin(self.config.BASE_URL, self.config.SEARCH_ENDPOINT)
            self.logger.info(f"Fetching regulations from page {page}: {url}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
                verify=self.config.VERIFY_SSL,
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract regulation items
            regulations = self._parse_regulation_items(soup)
            
            # Extract pagination info
            total_pages = self._extract_total_pages(soup)
            
            self.logger.info(
                f"Successfully fetched {len(regulations)} regulations from page {page}"
            )
            
            return regulations, total_pages
        
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch regulation list from page {page}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error fetching regulation list: {e}")
            raise
    
    def _parse_regulation_items(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse individual regulation items dari soup.
        
        Args:
            soup: BeautifulSoup instance dari halaman search
            
        Returns:
            List of regulation data dicts
        """
        regulations = []
        
        # Sesuaikan selector dengan struktur HTML peraturan.bpk.go.id
        # (Ini adalah contoh umum, perlu disesuaikan dengan struktur aktual)
        item_selector = "tr"  # atau selector yang sesuai untuk row peraturan
        
        for item in soup.select(item_selector):
            try:
                regulation_data = self._extract_regulation_data(item)
                if regulation_data:
                    regulations.append(regulation_data)
            except Exception as e:
                self.logger.warning(f"Error parsing regulation item: {e}")
                continue
        
        return regulations
    
    def _extract_regulation_data(self, item) -> Optional[Dict]:
        """
        Extract data dari individual regulation item.
        
        Args:
            item: BeautifulSoup element untuk satu peraturan
            
        Returns:
            Dict dengan regulation data atau None jika parsing gagal
        """
        try:
            # Sesuaikan selectors ini dengan struktur HTML aktual
            judul_elem = item.select_one(".judul-peraturan, td:nth-child(2)")
            nomor_elem = item.select_one(".nomor-peraturan, td:nth-child(1)")
            tahun_elem = item.select_one(".tahun, td:nth-child(3)")
            jenis_elem = item.select_one(".jenis, td:nth-child(4)")
            tanggal_elem = item.select_one(".tanggal, td:nth-child(5)")
            
            if not all([judul_elem, nomor_elem]):
                return None
            
            # Extract link untuk detail page
            link_elem = item.select_one("a[href]")
            url = urljoin(self.config.BASE_URL, link_elem["href"]) if link_elem else None
            
            return {
                "judul": judul_elem.get_text(strip=True) if judul_elem else "",
                "nomor": nomor_elem.get_text(strip=True) if nomor_elem else "",
                "tahun": int(tahun_elem.get_text(strip=True)[-4:]) if tahun_elem else None,
                "jenis": jenis_elem.get_text(strip=True) if jenis_elem else "",
                "tanggal": tanggal_elem.get_text(strip=True) if tanggal_elem else None,
                "url": url,
            }
        
        except Exception as e:
            self.logger.warning(f"Error extracting regulation data: {e}")
            return None
    
    def _extract_total_pages(self, soup: BeautifulSoup) -> int:
        """
        Extract total pages dari pagination info.
        
        Args:
            soup: BeautifulSoup instance
            
        Returns:
            Total pages atau default value
        """
        try:
            pagination = soup.select_one(".pagination, .paging")
            if not pagination:
                return 1
            
            # Look for last page link
            last_link = pagination.select_one("a:last-child")
            if last_link and "href" in last_link.attrs:
                import re
                match = re.search(r"page=(\d+)", last_link["href"])
                if match:
                    return int(match.group(1))
            
            return 1
        except Exception:
            return 1
    
    def fetch_regulation_detail(self, url: str) -> LegalDocumentMetadata:
        """
        Fetch detail page untuk satu peraturan, ekstrak metadata & relations.
        
        Args:
            url: URL detail peraturan
            
        Returns:
            LegalDocumentMetadata instance
        """
        try:
            self._rate_limit()
            
            self.logger.info(f"Fetching regulation detail: {url}")
            response = self.session.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
                verify=self.config.VERIFY_SSL,
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract metadata
            metadata = self._extract_metadata_from_detail(soup)
            
            # Extract relations
            relations = self._extract_relations_table(soup)
            metadata["relations"] = relations
            
            # Extract PDF URL
            pdf_url = self._extract_pdf_url(soup)
            metadata["pdf_url"] = pdf_url
            
            # Set URL
            metadata["url"] = url
            
            return LegalDocumentMetadata(**metadata)
        
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch regulation detail from {url}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error processing regulation detail: {e}")
            raise
    
    def _extract_metadata_from_detail(self, soup: BeautifulSoup) -> Dict:
        """
        Extract metadata dari detail page.
        
        Args:
            soup: BeautifulSoup instance
            
        Returns:
            Dict dengan metadata
        """
        metadata = {
            "judul": "",
            "nomor": "",
            "tahun": datetime.now().year,
            "jenis": "",
            "tanggal_disahkan": None,
            "tanggal_diundangkan": None,
            "lembaga_penerbit": None,
        }
        
        try:
            # Sesuaikan selectors dengan struktur HTML aktual
            title_elem = soup.select_one("h1, .document-title, .judul-peraturan")
            if title_elem:
                metadata["judul"] = title_elem.get_text(strip=True)
            
            nomor_elem = soup.select_one(".nomor-peraturan, .regulation-number")
            if nomor_elem:
                nomor_text = nomor_elem.get_text(strip=True)
                metadata["nomor"] = nomor_text
                
                # Extract tahun dari nomor (e.g., "UU No. 11 Tahun 2008" -> 2008)
                import re
                year_match = re.search(r"(\d{4})", nomor_text)
                if year_match:
                    metadata["tahun"] = int(year_match.group(1))
            
            # Extract tipe peraturan
            jenis_elem = soup.select_one(".jenis-peraturan, .regulation-type")
            if jenis_elem:
                metadata["jenis"] = jenis_elem.get_text(strip=True)
            
            # Extract tanggal
            date_elem = soup.select_one(".tanggal-disahkan, .date-issued")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
                try:
                    metadata["tanggal_disahkan"] = datetime.strptime(date_str, "%d-%m-%Y")
                except ValueError:
                    pass
            
            # Extract lembaga
            lembaga_elem = soup.select_one(".lembaga-penerbit, .issuing-body")
            if lembaga_elem:
                metadata["lembaga_penerbit"] = lembaga_elem.get_text(strip=True)
        
        except Exception as e:
            self.logger.warning(f"Error extracting metadata from detail page: {e}")
        
        return metadata
    
    def _extract_relations_table(self, soup: BeautifulSoup) -> List[LegalDocumentRelation]:
        """
        Extract tabel hubungan hukum (Mengubah, Mencabut, Dasar Delegasi).
        
        Args:
            soup: BeautifulSoup instance
            
        Returns:
            List of LegalDocumentRelation
        """
        relations = []
        
        try:
            # Cari tabel relasi (biasanya ada section khusus)
            tables = soup.select("table")
            
            for table in tables:
                # Cek header untuk identify tabel relasi
                headers = [h.get_text(strip=True).lower() for h in table.select("th")]
                
                if any(keyword in " ".join(headers) for keyword in 
                       ["mengubah", "mencabut", "dasar delegasi", "hubungan"]):
                    # Parse rows dari tabel relasi
                    for row in table.select("tbody tr"):
                        relation = self._parse_relation_row(row)
                        if relation:
                            relations.append(relation)
        
        except Exception as e:
            self.logger.warning(f"Error extracting relations table: {e}")
        
        return relations
    
    def _parse_relation_row(self, row) -> Optional[LegalDocumentRelation]:
        """
        Parse satu row dari relasi table.
        
        Args:
            row: BeautifulSoup element untuk satu row
            
        Returns:
            LegalDocumentRelation atau None
        """
        try:
            cells = row.select("td")
            if len(cells) < 2:
                return None
            
            relation_type_text = cells[0].get_text(strip=True).upper()
            target_regulation = cells[1].get_text(strip=True)
            
            # Map tipe relasi
            relation_type = None
            if "MENGUBAH" in relation_type_text:
                relation_type = LegalDocumentStatusEnum.MENGUBAH
            elif "MENCABUT" in relation_type_text:
                relation_type = LegalDocumentStatusEnum.MENCABUT
            elif "DASAR DELEGASI" in relation_type_text or "DELEGASI" in relation_type_text:
                relation_type = LegalDocumentStatusEnum.DASAR_DELEGASI
            
            if not relation_type or not target_regulation:
                return None
            
            return LegalDocumentRelation(
                source_regulation="",  # akan di-fill dari parent metadata
                target_regulation=target_regulation,
                relation_type=relation_type,
                description=cells[2].get_text(strip=True) if len(cells) > 2 else None,
            )
        
        except Exception as e:
            self.logger.warning(f"Error parsing relation row: {e}")
            return None
    
    def _extract_pdf_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract URL untuk PDF file dari detail page.
        
        Args:
            soup: BeautifulSoup instance
            
        Returns:
            PDF URL atau None
        """
        try:
            # Cari link yang mengarah ke PDF
            pdf_link = soup.select_one("a[href*='.pdf'], a[href*='pdf'], .download-pdf a")
            
            if pdf_link and "href" in pdf_link.attrs:
                pdf_url = pdf_link["href"]
                # Handle relative URLs
                if not pdf_url.startswith("http"):
                    pdf_url = urljoin(self.config.BASE_URL, pdf_url)
                return pdf_url
        
        except Exception as e:
            self.logger.warning(f"Error extracting PDF URL: {e}")
        
        return None
    
    def download_pdf(
        self,
        pdf_url: str,
        nomor_peraturan: str,
        force_download: bool = False,
    ) -> Optional[str]:
        """
        Download file PDF dari URL dengan safety checks.
        
        Args:
            pdf_url: URL dari file PDF
            nomor_peraturan: Nomor peraturan (untuk naming)
            force_download: Force download meski file sudah ada
            
        Returns:
            Path ke file yang didownload, atau None jika gagal
        """
        try:
            # Check apakah file sudah ada
            pdf_path = self.file_manager.get_pdf_path(nomor_peraturan)
            
            if pdf_path.exists() and not force_download:
                self.logger.info(f"PDF already exists for {nomor_peraturan}: {pdf_path}")
                return str(pdf_path)
            
            self._rate_limit()
            
            self.logger.info(f"Starting PDF download for {nomor_peraturan} from {pdf_url}")
            
            # Download dengan streaming
            response = self.session.get(
                pdf_url,
                timeout=self.config.REQUEST_TIMEOUT,
                verify=self.config.VERIFY_SSL,
                stream=True,
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type:
                self.logger.warning(
                    f"Downloaded content is not PDF (content-type: {content_type})"
                )
            
            # Check file size
            content_length = response.headers.get("content-length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.config.MAX_PDF_SIZE_MB:
                    self.logger.error(
                        f"PDF file too large ({size_mb:.2f} MB > {self.config.MAX_PDF_SIZE_MB} MB)"
                    )
                    return None
            
            # Write file dengan chunks
            downloaded_size = 0
            with open(pdf_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=self.config.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Safety check untuk total size
                        if downloaded_size > (self.config.MAX_PDF_SIZE_MB * 1024 * 1024):
                            pdf_path.unlink()
                            self.logger.error(f"PDF file exceeded max size limit during download")
                            return None
            
            # Verify downloaded file
            actual_size_mb = self.file_manager.get_file_size_mb(pdf_path)
            file_hash = self.file_manager.get_file_hash(pdf_path)
            
            self.logger.info(
                f"PDF downloaded successfully for {nomor_peraturan}: "
                f"{actual_size_mb:.2f} MB (hash: {file_hash})"
            )
            
            return str(pdf_path)
        
        except requests.RequestException as e:
            self.logger.error(f"Failed to download PDF from {pdf_url}: {e}")
            return None
        except IOError as e:
            self.logger.error(f"IO error while writing PDF file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during PDF download: {e}")
            return None
    
    def scrape_regulation(
        self,
        regulation_url: str,
        download_pdf: bool = True,
    ) -> Optional[LegalDocumentMetadata]:
        """
        Scrape satu regulation lengkap (metadata + relations + PDF).
        
        Args:
            regulation_url: URL detail peraturan
            download_pdf: Apakah download PDF juga
            
        Returns:
            LegalDocumentMetadata atau None jika gagal
        """
        try:
            # Fetch detail & metadata
            metadata = self.fetch_regulation_detail(regulation_url)
            
            # Download PDF jika diminta dan URL tersedia
            if download_pdf and metadata.pdf_url:
                pdf_path = self.download_pdf(
                    str(metadata.pdf_url),
                    metadata.nomor,
                )
                if pdf_path:
                    metadata.pdf_path = pdf_path
            
            return metadata
        
        except Exception as e:
            self.logger.error(f"Failed to scrape regulation from {regulation_url}: {e}")
            return None
    
    def scrape_all_regulations(
        self,
        max_pages: Optional[int] = None,
        download_pdf: bool = True,
    ) -> List[LegalDocumentMetadata]:
        """
        Scrape semua regulasi dari BPK portal dengan pagination.
        
        Args:
            max_pages: Maximum pages untuk di-scrape (default: config.MAX_PAGES_TO_SCRAPE)
            download_pdf: Apakah download PDF untuk setiap regulasi
            
        Returns:
            List of LegalDocumentMetadata
        """
        max_pages = max_pages or self.config.MAX_PAGES_TO_SCRAPE
        all_regulations = []
        
        try:
            page = 1
            while page <= max_pages:
                self.logger.info(f"Scraping page {page}...")
                
                try:
                    regulations_data, total_pages = self.fetch_regulation_list(page)
                    
                    if not regulations_data:
                        self.logger.info(f"No regulations found on page {page}. Stopping.")
                        break
                    
                    # Process setiap regulation di halaman
                    for reg_data in regulations_data:
                        if reg_data.get("url"):
                            metadata = self.scrape_regulation(
                                reg_data["url"],
                                download_pdf=download_pdf,
                            )
                            if metadata:
                                all_regulations.append(metadata)
                    
                    # Update relasi source_regulation
                    for regulation in all_regulations[-len(regulations_data):]:
                        for relation in regulation.relations:
                            relation.source_regulation = regulation.nomor
                    
                    # Check apakah sudah di page terakhir
                    if page >= total_pages:
                        break
                    
                    page += 1
                
                except Exception as e:
                    self.logger.error(f"Error processing page {page}: {e}")
                    page += 1
                    continue
        
        except Exception as e:
            self.logger.error(f"Fatal error during scraping all regulations: {e}")
        
        self.logger.info(
            f"Completed scraping. Total regulations: {len(all_regulations)}"
        )
        
        return all_regulations
    
    def close(self) -> None:
        """Close session dan cleanup resources."""
        if self.session:
            self.session.close()
            self.logger.info("BPK Crawler session closed")
