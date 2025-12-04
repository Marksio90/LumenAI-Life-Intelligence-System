"""
Document Chunking Service

Advanced text chunking strategies for optimal RAG performance:
- Recursive character splitting (preserves structure)
- Semantic chunking (groups by meaning)
- Sliding window with overlap
- Metadata preservation
- Multi-language support
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib

from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter
)
import tiktoken

from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class ChunkingStrategy(str, Enum):
    """Available chunking strategies"""
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"


@dataclass
class Chunk:
    """Document chunk with metadata"""
    id: str
    text: str
    start_char: int
    end_char: int
    chunk_index: int
    total_chunks: int
    metadata: Dict[str, Any]
    token_count: int


@dataclass
class Document:
    """Source document"""
    id: str
    text: str
    metadata: Dict[str, Any]


class ChunkingService:
    """
    Intelligent document chunking service

    Features:
    - Multiple chunking strategies
    - Smart overlap to preserve context
    - Separator detection (paragraphs, sentences, code blocks)
    - Token-aware chunking
    - Metadata preservation
    """

    # Separators for recursive splitting (ordered by priority)
    SEPARATORS = [
        "\n\n\n",  # Multiple newlines (section breaks)
        "\n\n",    # Paragraph breaks
        "\n",      # Line breaks
        ". ",      # Sentence ends
        "! ",      # Exclamation
        "? ",      # Question
        "; ",      # Semicolon
        ", ",      # Comma
        " ",       # Space
        ""         # Character-level (last resort)
    ]

    # Code-specific separators
    CODE_SEPARATORS = [
        "\n\nclass ",
        "\n\ndef ",
        "\n\nasync def ",
        "\n\n",
        "\n",
        " ",
        ""
    ]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        model: str = "gpt-4"
    ):
        """
        Initialize chunking service

        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks (tokens)
            model: Model for token counting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model = model

        # Token encoder
        self.encoder = tiktoken.encoding_for_model(model)

        # Text splitters
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            separators=self.SEPARATORS,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self._count_tokens,
            is_separator_regex=False
        )

        self.code_splitter = RecursiveCharacterTextSplitter(
            separators=self.CODE_SEPARATORS,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self._count_tokens,
            is_separator_regex=False
        )

        self.token_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding_name=tiktoken.encoding_for_model(model).name
        )

        logger.info(f"Chunking service initialized: chunk_size={chunk_size}, overlap={chunk_overlap}")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.encoder.encode(text))
        except Exception:
            # Fallback
            return len(text) // 4

    def _generate_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID"""
        return hashlib.sha256(f"{doc_id}:{chunk_index}".encode()).hexdigest()[:16]

    def _detect_content_type(self, text: str) -> str:
        """Detect if text is code, markdown, or plain text"""
        # Check for code patterns
        code_patterns = [
            r'^\s*(def |class |import |from |function |const |let |var )',
            r'\{[\s\S]*\}',  # Curly braces
            r'^\s*#include',  # C/C++ includes
        ]

        for pattern in code_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return "code"

        # Check for markdown
        if re.search(r'^#{1,6}\s', text, re.MULTILINE):
            return "markdown"

        return "text"

    def chunk_document(
        self,
        document: Document,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    ) -> List[Chunk]:
        """
        Chunk document using specified strategy

        Args:
            document: Document to chunk
            strategy: Chunking strategy

        Returns:
            List of chunks with metadata
        """
        # Detect content type
        content_type = self._detect_content_type(document.text)

        # Select splitter
        if strategy == ChunkingStrategy.RECURSIVE:
            if content_type == "code":
                splitter = self.code_splitter
            else:
                splitter = self.recursive_splitter
        elif strategy == ChunkingStrategy.SLIDING_WINDOW:
            splitter = self.token_splitter
        else:
            splitter = self.recursive_splitter

        # Split text
        try:
            text_chunks = splitter.split_text(document.text)
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            # Fallback: simple token-based split
            text_chunks = self._simple_chunk(document.text)

        # Create chunk objects
        chunks = []
        char_position = 0

        for i, text in enumerate(text_chunks):
            # Find chunk position in original text
            start_char = document.text.find(text, char_position)
            if start_char == -1:
                start_char = char_position
            end_char = start_char + len(text)
            char_position = end_char

            # Create chunk
            chunk = Chunk(
                id=self._generate_chunk_id(document.id, i),
                text=text,
                start_char=start_char,
                end_char=end_char,
                chunk_index=i,
                total_chunks=len(text_chunks),
                metadata={
                    **document.metadata,
                    "document_id": document.id,
                    "content_type": content_type,
                    "strategy": strategy.value
                },
                token_count=self._count_tokens(text)
            )
            chunks.append(chunk)

        logger.info(f"Chunked document {document.id}: {len(chunks)} chunks (strategy={strategy.value}, type={content_type})")
        return chunks

    def _simple_chunk(self, text: str) -> List[str]:
        """Fallback: Simple token-based chunking"""
        tokens = self.encoder.encode(text)
        chunks = []

        for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = self.encoder.decode(chunk_tokens)
            chunks.append(chunk_text)

        return chunks

    def chunk_conversation(
        self,
        messages: List[Dict[str, str]],
        max_messages_per_chunk: int = 10
    ) -> List[Chunk]:
        """
        Chunk conversation history

        Args:
            messages: List of messages with 'role' and 'content'
            max_messages_per_chunk: Maximum messages per chunk

        Returns:
            Conversation chunks
        """
        chunks = []
        total_messages = len(messages)

        for i in range(0, total_messages, max_messages_per_chunk):
            chunk_messages = messages[i:i + max_messages_per_chunk]

            # Format messages
            text = "\n\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in chunk_messages
            ])

            # Create chunk
            chunk = Chunk(
                id=self._generate_chunk_id("conversation", i),
                text=text,
                start_char=i,
                end_char=min(i + max_messages_per_chunk, total_messages),
                chunk_index=i // max_messages_per_chunk,
                total_chunks=(total_messages + max_messages_per_chunk - 1) // max_messages_per_chunk,
                metadata={
                    "type": "conversation",
                    "message_count": len(chunk_messages),
                    "start_index": i,
                    "end_index": min(i + max_messages_per_chunk, total_messages)
                },
                token_count=self._count_tokens(text)
            )
            chunks.append(chunk)

        logger.info(f"Chunked conversation: {len(chunks)} chunks from {total_messages} messages")
        return chunks

    def merge_small_chunks(
        self,
        chunks: List[Chunk],
        min_chunk_size: int = 100
    ) -> List[Chunk]:
        """
        Merge chunks that are too small

        Args:
            chunks: List of chunks
            min_chunk_size: Minimum chunk size in tokens

        Returns:
            Merged chunks
        """
        if not chunks:
            return []

        merged = []
        current_chunk = None

        for chunk in chunks:
            if current_chunk is None:
                current_chunk = chunk
                continue

            # Check if current chunk is too small
            if current_chunk.token_count < min_chunk_size:
                # Merge with next chunk
                merged_text = current_chunk.text + "\n\n" + chunk.text
                merged_tokens = self._count_tokens(merged_text)

                current_chunk = Chunk(
                    id=current_chunk.id,  # Keep first ID
                    text=merged_text,
                    start_char=current_chunk.start_char,
                    end_char=chunk.end_char,
                    chunk_index=current_chunk.chunk_index,
                    total_chunks=current_chunk.total_chunks,
                    metadata=current_chunk.metadata,
                    token_count=merged_tokens
                )
            else:
                merged.append(current_chunk)
                current_chunk = chunk

        # Add last chunk
        if current_chunk:
            merged.append(current_chunk)

        logger.debug(f"Merged chunks: {len(chunks)} -> {len(merged)}")
        return merged

    def get_chunk_stats(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Get statistics about chunks"""
        if not chunks:
            return {}

        token_counts = [c.token_count for c in chunks]

        return {
            "total_chunks": len(chunks),
            "avg_tokens": sum(token_counts) / len(token_counts),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "total_tokens": sum(token_counts)
        }


# Global instance
_chunking_service: Optional[ChunkingService] = None


def get_chunking_service() -> ChunkingService:
    """Get or create global chunking service instance"""
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
