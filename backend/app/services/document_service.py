import logging
import re
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
from app.config import settings
from app.models.schemas import DocumentMetadata, Chunk
from app.rag.ingestion import ingestion_manager
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)

class DocumentService:
    """
    Business service layer managing document uploads, storage, and index operations.
    """

    def __init__(self):
        self.storage_dir = settings.documents_dir

    def handle_upload(
        self,
        file: UploadFile,
        title: Optional[str] = None,
        author: Optional[str] = "Unknown"
    ) -> DocumentMetadata:
        """
        Saves uploaded file to disk and initiates ingestion.
        """
        filename = Path((file.filename or "").replace("\\", "/")).name
        if not filename or filename in {".", ".."}:
            raise ValueError("A valid filename is required.")

        extension = Path(filename).suffix.lower()
        if extension not in {".pdf", ".md", ".markdown", ".txt"}:
            raise ValueError("Unsupported file format. Supported: .pdf, .md, .markdown, .txt")

        target_path = self.storage_dir / filename
        if target_path.exists():
            target_path = target_path.with_name(
                f"{target_path.stem}_{uuid.uuid4().hex[:8]}{target_path.suffix}"
            )

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        bytes_written = 0
        try:
            with target_path.open("xb") as destination:
                while chunk := file.file.read(64 * 1024):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise ValueError(
                            f"File exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_MB}MB"
                        )
                    destination.write(chunk)
        except ValueError:
            target_path.unlink(missing_ok=True)
            raise
        except Exception as e:
            target_path.unlink(missing_ok=True)
            logger.exception("Failed to save uploaded file")
            raise IOError("Could not save the uploaded file.") from e

        # Ingest file
        try:
            return ingestion_manager.ingest_file(
                file_path=target_path,
                title=title or Path(filename).stem.replace('_', ' ').title(),
                author=author
            )
        except Exception:
            target_path.unlink(missing_ok=True)
            raise

    def handle_text_notes(
        self,
        title: str,
        content: str,
        author: Optional[str] = "Unknown"
    ) -> DocumentMetadata:
        """
        Ingests pasted markdown or text notes directly.
        """
        content_bytes = content.encode("utf-8")
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content_bytes) > max_bytes:
            raise ValueError(
                f"Text exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # Also persist text file to data/documents for user inspection
        stem = re.sub(r"[^a-z0-9_-]+", "_", title.lower()).strip("_")[:30] or "notes"
        filename = f"{stem}_{uuid.uuid4().hex[:8]}.txt"
        file_path = self.storage_dir / filename
        file_path.write_text(content, encoding="utf-8")

        return ingestion_manager.ingest_text(
            title=title,
            content=content,
            author=author
        )

    def list_documents(self) -> List[DocumentMetadata]:
        return ingestion_manager.list_documents()

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        return ingestion_manager.get_document(document_id)

    def delete_document(self, document_id: str) -> bool:
        return ingestion_manager.delete_document(document_id)

    def reindex_document(self, document_id: str) -> Optional[DocumentMetadata]:
        return ingestion_manager.reindex_document(document_id)

    def get_document_chunks(self, document_id: str) -> List[Chunk]:
        return vector_store.get_document_chunks(document_id)

# Global singleton
document_service = DocumentService()
