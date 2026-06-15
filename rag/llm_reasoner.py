"""
LLM Reasoner for RAG

Performs LLM-based reasoning over retrieved context using Google Gemini.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging
from datetime import datetime
import json
import re

import google.generativeai as genai


logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    """Result from LLM reasoning."""
    answer: str
    reasoning_steps: List[str] = field(default_factory=list)
    sources: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    tokens_used: int = 0
    model: str = "gemini-1.5-pro"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "answer": self.answer,
            "reasoning_steps": self.reasoning_steps,
            "sources": self.sources,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
        }


class LLMReasoner:
    """
    LLM-based reasoner for legal document Q&A.
    
    Uses Google Gemini 1.5 Pro with chain-of-thought reasoning.
    """
    
    # Prompt templates
    SYSTEM_PROMPT = """Anda adalah ahli hukum Indonesia yang berpengalaman. Tugas Anda adalah:
1. Menjawab pertanyaan hukum berdasarkan konteks regulasi yang diberikan
2. Menjelaskan dasar hukum dengan merujuk pada pasal spesifik
3. Mengidentifikasi hubungan antar peraturan
4. Memberikan analisis yang komprehensif namun jelas

Panduan:
- Selalu merujuk pada pasal/peraturan spesifik
- Jelaskan implikasi hukum dari pertanyaan
- Identifikasi ketentuan terkait yang relevan
- Berikan kesimpulan yang didukung oleh teks regulasi
- Jika ada ketidakpastian, nyatakan dengan jelas

Format jawaban:
1. Kesimpulan utama (1-2 kalimat)
2. Dasar hukum (pasal-pasal relevan)
3. Penjelasan detail
4. Implikasi atau catatan penting"""

    REASONING_PROMPT = """Berdasarkan konteks hukum di bawah ini, jawab pertanyaan berikut dengan analisis mendalam:

KONTEKS:
{context}

PERTANYAAN: {question}

Langkah-langkah analisis:
1. Identifikasi isu hukum utama dari pertanyaan
2. Cari ketentuan relevan dalam konteks
3. Analisis penerapan ketentuan tersebut
4. Pertimbangkan hubungan dengan peraturan terkait
5. Berikan kesimpulan dengan dasar hukum yang jelas

JAWABAN:"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize LLM reasoner.
        
        Args:
            api_key: Google Gemini API key
            model: Model to use (default: gemini-1.5-pro)
        """
        genai.configure(api_key=api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model_name=model)
        self.reasoning_history: List[ReasoningResult] = []
    
    def reason(
        self,
        question: str,
        context: str,
        retrieve_reasoning_steps: bool = True,
        confidence_threshold: float = 0.5,
    ) -> ReasoningResult:
        """
        Perform reasoning over context.
        
        Args:
            question: User question
            context: Context from retriever (formatted)
            retrieve_reasoning_steps: Extract reasoning steps
            confidence_threshold: Minimum confidence for answer
            
        Returns:
            ReasoningResult with answer and metadata
        """
        try:
            # Build prompt
            prompt = self.REASONING_PROMPT.format(
                context=context,
                question=question,
            )
            
            # Call Gemini API
            response = self.model.generate_content(
                [self.SYSTEM_PROMPT, prompt],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                    top_p=0.8,
                ),
            )
            
            answer = response.text
            
            # Extract reasoning steps if requested
            reasoning_steps = []
            if retrieve_reasoning_steps:
                reasoning_steps = self._extract_reasoning_steps(answer)
            
            # Calculate confidence based on answer quality
            confidence = self._calculate_confidence(answer, question)
            
            # Extract sources from answer
            sources = self._extract_sources(answer)
            
            # Estimate token usage
            tokens_used = self._estimate_tokens(prompt + answer)
            
            result = ReasoningResult(
                answer=answer,
                reasoning_steps=reasoning_steps,
                sources=sources,
                confidence=confidence,
                tokens_used=tokens_used,
                model=self.model_name,
            )
            
            self.reasoning_history.append(result)
            
            logger.info(f"Reasoning completed: {confidence:.1%} confidence, {tokens_used} tokens")
            
            return result
            
        except Exception as e:
            logger.error(f"Reasoning failed: {e}", exc_info=True)
            return ReasoningResult(
                answer=f"Error: {str(e)}",
                confidence=0.0,
            )
    
    def reason_with_followup(
        self,
        question: str,
        context: str,
        followup_question: str = None,
    ) -> Tuple[ReasoningResult, Optional[ReasoningResult]]:
        """
        Perform reasoning with optional follow-up question.
        
        Args:
            question: Initial question
            context: Context
            followup_question: Follow-up question (optional)
            
        Returns:
            Tuple of (initial_result, followup_result)
        """
        # Initial reasoning
        initial_result = self.reason(question, context)
        
        followup_result = None
        if followup_question:
            # For follow-up, include previous answer in context
            enhanced_context = f"{context}\n\n[JAWABAN SEBELUMNYA]\n{initial_result.answer}"
            followup_result = self.reason(followup_question, enhanced_context)
        
        return initial_result, followup_result
    
    def create_summary(
        self, context: str, max_length: int = 500
    ) -> str:
        """
        Create summary of retrieved context.
        
        Args:
            context: Context to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summary text
        """
        try:
            prompt = f"""Buatlah ringkasan singkat (maksimal {max_length} kata) dari teks hukum berikut:

