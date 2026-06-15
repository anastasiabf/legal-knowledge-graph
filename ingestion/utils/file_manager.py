"""
File management utilities untuk download dan storage PDF.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class FileManager:
    """Mengelola file operations untuk PDF storage dan retrieval."""
    
    def __init__(self, base_dir: str):
        """
        Initialize FileManager.
        
        Args:
            base_dir: Base directory untuk menyimpan files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_pdf_filename(self, nomor_peraturan: str) -> str:
        """
        Generate filename untuk PDF berdasarkan nomor peraturan.
        
        Args:
            nomor_peraturan: Nomor peraturan (e.g., "UU No. 11 Tahun 2008")
            
        Returns:
            Filename yang aman untuk filesistem
        """
        # Replace spasi dan karakter khusus
        safe_name = nomor_peraturan.replace(" ", "_").replace(".", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        return f"{safe_name}.pdf"
    
    def get_pdf_path(self, nomor_peraturan: str) -> Path:
        """
        Get full path untuk menyimpan PDF.
        
        Args:
            nomor_peraturan: Nomor peraturan
            
        Returns:
            Full path di base_dir
        """
        filename = self.get_pdf_filename(nomor_peraturan)
        return self.base_dir / filename
    
    def pdf_exists(self, nomor_peraturan: str) -> bool:
        """Check apakah PDF sudah di-download."""
        return self.get_pdf_path(nomor_peraturan).exists()
    
    def get_file_size_mb(self, file_path: Path) -> float:
        """Get ukuran file dalam MB."""
        if not file_path.exists():
            return 0.0
        return file_path.stat().st_size / (1024 * 1024)
    
    def get_file_hash(self, file_path: Path) -> str:
        """
        Hitung MD5 hash dari file untuk integrity checking.
        
        Args:
            file_path: Path ke file
            
        Returns:
            MD5 hash string
        """
        if not file_path.exists():
            return ""
        
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """
        Remove files older than specified days.
        
        Args:
            days_old: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_old)
        deleted_count = 0
        
        for pdf_file in self.base_dir.glob("*.pdf"):
            file_mtime = datetime.utcfromtimestamp(pdf_file.stat().st_mtime)
            if file_mtime < cutoff_time:
                pdf_file.unlink()
                deleted_count += 1
        
        return deleted_count
