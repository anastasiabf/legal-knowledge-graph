"""
LLM Extractor menggunakan Google Gemini 1.5 Pro untuk structured extraction.

Fitur:
- Batch processing dengan token management
- Structured output menggunakan Pydantic
- Retry logic untuk API failures
- Cost tracking & optimization
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

try:
    from google.generativeai import GenerativeModel, configure
    from google.api_core.exceptions import GoogleAPIError
except ImportError:
    GenerativeModel = None
    configure = None
    GoogleAPIError = Exception

from extraction.models import (
    LegalEntity,
    PasalReference,
    KonsepHukum,
    EnrichedPasalContent,
)
from ingestion.utils import get_logger


class GeminiLLMExtractor:
    """
    LLM Extractor menggunakan Google Gemini 1.5 Pro untuk extraction tugas hukum.
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize Gemini extractor.
        
        Args:
            api_key: Google Gemini API key
            model: Model name (default: gemini-1.5-pro)
        """
        if not GenerativeModel:
            raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
        
        self.api_key = api_key
        self.model_name = model
        self.logger = get_logger(__name__)
        
        # Configure API
        configure(api_key=api_key)
        self.client = GenerativeModel(model)
        
        # Token tracking
        self.total_tokens_used = 0
        self.api_calls = 0
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
    
    def extract_entities_from_pasal(
        self,
        nomor_pasal: str,
        pasal_text: str,
    ) -> Tuple[List[LegalEntity], List[str]]:
        """
        Extract legal entities (KonsepHukum) dari text pasal.
        
        Args:
            nomor_pasal: Nomor pasal
            pasal_text: Full text pasal
            
        Returns:
            Tuple of (list of entities, warnings)
        """
        warnings = []
        
        try:
            # Create extraction prompt
            prompt = self._create_entity_extraction_prompt(nomor_pasal, pasal_text)
            
            # Call Gemini API dengan retry
            response = self._call_gemini_api(prompt)
            
            # Parse response
            entities = self._parse_entity_response(response, nomor_pasal, pasal_text)
            
            return entities, warnings
        
        except Exception as e:
            self.logger.error(f"Error extracting entities from Pasal {nomor_pasal}: {e}")
            warnings.append(f"Entity extraction failed: {str(e)}")
            return [], warnings
    
    def extract_pasal_references(
        self,
        nomor_pasal: str,
        pasal_text: str,
    ) -> Tuple[List[PasalReference], List[str]]:
        """
        Extract references ke pasal lain (MERUJUK_KE) dari text.
        
        Args:
            nomor_pasal: Nomor pasal
            pasal_text: Full text pasal
            
        Returns:
            Tuple of (list of references, warnings)
        """
        warnings = []
        
        try:
            # Create reference extraction prompt
            prompt = self._create_reference_extraction_prompt(nomor_pasal, pasal_text)
            
            # Call Gemini API
            response = self._call_gemini_api(prompt)
            
            # Parse response
            references = self._parse_reference_response(response, nomor_pasal)
            
            return references, warnings
        
        except Exception as e:
            self.logger.error(f"Error extracting references from Pasal {nomor_pasal}: {e}")
            warnings.append(f"Reference extraction failed: {str(e)}")
            return [], warnings
    
    def extract_legal_concepts(
        self,
        nomor_peraturan: str,
        document_text: str,
    ) -> Tuple[List[KonsepHukum], List[str]]:
        """
        Extract legal concepts (KonsepHukum) dari seluruh dokumen.
        
        Args:
            nomor_peraturan: Nomor peraturan
            document_text: Full document text
            
        Returns:
            Tuple of (list of concepts, warnings)
        """
        warnings = []
        
        try:
            # Create concept extraction prompt
            prompt = self._create_concept_extraction_prompt(nomor_peraturan, document_text)
            
            # Call Gemini API
            response = self._call_gemini_api(prompt)
            
            # Parse response
            concepts = self._parse_concept_response(response)
            
            return concepts, warnings
        
        except Exception as e:
            self.logger.error(f"Error extracting legal concepts: {e}")
            warnings.append(f"Concept extraction failed: {str(e)}")
            return [], warnings
    
    def _create_entity_extraction_prompt(self, nomor_pasal: str, pasal_text: str) -> str:
        """Create prompt untuk entity extraction."""
        return f"""
Sebagai ahli hukum Indonesia, ekstrak semua konsep hukum (legal entities/concepts) dari pasal berikut.

PASAL {nomor_pasal}:
{pasal_text}

Untuk setiap entity yang ditemukan, berikan dalam format JSON:
{{
  "entities": [
    {{
      "text": "nama entity",
      "entity_type": "jenis entity (e.g., Konsep, Lembaga, Tindakan Hukum, dll)",
      "confidence": 0.9,
      "context": "snippet teks yang melingkupi entity"
    }}
  ]
}}

Fokus pada:
1. Konsep hukum utama (Transaksi Elektronik, Informasi Elektronik, dll)
2. Lembaga/Pejabat (Presiden, Menteri, dll)
3. Tindakan hukum (mengatur, mencabut, mengubah, dll)
4. Istilah teknis hukum

Pastikan confidence score akurat (0-1).
"""
    
    def _create_reference_extraction_prompt(self, nomor_pasal: str, pasal_text: str) -> str:
        """Create prompt untuk reference extraction."""
        return f"""
Sebagai ahli hukum Indonesia, identifikasi semua referensi ke pasal lain dalam teks berikut.

