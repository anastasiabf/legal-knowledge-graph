"""
Context Manager for RAG

Manages context windows, chunking, and optimization for LLM processing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    """Single chunk of context."""
    content: str
    chunk_id: int
    source_pasal: str
    source_peraturan: str
    start_position: int
    end_position: int
    relevance_score: float = 1.0
    order_in_window: int = 0
    
    def token_count(self) -> int:
        """Estimate token count (rough: 1 token ≈ 4 chars for Indonesian)."""
        return len(self.content) // 4
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "chunk_id": self.chunk_id,
            "source_pasal": self.source_pasal,
            "source_peraturan": self.source_peraturan,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "relevance_score": self.relevance_score,
            "order_in_window": self.order_in_window,
            "token_count": self.token_count(),
        }


@dataclass
class ContextWindow:
    """Context window for LLM processing."""
    chunks: List[ContextChunk]
    window_id: str
    max_tokens: int
    used_tokens: int = 0
    available_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def get_content(self) -> str:
        """Get concatenated context content."""
        return "\n\n".join(chunk.content for chunk in self.chunks)
    
    def get_summary(self) -> str:
        """Get summary of context window."""
        return f"ContextWindow(id={self.window_id}, chunks={len(self.chunks)}, tokens={self.used_tokens}/{self.max_tokens})"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "window_id": self.window_id,
            "chunks": [c.to_dict() for c in self.chunks],
            "max_tokens": self.max_tokens,
            "used_tokens": self.used_tokens,
            "available_tokens": self.available_tokens,
            "metadata": self.metadata,
        }


class ContextManager:
    """
    Manages context windows for LLM processing.
    
    Features:
    - Automatic chunking of long documents
    - Context window optimization
    - Token count management
    - Relevance-based ordering
    """
    
    def __init__(
        self,
        max_context_tokens: int = 4000,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize context manager.
        
        Args:
            max_context_tokens: Maximum tokens for context window
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.max_context_tokens = max_context_tokens
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.windows_history: List[ContextWindow] = []
    
    def create_context_window(
        self,
        retrieved_documents: List,
        query: str = "",
    ) -> ContextWindow:
        """
        Create optimized context window from retrieved documents.
        
        Args:
            retrieved_documents: List of RetrievedDocument objects
            query: Original query for context
            
        Returns:
            Optimized ContextWindow
        """
        chunks = []
        chunk_id = 0
        total_tokens = 0
        
        # Process each document
        for doc in retrieved_documents:
            # Chunk long document texts
            doc_chunks = self._chunk_document(
                doc.pasal_text,
                doc.nomor_pasal,
                doc.nomor_peraturan,
                doc.score,
                chunk_id,
            )
            
            # Add chunks to window if space available
            for chunk in doc_chunks:
                chunk_tokens = chunk.token_count()
                
                if total_tokens + chunk_tokens <= self.max_context_tokens:
                    chunks.append(chunk)
                    total_tokens += chunk_tokens
                    chunk_id += 1
                else:
                    # Window full
                    break
            
            if total_tokens >= self.max_context_tokens:
                break
        
        # Sort chunks by relevance score (descending)
        chunks = sorted(chunks, key=lambda x: x.relevance_score, reverse=True)
        
        # Assign order in window
        for i, chunk in enumerate(chunks, 1):
            chunk.order_in_window = i
        
        # Create window
        window = ContextWindow(
            chunks=chunks,
            window_id=self._generate_window_id(),
            max_tokens=self.max_context_tokens,
            used_tokens=total_tokens,
            available_tokens=self.max_context_tokens - total_tokens,
            metadata={
                "query": query,
                "num_documents": len(retrieved_documents),
            }
        )
        
        self.windows_history.append(window)
        
        logger.info(f"Created context window: {window.get_summary()}")
        
        return window
    
    def _chunk_document(
        self,
        text: str,
        pasal_nomor: str,
        peraturan_nomor: str,
        relevance_score: float,
        start_chunk_id: int,
    ) -> List[ContextChunk]:
        """
        Chunk a document into smaller pieces.
        
        Args:
            text: Document text
            pasal_nomor: Article number
            peraturan_nomor: Regulation number
            relevance_score: Relevance score from retrieval
            start_chunk_id: Starting chunk ID
            
        Returns:
            List of ContextChunks
        """
        chunks = []
        
        # If text fits in one chunk, return as-is
        if len(text) <= self.chunk_size:
            chunk = ContextChunk(
                content=text.strip(),
                chunk_id=start_chunk_id,
                source_pasal=pasal_nomor,
                source_peraturan=peraturan_nomor,
                start_position=0,
                end_position=len(text),
                relevance_score=relevance_score,
            )
            return [chunk]
        
        # Split into chunks with overlap
        chunks_list = []
        start = 0
        chunk_num = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # Try to break at sentence boundary if possible
            if end < len(text):
                # Find last period, question mark, or newline
                for delim in ["\n", "。", ".", "?"]:
                    last_delim = text.rfind(delim, start, end)
                    if last_delim > start:
                        end = last_delim + 1
                        break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk = ContextChunk(
                    content=chunk_text,
                    chunk_id=start_chunk_id + chunk_num,
                    source_pasal=pasal_nomor,
                    source_peraturan=peraturan_nomor,
                    start_position=start,
                    end_position=end,
                    relevance_score=relevance_score,
                )
                chunks_list.append(chunk)
                chunk_num += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
            if start >= len(text):
                break
        
        return chunks_list
    
    def optimize_context_order(
        self, window: ContextWindow, strategy: str = "relevance"
    ) -> ContextWindow:
        """
        Optimize chunk order within context window.
        
        Args:
            window: Context window to optimize
            strategy: Ordering strategy ("relevance", "source", "sequential")
            
        Returns:
            Optimized context window
        """
        if strategy == "relevance":
            # Sort by relevance score (highest first)
            window.chunks = sorted(window.chunks, key=lambda x: x.relevance_score, reverse=True)
            
        elif strategy == "source":
            # Group by source pasal, then sort
            window.chunks = sorted(
                window.chunks,
                key=lambda x: (x.source_pasal, x.chunk_id)
            )
            
        elif strategy == "sequential":
            # Keep sequential order within each source
            window.chunks = sorted(window.chunks, key=lambda x: x.chunk_id)
        
        # Update order_in_window
        for i, chunk in enumerate(window.chunks, 1):
            chunk.order_in_window = i
        
        return window
    
    def truncate_window(
        self, window: ContextWindow, max_tokens: int = None
    ) -> ContextWindow:
        """
        Truncate context window to fit within token limit.
        
        Args:
            window: Context window to truncate
            max_tokens: Maximum tokens (default: use configured limit)
            
        Returns:
            Truncated context window
        """
        if max_tokens is None:
            max_tokens = self.max_context_tokens
        
        truncated_chunks = []
        total_tokens = 0
        
        for chunk in window.chunks:
            chunk_tokens = chunk.token_count()
            
            if total_tokens + chunk_tokens <= max_tokens:
                truncated_chunks.append(chunk)
                total_tokens += chunk_tokens
            else:
                break
        
        window.chunks = truncated_chunks
        window.used_tokens = total_tokens
        window.available_tokens = max_tokens - total_tokens
        
        logger.info(f"Truncated context window: {len(truncated_chunks)} chunks, {total_tokens} tokens")
        
        return window
    
    def add_system_context(
        self, window: ContextWindow, context_text: str
    ) -> ContextWindow:
        """
        Add system context (instructions, format examples) to window.
        
        Args:
            window: Context window
            context_text: System context to add
            
        Returns:
            Updated context window with system context
        """
        system_chunk = ContextChunk(
            content=context_text,
            chunk_id=-1,  # Special ID for system context
            source_pasal="SYSTEM",
            source_peraturan="SYSTEM",
            start_position=0,
            end_position=len(context_text),
            relevance_score=2.0,  # Highest priority
            order_in_window=0,
        )
        
        # Insert system context at the beginning
        window.chunks.insert(0, system_chunk)
        window.used_tokens += system_chunk.token_count()
        
        return window
    
    def format_context_for_llm(
        self, window: ContextWindow, include_metadata: bool = True
    ) -> str:
        """
        Format context window for LLM input.
        
        Args:
            window: Context window
            include_metadata: Include source metadata
            
        Returns:
            Formatted context string
        """
        lines = []
        
        lines.append("=== KONTEKS HUKUM ===\n")
        
        for i, chunk in enumerate(window.chunks, 1):
            if include_metadata and chunk.source_pasal != "SYSTEM":
                lines.append(f"\n[{i}] Sumber: Pasal {chunk.source_pasal} - {chunk.source_peraturan}")
                lines.append(f"Relevansi: {chunk.relevance_score:.1%}\n")
            
            lines.append(chunk.content)
            lines.append("\n" + "-" * 50)
        
        return "\n".join(lines)
    
    def _generate_window_id(self) -> str:
        """Generate unique window ID."""
        import uuid
        return f"cw_{uuid.uuid4().hex[:8]}"
    
    def get_stats(self) -> Dict:
        """Get context management statistics."""
        if not self.windows_history:
            return {}
        
        total_chunks = sum(len(w.chunks) for w in self.windows_history)
        avg_tokens = sum(w.used_tokens for w in self.windows_history) / len(self.windows_history)
        
        return {
            "total_windows": len(self.windows_history),
            "total_chunks": total_chunks,
            "avg_tokens_per_window": avg_tokens,
            "max_context_tokens": self.max_context_tokens,
            "last_window": self.windows_history[-1].to_dict() if self.windows_history else {},
        }