{context}

Ringkasan harus:
1. Menangkap poin-poin utama
2. Mempertahankan ketentuan penting
3. Jelas dan mudah dipahami
4. Dalam bahasa Indonesia yang baik

RINGKASAN:"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=int(max_length / 2.5),
                ),
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return ""
    
    def extract_key_points(
        self, context: str, num_points: int = 5
    ) -> List[str]:
        """
        Extract key points from context.
        
        Args:
            context: Context text
            num_points: Number of key points to extract
            
        Returns:
            List of key points
        """
        try:
            prompt = f"""Ekstrak {num_points} poin utama dari teks hukum berikut:

{context}

Poin-poin harus:
1. Spesifik dan relevan
2. Menggunakan bahasa hukum yang tepat
3. Direferensikan ke pasal/ayat jika memungkinkan

Format: Berikan sebagai numbered list.

POIN-POIN UTAMA:"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1024,
                ),
            )
            
            # Parse numbered list
            points = self._parse_numbered_list(response.text)
            return points[:num_points]
            
        except Exception as e:
            logger.error(f"Key point extraction failed: {e}")
            return []
    
    def _extract_reasoning_steps(self, answer: str) -> List[str]:
        """Extract numbered reasoning steps from answer."""
        steps = []
        
        # Look for numbered items (1., 2., etc.) or bullet points
        patterns = [
            r'^\s*\d+\.\s+(.+?)(?=\n\d+\.|$)',
            r'^\s*-\s+(.+?)(?=\n-|$)',
            r'^\s*•\s+(.+?)(?=\n•|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, answer, re.MULTILINE)
            if matches:
                steps.extend([m.strip() for m in matches])
        
        return steps[:5]  # Top 5 steps
    
    def _calculate_confidence(self, answer: str, question: str) -> float:
        """Calculate confidence score for answer."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence if answer references specific articles
        if re.search(r'\bPasal\s+\d+', answer, re.IGNORECASE):
            confidence += 0.2
        
        # Increase if cites multiple sources
        if len(re.findall(r'\bPasal\s+\d+', answer, re.IGNORECASE)) > 2:
            confidence += 0.1
        
        # Decrease if contains uncertainty indicators
        uncertainty_words = ["mungkin", "kemungkinan", "tidak jelas", "sulit", "pasti"]
        if any(word in answer.lower() for word in uncertainty_words):
            confidence -= 0.1
        
        # Ensure 0-1 range
        return max(0.0, min(1.0, confidence))
    
    def _extract_sources(self, answer: str) -> List[Dict]:
        """Extract sources (pasal references) from answer."""
        sources = []
        
        # Find pasal references
        matches = re.finditer(r'Pasal\s+(\d+(?:\s*,\s*\d+)*)', answer, re.IGNORECASE)
        
        for match in matches:
            pasal_text = match.group(1)
            # Extract individual pasal numbers
            pasal_numbers = re.findall(r'\d+', pasal_text)
            
            for num in pasal_numbers:
                if not any(s["pasal"] == num for s in sources):
                    sources.append({
                        "pasal": num,
                        "type": "Pasal",
                    })
        
        return sources[:10]  # Top 10 sources
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: Indonesian text)."""
        # Rough estimate for Indonesian: 1 token ≈ 4-5 characters
        return max(1, len(text) // 4)
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """Parse numbered list from text."""
        items = []
        
        # Match numbered items (1., 2., etc.)
        matches = re.findall(r'^\s*\d+\.\s+(.+?)(?=\n\s*\d+\.|$)', text, re.MULTILINE)
        
        return [m.strip() for m in matches]
    
    def get_stats(self) -> Dict:
        """Get reasoning statistics."""
        if not self.reasoning_history:
            return {}
        
        return {
            "total_reasonings": len(self.reasoning_history),
            "avg_confidence": sum(r.confidence for r in self.reasoning_history) / len(self.reasoning_history),
            "total_tokens": sum(r.tokens_used for r in self.reasoning_history),
            "last_reasoning": self.reasoning_history[-1].to_dict() if self.reasoning_history else {},
        }
