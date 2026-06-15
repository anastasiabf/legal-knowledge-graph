"""
PDF Processor - Ekstraksi teks dari PDF peraturan

Mengekstrak:
- Struktur Bab dan Pasal
- Text per pasal beserta ayat-ayatnya
- Validasi struktur dokumen hukum
- Error handling untuk format PDF yang berbeda
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from ..models import (
    PDFExtractedContent,
    PasalContent,
)
from ..utils import get_logger


class PDFProcessor:
    """
    Processor untuk ekstraksi konten dari PDF peraturan.
    
    Fitur:
    - Multi-method support (PyMuPDF + PDFPlumber)
    - Structured extraction (Bab -> Pasal -> Ayat)
    - Regex-based pasal/ayat detection
    - Comprehensive error handling & warnings
    """
    
    # Regex patterns untuk detect struktur hukum
    BAB_PATTERN = re.compile(
        r"^BAB\s+([IVX]+|[0-9]+)\s*[:\-\.]?\s*(.*)$",
        re.MULTILINE | re.IGNORECASE
    )
    PASAL_PATTERN = re.compile(
        r"^(?:PASAL|Pasal|pasal)?\s*(\d+)\s*[:\-\.]?\s*(.*)$",
        re.MULTILINE
    )
    AYAT_PATTERN = re.compile(
        r"^\s*\((\d+)\)\s+(.+)$",
        re.MULTILINE
    )
    
    def __init__(self, method: str = "PyMuPDF"):
        """
        Initialize PDF Processor.
        
        Args:
            method: "PyMuPDF" atau "PDFPlumber"
        """
        self.method = method
        self.logger = get_logger(__name__)
        
        if method == "PyMuPDF" and fitz is None:
            self.logger.warning("PyMuPDF not installed, will try PDFPlumber")
            self.method = "PDFPlumber"
        
        if method == "PDFPlumber" and pdfplumber is None:
            self.logger.warning("PDFPlumber not installed, will try PyMuPDF")
            self.method = "PyMuPDF"
        
        if self.method == "PyMuPDF" and fitz is None:
            raise ImportError("Neither PyMuPDF nor PDFPlumber is installed")
    
    def extract(
        self,
        pdf_path: str,
        nomor_peraturan: str,
    ) -> PDFExtractedContent:
        """
        Extract konten lengkap dari PDF.
        
        Args:
            pdf_path: Path ke file PDF
            nomor_peraturan: Nomor peraturan (untuk metadata)
            
        Returns:
            PDFExtractedContent instance
        """
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.logger.info(f"Starting PDF extraction: {pdf_path} using {self.method}")
        
        try:
            if self.method == "PyMuPDF":
                return self._extract_with_pymupdf(pdf_file, nomor_peraturan)
            else:
                return self._extract_with_pdfplumber(pdf_file, nomor_peraturan)
        
        except Exception as e:
            self.logger.error(f"Error extracting PDF {pdf_path}: {e}")
            
            # Fallback ke method lain jika ada
            if self.method == "PyMuPDF" and pdfplumber is not None:
                self.logger.info("Retrying with PDFPlumber...")
                return self._extract_with_pdfplumber(pdf_file, nomor_peraturan)
            
            raise
    
    def _extract_with_pymupdf(
        self,
        pdf_file: Path,
        nomor_peraturan: str,
    ) -> PDFExtractedContent:
        """
        Extract menggunakan PyMuPDF (fitz).
        
        Args:
            pdf_file: Path ke PDF
            nomor_peraturan: Nomor peraturan
            
        Returns:
            PDFExtractedContent
        """
        if fitz is None:
            raise ImportError("PyMuPDF is not installed")
        
        doc = None
        try:
            doc = fitz.open(str(pdf_file))
            total_pages = doc.page_count
            
            # Extract teks dari semua halaman
            full_text = ""
            for page_num in range(total_pages):
                page = doc[page_num]
                full_text += page.get_text()
                full_text += "\n--- PAGE BREAK ---\n"
            
            # Parse struktur Bab dan Pasal
            chapters, all_pasals = self._parse_structure(full_text)
            
            result = PDFExtractedContent(
                nomor_peraturan=nomor_peraturan,
                pdf_path=str(pdf_file),
                total_pages=total_pages,
                chapters=chapters,
                all_pasals=all_pasals,
                raw_full_text=full_text,
                extraction_method="PyMuPDF",
            )
            
            self.logger.info(
                f"Successfully extracted PDF: {total_pages} pages, "
                f"{len(all_pasals)} pasals found"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"PyMuPDF extraction failed: {e}")
            raise
        
        finally:
            if doc:
                doc.close()
    
    def _extract_with_pdfplumber(
        self,
        pdf_file: Path,
        nomor_peraturan: str,
    ) -> PDFExtractedContent:
        """
        Extract menggunakan PDFPlumber.
        
        Args:
            pdf_file: Path ke PDF
            nomor_peraturan: Nomor peraturan
            
        Returns:
            PDFExtractedContent
        """
        if pdfplumber is None:
            raise ImportError("PDFPlumber is not installed")
        
        try:
            with pdfplumber.open(str(pdf_file)) as pdf:
                total_pages = len(pdf.pages)
                
                # Extract teks dari semua halaman
                full_text = ""
                for page_idx, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text += text
                    full_text += f"\n--- PAGE {page_idx} ---\n"
            
            # Parse struktur Bab dan Pasal
            chapters, all_pasals = self._parse_structure(full_text)
            
            result = PDFExtractedContent(
                nomor_peraturan=nomor_peraturan,
                pdf_path=str(pdf_file),
                total_pages=total_pages,
                chapters=chapters,
                all_pasals=all_pasals,
                raw_full_text=full_text,
                extraction_method="PDFPlumber",
            )
            
            self.logger.info(
                f"Successfully extracted PDF: {total_pages} pages, "
                f"{len(all_pasals)} pasals found"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"PDFPlumber extraction failed: {e}")
            raise
    
    def _parse_structure(self, text: str) -> Tuple[Dict[str, List[PasalContent]], List[PasalContent]]:
        """
        Parse struktur Bab dan Pasal dari text.
        
        Args:
            text: Full text dari PDF
            
        Returns:
            Tuple of (chapters dict, all_pasals list)
        """
        chapters: Dict[str, List[PasalContent]] = {}
        all_pasals: List[PasalContent] = []
        
        current_chapter = "PENDAHULUAN"
        pasal_counter = 0
        
        # Split text by lines untuk processing
        lines = text.split("\n")
        current_pasal_lines: List[str] = []
        current_pasal_num: Optional[str] = None
        
        for line in lines:
            line = line.strip()
            if not line or "---" in line:  # Skip empty dan page breaks
                continue
            
            # Check untuk BAB
            bab_match = self.BAB_PATTERN.match(line)
            if bab_match:
                # Save previous pasal jika ada
                if current_pasal_num and current_pasal_lines:
                    pasal = self._create_pasal_content(
                        current_pasal_num,
                        current_pasal_lines,
                        pasal_counter,
                    )
                    all_pasals.append(pasal)
                    if current_chapter not in chapters:
                        chapters[current_chapter] = []
                    chapters[current_chapter].append(pasal)
                    pasal_counter += 1
                    current_pasal_lines = []
                    current_pasal_num = None
                
                # Update current chapter
                bab_num = bab_match.group(1)
                bab_title = bab_match.group(2) if bab_match.group(2) else ""
                current_chapter = f"BAB {bab_num}"
                if bab_title:
                    current_chapter += f" {bab_title}"
                
                if current_chapter not in chapters:
                    chapters[current_chapter] = []
                
                continue
            
            # Check untuk PASAL
            pasal_match = self.PASAL_PATTERN.match(line)
            if pasal_match:
                # Save previous pasal
                if current_pasal_num and current_pasal_lines:
                    pasal = self._create_pasal_content(
                        current_pasal_num,
                        current_pasal_lines,
                        pasal_counter,
                    )
                    all_pasals.append(pasal)
                    if current_chapter not in chapters:
                        chapters[current_chapter] = []
                    chapters[current_chapter].append(pasal)
                    pasal_counter += 1
                
                # Start new pasal
                current_pasal_num = pasal_match.group(1)
                current_pasal_lines = [pasal_match.group(2)] if pasal_match.group(2) else []
                continue
            
            # Accumulate lines ke current pasal
            if current_pasal_num:
                current_pasal_lines.append(line)
        
        # Save last pasal
        if current_pasal_num and current_pasal_lines:
            pasal = self._create_pasal_content(
                current_pasal_num,
                current_pasal_lines,
                pasal_counter,
            )
            all_pasals.append(pasal)
            if current_chapter not in chapters:
                chapters[current_chapter] = []
            chapters[current_chapter].append(pasal)
        
        return chapters, all_pasals
    
    def _create_pasal_content(
        self,
        pasal_num: str,
        lines: List[str],
        order_index: int,
    ) -> PasalContent:
        """
        Create PasalContent object dari lines.
        
        Args:
            pasal_num: Nomor pasal
            lines: List of lines yang termasuk pasal ini
            order_index: Urutan pasal dalam dokumen
            
        Returns:
            PasalContent instance
        """
        full_text = " ".join(lines)
        
        # Extract ayat-ayat
        ayat_dict: Dict[str, str] = {}
        current_ayat_num = "1"
        
        for line in lines:
            ayat_match = self.AYAT_PATTERN.match(line)
            if ayat_match:
                current_ayat_num = ayat_match.group(1)
                ayat_dict[current_ayat_num] = ayat_match.group(2)
            else:
                # Append ke current ayat
                if current_ayat_num in ayat_dict:
                    ayat_dict[current_ayat_num] += f" {line}"
                else:
                    ayat_dict[current_ayat_num] = line
        
        # Jika tidak ada ayat yang terdeteksi, gunakan full text sebagai ayat 1
        if not ayat_dict:
            ayat_dict["1"] = full_text
        
        # Clean up ayat text
        for key in ayat_dict:
            ayat_dict[key] = " ".join(ayat_dict[key].split())  # normalize whitespace
        
        return PasalContent(
            nomor_pasal=pasal_num,
            ayat=ayat_dict,
            full_text=full_text,
            order_index=order_index,
        )
    
    def extract_pasal_by_number(
        self,
        pdf_content: PDFExtractedContent,
        pasal_num: str,
    ) -> Optional[PasalContent]:
        """
        Get pasal content by nomor pasal.
        
        Args:
            pdf_content: PDFExtractedContent dari ekstraksi sebelumnya
            pasal_num: Nomor pasal (e.g., "27")
            
        Returns:
            PasalContent atau None jika tidak ditemukan
        """
        for pasal in pdf_content.all_pasals:
            if pasal.nomor_pasal == pasal_num:
                return pasal
        
        return None
    
    def get_pasal_text_for_embedding(
        self,
        pasal: PasalContent,
    ) -> str:
        """
        Get text pasal yang siap untuk embedding ke vector store.
        
        Args:
            pasal: PasalContent
            
        Returns:
            Formatted text untuk embedding
        """
        # Format: "Pasal [nomor]: [full text]"
        return f"Pasal {pasal.nomor_pasal}: {pasal.full_text}"
    
    def validate_extraction(
        self,
        pdf_content: PDFExtractedContent,
    ) -> Tuple[bool, List[str]]:
        """
        Validate hasil ekstraksi PDF.
        
        Args:
            pdf_content: PDFExtractedContent hasil ekstraksi
            
        Returns:
            Tuple of (is_valid, list of warnings/errors)
        """
        issues = []
        
        # Check minimal content
        if not pdf_content.raw_full_text or len(pdf_content.raw_full_text) < 100:
            issues.append("PDF content terlalu kecil atau kosong")
        
        if not pdf_content.all_pasals:
            issues.append("Tidak ada pasal yang terdeteksi dalam PDF")
        
        # Check untuk anomali dalam struktur
        if pdf_content.total_pages == 0:
            issues.append("PDF tidak memiliki halaman")
        
        if len(pdf_content.all_pasals) > 1000:
            issues.append(f"Jumlah pasal mencurigakan: {len(pdf_content.all_pasals)}")
        
        # Check untuk empty chapters
        empty_chapters = [ch for ch, pasals in pdf_content.chapters.items() if not pasals]
        if empty_chapters:
            issues.append(f"Chapters kosong: {', '.join(empty_chapters)}")
        
        is_valid = len(issues) == 0
        
        return is_valid, issues


def batch_extract_pdfs(
    pdf_paths: List[str],
    nomor_peraturan_map: Dict[str, str],
    method: str = "PyMuPDF",
) -> List[PDFExtractedContent]:
    """
    Batch extract multiple PDF files.
    
    Args:
        pdf_paths: List of PDF file paths
        nomor_peraturan_map: Dict mapping pdf_path -> nomor_peraturan
        method: Extraction method
        
    Returns:
        List of PDFExtractedContent
    """
    processor = PDFProcessor(method=method)
    results = []
    
    for pdf_path in pdf_paths:
        try:
            nomor = nomor_peraturan_map.get(pdf_path, Path(pdf_path).stem)
            content = processor.extract(pdf_path, nomor)
            results.append(content)
        except Exception as e:
            get_logger(__name__).error(f"Failed to extract {pdf_path}: {e}")
            continue
    
    return results