PASAL {nomor_pasal}:
{pasal_text}

Untuk setiap referensi, berikan dalam format JSON:
{{
  "references": [
    {{
      "target_pasal": "nomor pasal yang dirujuk (e.g., '27', '10', dll)",
      "reference_type": "MERUJUK_KE",
      "reference_text": "teks yang menunjukkan referensi",
      "confidence": 0.95
    }}
  ]
}}

Cari pola seperti:
- "Sebagaimana dimaksud dalam Pasal X..."
- "Sebagaimana diatur dalam Pasal X..."
- "Lihat Pasal X..."
- "Pasal X ayat Y"
- Referensi eksplisit ke pasal lain

Kembali dengan JSON yang valid.
"""
    
    def _create_concept_extraction_prompt(self, nomor_peraturan: str, document_text: str) -> str:
        """Create prompt untuk concept extraction dari seluruh dokumen."""
        # Truncate text jika terlalu panjang untuk context window
        max_chars = 100000
        truncated_text = document_text[:max_chars]
        if len(document_text) > max_chars:
            truncated_text += f"\n... (Document truncated, total {len(document_text)} chars)"
        
        return f"""
Sebagai ahli hukum Indonesia, ekstrak konsep hukum utama dari peraturan berikut.

PERATURAN: {nomor_peraturan}

{truncated_text}

Identifikasi 5-20 konsep hukum utama yang diatur peraturan ini. Untuk setiap konsep:

{{
  "concepts": [
    {{
      "nama": "nama konsep",
      "definisi": "definisi singkat",
      "pasal_utama": "pasal nomor yang utama mengatur konsep ini",
      "frequency": "berapa kali konsep muncul dalam dokumen (estimasi)",
      "confidence": 0.9
    }}
  ]
}}

Contoh konsep: Transaksi Elektronik, Informasi Elektronik, Tanda Tangan Elektronik, dll.

Return JSON yang valid dan minimal 3 konsep.
"""
    
    def _call_gemini_api(self, prompt: str) -> str:
        """
        Call Gemini API dengan retry logic.
        
        Args:
            prompt: Prompt untuk API
            
        Returns:
            Response text dari API
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Calling Gemini API (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,  # Lower untuk consistency
                        "top_p": 0.8,
                        "max_output_tokens": 2048,
                    }
                )
                
                # Track API calls dan estimate tokens
                self.api_calls += 1
                # Rough estimate: input + output tokens
                estimated_tokens = len(prompt.split()) + len(response.text.split())
                self.total_tokens_used += estimated_tokens
                
                return response.text
            
            except GoogleAPIError as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"Gemini API error (attempt {attempt + 1}): {e}. Retrying..."
                    )
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise
            
            except Exception as e:
                self.logger.error(f"Unexpected error calling Gemini API: {e}")
                raise
    
    def _parse_entity_response(
        self,
        response: str,
        nomor_pasal: str,
        pasal_text: str,
    ) -> List[LegalEntity]:
        """Parse entity extraction response dari Gemini."""
        entities = []
        
        try:
            # Extract JSON dari response
            json_str = self._extract_json_from_response(response)
            data = json.loads(json_str)
            
            for entity_data in data.get("entities", []):
                entity = LegalEntity(
                    text=entity_data.get("text", ""),
                    entity_type=entity_data.get("entity_type", "Konsep"),
                    pasal_nomor=nomor_pasal,
                    confidence=float(entity_data.get("confidence", 0.5)),
                    context=entity_data.get("context", pasal_text[:200]),
                )
                entities.append(entity)
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Error parsing entity response: {e}")
        
        return entities
    
    def _parse_reference_response(
        self,
        response: str,
        nomor_pasal: str,
    ) -> List[PasalReference]:
        """Parse reference extraction response."""
        references = []
        
        try:
            json_str = self._extract_json_from_response(response)
            data = json.loads(json_str)
            
            for ref_data in data.get("references", []):
                reference = PasalReference(
                    source_pasal=nomor_pasal,
                    target_pasal=ref_data.get("target_pasal", ""),
                    reference_type=ref_data.get("reference_type", "MERUJUK_KE"),
                    reference_text=ref_data.get("reference_text", ""),
                    confidence=float(ref_data.get("confidence", 0.5)),
                )
                references.append(reference)
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Error parsing reference response: {e}")
        
        return references
    
    def _parse_concept_response(self, response: str) -> List[KonsepHukum]:
        """Parse concept extraction response."""
        concepts = []
        
        try:
            json_str = self._extract_json_from_response(response)
            data = json.loads(json_str)
            
            for concept_data in data.get("concepts", []):
                concept = KonsepHukum(
                    nama=concept_data.get("nama", ""),
                    definisi=concept_data.get("definisi"),
                    pasal_utama=concept_data.get("pasal_utama", ""),
                    frequency=int(concept_data.get("frequency", 1)),
                    confidence=float(concept_data.get("confidence", 0.5)),
                )
                concepts.append(concept)
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Error parsing concept response: {e}")
        
        return concepts
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON object dari response yang mungkin mengandung text lain.
        
        Args:
            response: Response text dari API
            
        Returns:
            JSON string
        """
        # Find JSON object dalam response
        import re
        
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # Fallback: assume entire response is JSON
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics tentang API usage."""
        return {
            "api_calls": self.api_calls,
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost_usd": self.total_tokens_used * 0.0015 / 1000,  # Rough estimate
            "model": self.model_name,
        }
