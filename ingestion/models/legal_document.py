"""
Pydantic models untuk struktur dokumen hukum.
Memastikan type safety dan validasi data untuk scraping & PDF extraction.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class LegalDocumentStatusEnum(str, Enum):
    """Status hubungan hukum antar peraturan."""
    AKTIF = "AKTIF"
    DICABUT = "DICABUT"
    DIUBAH = "DIUBAH"
    MENGUBAH = "MENGUBAH"
    MENCABUT = "MENCABUT"
    DASAR_DELEGASI = "DASAR_DELEGASI"


class LegalDocumentRelation(BaseModel):
    """Representasi relasi antar peraturan (e.g., mencabut, mengubah)."""
    
    source_regulation: str = Field(..., description="Nomor peraturan sumber")
    target_regulation: str = Field(..., description="Nomor peraturan target")
    relation_type: LegalDocumentStatusEnum = Field(..., description="Tipe relasi")
    description: Optional[str] = Field(None, description="Deskripsi relasi")
    
    class Config:
        use_enum_values = True


class LegalDocumentMetadata(BaseModel):
    """Metadata lengkap dari peraturan yang diunduh dari BPK portal."""
    
    judul: str = Field(..., description="Judul peraturan")
    nomor: str = Field(..., description="Nomor peraturan (e.g., 'UU No. 11 Tahun 2008')")
    tahun: int = Field(..., description="Tahun peraturan diterbitkan")
    jenis: str = Field(..., description="Jenis peraturan (UU, PP, PERPRES, PERMEN, Perda, dll)")
    tanggal_disahkan: Optional[datetime] = Field(None, description="Tanggal disahkan")
    tanggal_diundangkan: Optional[datetime] = Field(None, description="Tanggal diundangkan")
    lembaga_penerbit: Optional[str] = Field(None, description="Lembaga yang menerbitkan")
    url: Optional[HttpUrl] = Field(None, description="URL peraturan di portal BPK")
    pdf_url: Optional[HttpUrl] = Field(None, description="URL PDF peraturan")
    pdf_path: Optional[str] = Field(None, description="Path lokal file PDF yang diunduh")
    
    # Relasi dengan peraturan lain
    relations: List[LegalDocumentRelation] = Field(
        default_factory=list,
        description="Relasi dengan peraturan lain (mencabut, mengubah, dll)"
    )
    
    # Metadata teknis
    source_scraped_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Waktu data di-scrape"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Waktu terakhir diupdate"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "judul": "Undang-Undang tentang Informasi dan Transaksi Elektronik",
                "nomor": "UU No. 11 Tahun 2008",
                "tahun": 2008,
                "jenis": "UU",
                "tanggal_disahkan": "2008-04-21",
                "lembaga_penerbit": "Presiden Republik Indonesia",
                "url": "https://peraturan.bpk.go.id/Details/...",
                "pdf_url": "https://peraturan.bpk.go.id/Files/...",
            }
        }


class PasalContent(BaseModel):
    """Struktur konten pasal dari PDF."""
    
    nomor_pasal: str = Field(..., description="Nomor pasal (e.g., '27')")
    judul: Optional[str] = Field(None, description="Judul pasal jika ada")
    ayat: Dict[str, str] = Field(
        default_factory=dict,
        description="Ayat-ayat dengan format {'1': 'text ayat 1', '2': 'text ayat 2'}"
    )
    full_text: str = Field(..., description="Teks lengkap pasal including semua ayat")
    order_index: int = Field(..., description="Urutan pasal dalam dokumen")


class PDFExtractedContent(BaseModel):
    """Hasil ekstraksi lengkap dari PDF peraturan."""
    
    nomor_peraturan: str = Field(..., description="Nomor peraturan (dari metadata)")
    pdf_path: str = Field(..., description="Path file PDF yang diekstrak")
    total_pages: int = Field(..., description="Total halaman PDF")
    
    # Struktur bab dan pasal
    chapters: Dict[str, List[PasalContent]] = Field(
        default_factory=dict,
        description="Struktur bab -> [daftar pasal]"
    )
    all_pasals: List[PasalContent] = Field(
        default_factory=list,
        description="Daftar semua pasal dalam urutan"
    )
    
    # Metadata ekstraksi
    extraction_method: str = Field(
        default="PyMuPDF",
        description="Metode ekstraksi yang digunakan"
    )
    raw_full_text: str = Field(..., description="Teks mentah dari seluruh PDF")
    
    # Error & warning
    extraction_warnings: List[str] = Field(
        default_factory=list,
        description="Warning selama proses ekstraksi"
    )
    is_valid: bool = Field(
        default=True,
        description="Apakah ekstraksi valid dan siap proses"
    )
    
    # Metadata teknis
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Waktu ekstraksi dilakukan"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "nomor_peraturan": "UU No. 11 Tahun 2008",
                "pdf_path": "/data/uu_11_2008.pdf",
                "total_pages": 25,
                "chapters": {
                    "BAB I": [
                        {
                            "nomor_pasal": "1",
                            "full_text": "...",
                            "ayat": {"1": "...", "2": "..."},
                            "order_index": 0
                        }
                    ]
                }
            }
        }
