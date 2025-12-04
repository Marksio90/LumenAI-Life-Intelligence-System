"""
File Processing Service for PDF, Images, and Document Upload

Handles file upload, processing, and RAG integration.
"""

import asyncio
import logging
import tempfile
import os
from typing import Optional, BinaryIO, List, Dict, Any
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import mimetypes

import aiofiles
from PIL import Image
import PyPDF2
import pytesseract

from backend.services.rag import get_rag_pipeline, Document

logger = logging.getLogger(__name__)


class FileProcessingService:
    """
    Service for processing uploaded files and integrating with RAG.

    Features:
    - PDF text extraction
    - Image OCR (Tesseract)
    - Document chunking
    - RAG integration
    - Multiple file format support
    - Virus scanning (placeholder)
    """

    # Maximum file sizes (bytes)
    MAX_FILE_SIZE = {
        "pdf": 50 * 1024 * 1024,      # 50 MB
        "image": 10 * 1024 * 1024,     # 10 MB
        "text": 5 * 1024 * 1024,       # 5 MB
        "default": 25 * 1024 * 1024    # 25 MB
    }

    # Supported file types
    SUPPORTED_TYPES = {
        "pdf": [".pdf"],
        "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
        "text": [".txt", ".md", ".csv", ".json", ".xml", ".html"]
    }

    def __init__(self):
        self.upload_dir = Path(tempfile.gettempdir()) / "lumenai_uploads"
        self.upload_dir.mkdir(exist_ok=True)
        self.rag_pipeline = None
        logger.info("FileProcessingService initialized")

    def _get_rag_pipeline(self):
        """Lazy initialization of RAG pipeline."""
        if not self.rag_pipeline:
            try:
                self.rag_pipeline = get_rag_pipeline()
            except Exception as e:
                logger.warning(f"RAG pipeline not available: {e}")
        return self.rag_pipeline

    def validate_file(
        self,
        filename: str,
        file_size: int,
        allowed_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate uploaded file.

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes
            allowed_types: Optional list of allowed types (pdf, image, text)

        Returns:
            Validation result with status and message
        """
        # Get file extension
        ext = Path(filename).suffix.lower()

        # Determine file type
        file_type = None
        for ftype, extensions in self.SUPPORTED_TYPES.items():
            if ext in extensions:
                file_type = ftype
                break

        if not file_type:
            return {
                "valid": False,
                "error": f"Unsupported file type: {ext}",
                "file_type": None
            }

        # Check if type is allowed
        if allowed_types and file_type not in allowed_types:
            return {
                "valid": False,
                "error": f"File type not allowed: {file_type}",
                "file_type": file_type
            }

        # Check file size
        max_size = self.MAX_FILE_SIZE.get(file_type, self.MAX_FILE_SIZE["default"])
        if file_size > max_size:
            return {
                "valid": False,
                "error": f"File too large: {file_size} bytes (max: {max_size} bytes)",
                "file_type": file_type
            }

        return {
            "valid": True,
            "file_type": file_type,
            "extension": ext
        }

    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload and save a file.

        Args:
            file: File object
            filename: Original filename
            user_id: User ID
            metadata: Optional metadata

        Returns:
            Upload result with file ID and path
        """
        # Generate unique file ID
        file_id = str(uuid4())
        ext = Path(filename).suffix.lower()
        safe_filename = f"{file_id}{ext}"
        file_path = self.upload_dir / user_id / safe_filename

        # Create user directory
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read() if hasattr(file, 'read') else file
            await f.write(content)

        file_size = file_path.stat().st_size

        result = {
            "file_id": file_id,
            "filename": filename,
            "safe_filename": safe_filename,
            "file_path": str(file_path),
            "file_size": file_size,
            "user_id": user_id,
            "metadata": metadata or {},
            "uploaded_at": datetime.utcnow().isoformat()
        }

        logger.info(
            f"File uploaded: file_id={file_id}, user={user_id}, "
            f"size={file_size} bytes"
        )

        return result

    async def process_pdf(
        self,
        file_path: str,
        extract_images: bool = False
    ) -> Dict[str, Any]:
        """
        Extract text from PDF file.

        Args:
            file_path: Path to PDF file
            extract_images: Whether to extract and OCR images

        Returns:
            Extracted content with text and metadata
        """
        try:
            text_content = []
            page_count = 0

            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                page_count = len(pdf_reader.pages)

                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        text_content.append({
                            "page": page_num + 1,
                            "text": text
                        })

                    # Extract images if requested
                    if extract_images:
                        # TODO: Implement image extraction from PDF
                        pass

            full_text = "\n\n".join([page["text"] for page in text_content])

            result = {
                "text": full_text,
                "pages": text_content,
                "page_count": page_count,
                "character_count": len(full_text),
                "word_count": len(full_text.split()),
                "processed_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"PDF processed: pages={page_count}, "
                f"characters={result['character_count']}"
            )

            return result

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise

    async def process_image(
        self,
        file_path: str,
        ocr: bool = True,
        language: str = "eng"
    ) -> Dict[str, Any]:
        """
        Process image file and optionally perform OCR.

        Args:
            file_path: Path to image file
            ocr: Whether to perform OCR
            language: OCR language (default: English)

        Returns:
            Processed image data with text and metadata
        """
        try:
            # Open image
            image = Image.open(file_path)

            result = {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
                "processed_at": datetime.utcnow().isoformat()
            }

            # Perform OCR if requested
            if ocr:
                try:
                    text = pytesseract.image_to_string(image, lang=language)
                    result["text"] = text
                    result["character_count"] = len(text)
                    result["word_count"] = len(text.split())

                    logger.info(
                        f"Image OCR completed: characters={result['character_count']}"
                    )
                except Exception as e:
                    logger.error(f"OCR failed: {e}")
                    result["text"] = ""
                    result["ocr_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise

    async def process_text_file(
        self,
        file_path: str,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """
        Process text file.

        Args:
            file_path: Path to text file
            encoding: Text encoding

        Returns:
            Processed text data
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                text = await f.read()

            result = {
                "text": text,
                "character_count": len(text),
                "word_count": len(text.split()),
                "line_count": len(text.split("\n")),
                "encoding": encoding,
                "processed_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Text file processed: characters={result['character_count']}"
            )

            return result

        except Exception as e:
            logger.error(f"Error processing text file: {e}")
            raise

    async def process_and_index(
        self,
        file_id: str,
        file_path: str,
        file_type: str,
        user_id: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process file and index to RAG system.

        Args:
            file_id: Unique file identifier
            file_path: Path to file
            file_type: Type of file (pdf, image, text)
            user_id: User ID
            filename: Original filename
            metadata: Optional metadata

        Returns:
            Processing and indexing result
        """
        # Process file based on type
        if file_type == "pdf":
            processed = await self.process_pdf(file_path)
        elif file_type == "image":
            processed = await self.process_image(file_path)
        elif file_type == "text":
            processed = await self.process_text_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        text_content = processed.get("text", "")

        if not text_content or not text_content.strip():
            return {
                "file_id": file_id,
                "indexed": False,
                "error": "No text content extracted"
            }

        # Index to RAG if available
        rag_pipeline = self._get_rag_pipeline()
        if rag_pipeline:
            # Create document
            doc = Document(
                id=file_id,
                text=text_content,
                metadata={
                    "user_id": user_id,
                    "filename": filename,
                    "file_type": file_type,
                    "processed_at": processed["processed_at"],
                    "character_count": processed.get("character_count", 0),
                    "word_count": processed.get("word_count", 0),
                    **(metadata or {})
                }
            )

            # Index document
            await rag_pipeline.index_document(doc, strategy="recursive")

            logger.info(
                f"File indexed to RAG: file_id={file_id}, "
                f"chunks={processed.get('word_count', 0) // 200}"
            )

            return {
                "file_id": file_id,
                "indexed": True,
                "text_length": len(text_content),
                "processed": processed
            }

        return {
            "file_id": file_id,
            "indexed": False,
            "error": "RAG pipeline not available",
            "processed": processed
        }

    async def search_files(
        self,
        user_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search indexed files using RAG.

        Args:
            user_id: User ID
            query: Search query
            top_k: Number of results to return

        Returns:
            List of search results
        """
        rag_pipeline = self._get_rag_pipeline()
        if not rag_pipeline:
            return []

        try:
            result = await rag_pipeline.retrieve(
                query=query,
                top_k=top_k,
                use_hybrid=True,
                use_rerank=True,
                filters={"user_id": user_id}
            )

            return [
                {
                    "file_id": doc.id,
                    "filename": doc.metadata.get("filename"),
                    "file_type": doc.metadata.get("file_type"),
                    "text": doc.text,
                    "score": doc.score,
                    "metadata": doc.metadata
                }
                for doc in result.documents
            ]

        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []

    def cleanup_old_files(self, older_than_days: int = 30):
        """
        Clean up old uploaded files.

        Args:
            older_than_days: Remove files older than this many days
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (older_than_days * 86400)

        removed_count = 0
        for file_path in self.upload_dir.rglob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {e}")

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old files")


# Global instance
_file_processing_service = None


def get_file_processing_service() -> FileProcessingService:
    """Get or create the global FileProcessingService instance."""
    global _file_processing_service
    if _file_processing_service is None:
        _file_processing_service = FileProcessingService()
    return _file_processing_service
