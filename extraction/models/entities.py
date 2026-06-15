"""
Pydantic models untuk entities dan extraction results.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class LegalEntity(BaseModel):
    """Representasi entity hukum yang diekstrak dari pasal."""
    
    text: str = Field(..., description="Text dari entity")
    entity_type: str = Field(..., description="Tipe entity (e.g., Konsep, Lembaga, dll)")
    pasal_nomor: str = Field(..., description="Nomor pasal tempat entity ditemukan")
    confidence: float = Field(
        ...,
        description="Confidence score (0-1)",
        ge=0.0,
        le=1.0
    )
    context: Optional[str] = Field(None, description="Context snippet dari pasal")


class PasalReference(BaseModel):
    """Representasi reference antar pasal (MERUJUK_KE)."""
    
    source_pasal: str = Field(..., description="Nomor pasal sumber")
    target_pasal: str = Field(..., description="Nomor pasal target")
    reference_type: str = Field(
        default="MERUJUK_KE",
        description="Tipe referensi (MERUJUK_KE, MENGACU_PADA, dll)"
    )
    reference_text: str = Field(
        ...,
        description="Teks yang menunjukkan referensi"
    )
    confidence: float = Field(
        ...,
        description="Confidence score (0-1)",
        ge=0.0,
        le=1.0
    )


class KonsepHukum(BaseModel):
    """Representasi konsep hukum yang diekstrak."""
    
    nama: str = Field(..., description="Nama konsep hukum")
    definisi: Optional[str] = Field(None, description="Definisi dari konsep")
    pasal_utama: str = Field(
        ...,
        description="Nomor pasal utama yang mengatur konsep ini"
    )
    terkait_pasals: List[str] = Field(
        default_factory=list,
        description="Daftar pasal terkait"
    )
    frequency: int = Field(
        default=1,
        description="Frekuensi kemunculan dalam dokumen"
    )
    confidence: float = Field(
        ...,
        description="Confidence score (0-1)",
        ge=0.0,
        le=1.0
    )


class EnrichedPasalContent(BaseModel):
    """Pasal content yang sudah di-enrich dengan entities dan references."""
    
    nomor_pasal: str = Field(..., description="Nomor pasal")
    full_text: str = Field(..., description="Full text pasal")
    ayat: Dict[str, str] = Field(..., description="Ayat breakdown")
    
    # Enriched data
    entities: List[LegalEntity] = Field(
        default_factory=list,
        description="Entities yang diekstrak dari pasal"
    )
    references: List[PasalReference] = Field(
        default_factory=list,
        description="References ke pasal lain"
    )
    konsep_hukum: List[KonsepHukum] = Field(
        default_factory=list,
        description="Konsep hukum yang diatur pasal ini"
    )
    
    # Metadata
    extraction_method: str = Field(
        default="Gemini-1.5-Pro",
        description="Method yang digunakan untuk extraction"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Waktu extraction"
    )
    extraction_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings dari extraction process"
    )


class EnrichedDocumentContent(BaseModel):
    """Dokumen yang sudah di-enrich dengan entities dan references."""
    
    nomor_peraturan: str = Field(..., description="Nomor peraturan")
    pdf_path: str = Field(..., description="Path ke PDF sumber")
    
    # Enriched pasals
    enriched_pasals: List[EnrichedPasalContent] = Field(
        ...,
        description="Semua pasal dengan enrichment"
    )
    
    # Global entities
    all_entities: List[LegalEntity] = Field(
        default_factory=list,
        description="Semua entities dari dokumen"
    )
    
    # Global relationships
    all_references: List[PasalReference] = Field(
        default_factory=list,
        description="Semua references dari dokumen"
    )
    
    # Legal concepts
    konsep_hukum_list: List[KonsepHukum] = Field(
        default_factory=list,
        description="Konsep-konsep hukum dalam dokumen"
    )
    
    # Metadata
    total_entities: int = Field(default=0, description="Total entities")
    total_references: int = Field(default=0, description="Total references")
    total_konsep: int = Field(default=0, description="Total konsep hukum")
    
    extraction_method: str = Field(
        default="Gemini-1.5-Pro",
        description="LLM yang digunakan"
    )
    enrichment_started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Waktu enrichment dimulai"
    )
    enrichment_completed_at: Optional[datetime] = Field(
        None,
        description="Waktu enrichment selesai"
    )
    total_tokens_used: int = Field(
        default=0,
        description="Total tokens digunakan di LLM API"
    )
