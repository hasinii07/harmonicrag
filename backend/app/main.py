import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.evaluation import router as evaluation_router
from app.rag.vector_store import vector_store
from app.rag.lexical_search import lexical_index
from app.rag.embeddings import embedding_service
from app.rag.ingestion import ingestion_manager

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("HarmonicRAG")

def log_startup_diagnostics():
    chroma_count = vector_store.get_total_chunks_count()
    lexical_count = len(lexical_index.corpus_chunk_ids)
    coll_name = vector_store.collection.name if hasattr(vector_store, "collection") and vector_store.collection else "unavailable"
    doc_count = len(ingestion_manager.documents)
    doc_files_on_disk = len(list(settings.documents_dir.glob("*.*"))) if settings.documents_dir.exists() else 0
    embed_info = embedding_service.get_model_info()
    api_key_configured = bool(settings.api_key and settings.api_key.strip())
    gemini_key_status = f"CONFIGURED ({len(settings.api_key.strip())} chars, hidden)" if api_key_configured else "NOT CONFIGURED (offline fallback)"

    banner = [
        "=" * 72,
        "               HARMONICRAG SYSTEM STARTUP DIAGNOSTICS",
        "=" * 72,
        f"  Project Root:           {settings.PROJECT_ROOT}",
        f"  ChromaDB Directory:     {settings.chroma_dir} (exists: {settings.chroma_dir.exists()})",
        f"  Document Directory:     {settings.documents_dir} (exists: {settings.documents_dir.exists()})",
        f"  Metadata Directory:     {settings.metadata_dir} (exists: {settings.metadata_dir.exists()})",
        f"  Frontend Directory:     {settings.frontend_dir} (exists: {settings.frontend_dir.exists()})",
        "-" * 72,
        f"  ChromaDB Collection:    {coll_name}",
        f"  Vector Chunks Indexed:  {chroma_count} chunks",
        f"  BM25 Lexical Chunks:    {lexical_count} chunks",
        f"  Index Parity:           {'OK (Consistent)' if chroma_count == lexical_count and chroma_count > 0 else 'WARNING: Mismatch or empty'}",
        "-" * 72,
        f"  Registered Documents:   {doc_count} documents in registry",
        f"  Document Files on Disk: {doc_files_on_disk} files",
        f"  Embedding Model:        {embed_info.get('model_name')} (dim: {embed_info.get('dimension')})",
        f"  Embedding Provider:     {embed_info.get('provider')}",
        f"  Embedding Mode:         {embed_info.get('mode')}",
        f"  Generative Model:       {settings.GEMINI_MODEL}",
        f"  Gemini API Credentials: {gemini_key_status}",
        "=" * 72
    ]
    for line in banner:
        logger.info(line)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log_startup_diagnostics()
    yield
    logger.info("HarmonicRAG server shutting down...")

app = FastAPI(
    title="HarmonicRAG — Music Theory AI Chatbot",
    description="Evidence-grounded music theory research assistant using hybrid RAG and Google Gemini.",
    version="1.0.0",
    lifespan=lifespan
)

# Register API routers FIRST so they are not caught by static file catch-alls
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(evaluation_router)

# Serve Frontend static assets
frontend_path = settings.frontend_dir
if frontend_path.exists():
    app.mount("/css", StaticFiles(directory=str(frontend_path / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")

    @app.get("/", include_in_schema=False)
    def serve_frontend_root():
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "HarmonicRAG API is online. Frontend index.html not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
