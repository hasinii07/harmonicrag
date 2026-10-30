import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from app.models.schemas import DocumentMetadata, DocumentListResponse, TextIngestRequest, Chunk
from app.services.document_service import document_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])
logger = logging.getLogger(__name__)

@router.get("", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    """Lists all indexed instructional documents with page and chunk counts."""
    docs = document_service.list_documents()
    total_chunks = sum(d.chunk_count for d in docs)
    return DocumentListResponse(
        documents=docs,
        total_count=len(docs),
        total_chunks=total_chunks
    )

@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form("Unknown")
) -> DocumentMetadata:
    """
    Uploads a document (PDF, Markdown, or TXT), extracts text with page mapping,
    chunks content, and indexes it into ChromaDB and BM25.
    """
    try:
        return document_service.handle_upload(file=file, title=title, author=author)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Document ingestion failed")
        raise HTTPException(status_code=500, detail="Document ingestion failed.")

@router.post("/text", response_model=DocumentMetadata)
def ingest_text_notes(payload: TextIngestRequest) -> DocumentMetadata:
    """
    Ingests raw text or pasted markdown notes.
    """
    try:
        return document_service.handle_text_notes(
            title=payload.title,
            content=payload.content,
            author=payload.author
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Text ingestion failed")
        raise HTTPException(status_code=500, detail="Text ingestion failed.")

@router.get("/{document_id}", response_model=DocumentMetadata)
def get_document_details(document_id: str) -> DocumentMetadata:
    """Retrieves metadata for a specific document."""
    doc = document_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc

@router.get("/{document_id}/chunks", response_model=List[Chunk])
def get_document_chunks(document_id: str) -> List[Chunk]:
    """Retrieves all indexed text chunks and page associations for a document."""
    return document_service.get_document_chunks(document_id)

@router.delete("/{document_id}")
def delete_document(document_id: str):
    """
    Deletes a document and purges its chunks from ChromaDB and BM25.
    """
    success = document_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "success", "message": f"Document {document_id} and all its chunks were deleted."}

@router.post("/{document_id}/reindex", response_model=DocumentMetadata)
def reindex_document(document_id: str) -> DocumentMetadata:
    """
    Re-indexes an existing document across vector and lexical stores.
    """
    meta = document_service.reindex_document(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found or has no chunks.")
    return meta
