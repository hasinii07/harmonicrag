import os
import json
import uuid
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import pymupdf

from app.config import settings
from app.models.schemas import DocumentMetadata, Chunk
from app.rag.chunking import chunk_document_pages, chunk_text
from app.rag.vector_store import vector_store
from app.rag.lexical_search import lexical_index

logger = logging.getLogger(__name__)

class DocumentIngestionManager:
    """
    Manages document extraction (PDF, MD, TXT, Notes), chunking,
    dual indexing (ChromaDB + BM25), and metadata persistence.
    """

    def __init__(self, metadata_file: Optional[Path] = None):
        self.metadata_file = metadata_file or (settings.metadata_dir / "documents.json")
        self.documents: Dict[str, DocumentMetadata] = {}
        self.load_metadata()

    def load_metadata(self):
        """Loads document metadata registry from JSON."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.documents = {
                    item["id"]: DocumentMetadata(**item)
                    for item in data.get("documents", [])
                }
                logger.info(f"Loaded {len(self.documents)} documents from {self.metadata_file}")
            except Exception as e:
                logger.error(f"Failed to load document metadata: {e}")

    def save_metadata(self):
        """Persists document metadata registry to JSON."""
        try:
            data = {
                "documents": [doc.model_dump() for doc in self.documents.values()],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save document metadata: {e}")

    def _compute_checksum(self, content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    def extract_pdf(self, file_path: Path) -> Tuple[List[Dict[str, Any]], int]:
        """
        Extracts text from PDF page by page using PyMuPDF, preserving 1-indexed page associations.
        """
        pages: List[Dict[str, Any]] = []
        try:
            doc = pymupdf.open(str(file_path))
            page_count = len(doc)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if text:
                    pages.append({
                        "page_number": page_num,
                        "text": text,
                        "section": f"Page {page_num}"
                    })
            doc.close()
            return pages, page_count
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            raise ValueError("Failed to extract text from PDF.") from e

    def extract_text_file(self, file_path: Path) -> Tuple[List[Dict[str, Any]], int]:
        """
        Reads plain text or markdown file.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            pages = [{"page_number": 1, "text": content, "section": "Document Body"}]
            return pages, 1
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise ValueError("Failed to read document text.") from e

    def ingest_file(
        self,
        file_path: Path,
        title: Optional[str] = None,
        author: Optional[str] = "Unknown"
    ) -> DocumentMetadata:
        """
        Ingests a PDF, MD, or TXT file into both vector and lexical indexes.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_bytes = file_path.read_bytes()
        file_size = len(file_bytes)
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(f"File exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_MB}MB")

        checksum = self._compute_checksum(file_bytes)
        # Duplicate detection by checksum
        for existing in self.documents.values():
            if existing.checksum == checksum and existing.status == "indexed":
                logger.info(f"Duplicate document detected (id={existing.id}). Returning existing metadata.")
                return existing

        ext = file_path.suffix.lower()
        doc_id = str(uuid.uuid4())[:8]
        doc_title = title or file_path.stem.replace('_', ' ').replace('-', ' ').title()

        if ext == ".pdf":
            file_type = "pdf"
            pages, page_count = self.extract_pdf(file_path)
        elif ext in [".md", ".markdown"]:
            file_type = "md"
            pages, page_count = self.extract_text_file(file_path)
        elif ext in [".txt"]:
            file_type = "txt"
            pages, page_count = self.extract_text_file(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Supported: .pdf, .md, .txt")

        if not pages or all(not p.get("text") for p in pages):
            raise ValueError("Document contains no extractable text.")

        # Chunk pages
        chunks = chunk_document_pages(
            pages=pages,
            document_id=doc_id,
            document_title=doc_title,
            author=author,
            chunk_size=settings.CHUNK_SIZE_CHARS,
            chunk_overlap=settings.CHUNK_OVERLAP_CHARS
        )

        if not chunks:
            raise ValueError("Failed to create text chunks from document.")

        # Index in ChromaDB
        vector_store.add_chunks(chunks)

        # Index in BM25
        lexical_index.add_chunks(chunks)

        meta = DocumentMetadata(
            id=doc_id,
            filename=file_path.name,
            title=doc_title,
            author=author or "Unknown",
            file_type=file_type,
            file_size_bytes=file_size,
            page_count=page_count,
            chunk_count=len(chunks),
            status="indexed",
            created_at=datetime.now().isoformat(),
            checksum=checksum
        )

        self.documents[doc_id] = meta
        self.save_metadata()
        logger.info(f"Successfully ingested document '{doc_title}' ({doc_id}) with {len(chunks)} chunks.")
        return meta

    def ingest_text(
        self,
        title: str,
        content: str,
        author: Optional[str] = "Unknown"
    ) -> DocumentMetadata:
        """
        Ingests raw text or pasted notes.
        """
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Content cannot be empty.")

        content_bytes = clean_content.encode("utf-8")
        checksum = self._compute_checksum(content_bytes)

        # Duplicate check
        for existing in self.documents.values():
            if existing.checksum == checksum and existing.status == "indexed":
                return existing

        doc_id = str(uuid.uuid4())[:8]
        chunks = chunk_text(
            text=clean_content,
            document_id=doc_id,
            document_title=title,
            author=author,
            chunk_size=settings.CHUNK_SIZE_CHARS,
            chunk_overlap=settings.CHUNK_OVERLAP_CHARS
        )

        # Index in ChromaDB and BM25
        vector_store.add_chunks(chunks)
        lexical_index.add_chunks(chunks)

        meta = DocumentMetadata(
            id=doc_id,
            filename=f"{title.lower().replace(' ', '_')}.txt",
            title=title,
            author=author or "Unknown",
            file_type="notes",
            file_size_bytes=len(content_bytes),
            page_count=1,
            chunk_count=len(chunks),
            status="indexed",
            created_at=datetime.now().isoformat(),
            checksum=checksum
        )

        self.documents[doc_id] = meta
        self.save_metadata()
        logger.info(f"Successfully ingested notes '{title}' ({doc_id}) with {len(chunks)} chunks.")
        return meta

    def delete_document(self, document_id: str) -> bool:
        """
        Removes a document and all associated chunks from vector store, lexical index, and metadata.
        """
        if document_id not in self.documents:
            return False

        # Remove from vector store
        vector_store.delete_document(document_id)

        # Remove from lexical index
        lexical_index.delete_document(document_id)

        # Remove from registry
        del self.documents[document_id]
        self.save_metadata()
        logger.info(f"Deleted document {document_id}")
        return True

    def reindex_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """
        Re-indexes existing document chunks.
        """
        if document_id not in self.documents:
            return None

        # Fetch chunks from vector store
        chunks = vector_store.get_document_chunks(document_id)
        if not chunks:
            logger.warning(f"No chunks found for document {document_id} to re-index")
            return None

        # Re-index in BM25
        lexical_index.add_chunks(chunks)
        # Re-index in Chroma
        vector_store.add_chunks(chunks)

        meta = self.documents[document_id]
        meta.chunk_count = len(chunks)
        meta.status = "indexed"
        self.save_metadata()
        return meta

    def list_documents(self) -> List[DocumentMetadata]:
        return list(self.documents.values())

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        return self.documents.get(document_id)

# Global singleton
ingestion_manager = DocumentIngestionManager()
