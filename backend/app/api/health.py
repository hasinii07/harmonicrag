from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Literal
from app.config import settings
from app.rag.embeddings import embedding_service
from app.rag.vector_store import vector_store
from app.rag.lexical_search import lexical_index
from app.rag.ingestion import ingestion_manager
from app.rag.generation import answer_generator

router = APIRouter(prefix="/api/health", tags=["Health"])

class GeminiDiagnosticRequest(BaseModel):
    confirm: Literal[True]


@router.get("", response_model=Dict[str, Any])
def get_health() -> Dict[str, Any]:
    """
    Checks system health, model availability, vector database, and lexical index.
    """
    model_info = embedding_service.get_model_info()
    model_info.pop("fallback_reason", None)
    api_key_present = bool(settings.api_key and settings.api_key.strip())
    vector_count = vector_store.get_total_chunks_count()
    lexical_count = len(lexical_index.corpus_chunk_ids)

    return {
        "status": (
            "healthy"
            if vector_count > 0
            and vector_count == lexical_count
            and vector_store.embedding_compatible
            and embedding_service.is_available
            else "degraded"
        ),
        "app_name": "HarmonicRAG",
        "version": "1.0.0",
        "gemini_api_key_configured": api_key_present,
        "generative_model": settings.GEMINI_MODEL,
        "gemini_generation": {
            "configured": api_key_present,
            "connection_tested": bool(
                answer_generator.last_connection_test
                and answer_generator.last_connection_test.get("tested")
            ),
            "last_connection_test": answer_generator.last_connection_test,
        },
        "embedding_service": model_info,
        "vector_store": {
            "type": "ChromaDB",
            "indexed_chunks_count": vector_count,
            "embedding_compatible": vector_store.embedding_compatible,
            "embedding_signature": vector_store.embedding_signature
        },
        "lexical_index": {
            "type": "BM25Okapi",
            "indexed_chunks_count": lexical_count
        },
        "documents": {
            "total_documents": len(ingestion_manager.documents)
        }
    }


@router.post("/gemini/diagnostic", response_model=Dict[str, Any])
def diagnose_gemini_connection(request: GeminiDiagnosticRequest) -> Dict[str, Any]:
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    return answer_generator.diagnose_connection()
