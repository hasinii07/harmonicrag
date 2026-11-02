import sys
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.rag.embeddings import embedding_service
from app.rag.embedding_registry import register_migrated_collection

BATCH_SIZE = 64


def migrate() -> str:
    if not embedding_service.is_live:
        raise RuntimeError(
            "A live Gemini embedding connection is required for migration. "
            "Check GOOGLE_API_KEY, GEMINI_EMBEDDING_MODEL, and network access."
        )

    source_name = settings.CHROMA_COLLECTION_NAME
    client = chromadb.PersistentClient(
        path=str(settings.chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    source = client.get_collection(name=source_name)
    source_count = source.count()
    if source_count == 0:
        raise RuntimeError(f"Source collection '{source_name}' is empty.")

    signature_slug = (
        f"{embedding_service.model_name.replace('-', '_')}_{embedding_service.dimension}"
    )
    target_name = f"{source_name}_migrated_{signature_slug}_{uuid.uuid4().hex[:8]}"[:63]
    target = client.create_collection(
        name=target_name,
        metadata={
            "hnsw:space": "cosine",
            "migration_source": source_name,
            "embedding_signature": embedding_service.index_signature
        }
    )

    for offset in range(0, source_count, BATCH_SIZE):
        batch = source.get(
            limit=min(BATCH_SIZE, source_count - offset),
            offset=offset,
            include=["documents", "metadatas"]
        )
        ids = batch.get("ids") or []
        documents = batch.get("documents") or []
        metadatas = batch.get("metadatas") or []
        if not ids or len(ids) != len(documents) or len(ids) != len(metadatas):
            raise RuntimeError(f"Source collection returned an incomplete batch at offset {offset}.")

        vectors = embedding_service.embed_documents(documents)
        if len(vectors) != len(ids) or any(
            len(vector) != embedding_service.dimension for vector in vectors
        ):
            raise RuntimeError(f"Embedding dimension or count validation failed at offset {offset}.")
        target.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=vectors)

    if target.count() != source_count:
        raise RuntimeError(
            f"Migration verification failed: source has {source_count} chunks, "
            f"target has {target.count()}."
        )

    stored = target.get(limit=1, include=["embeddings"])
    vectors = stored.get("embeddings")
    if vectors is None or not len(vectors) or len(vectors[0]) != embedding_service.dimension:
        raise RuntimeError("Migrated collection has an unexpected embedding dimension.")

    register_migrated_collection(
        target_name,
        source_name,
        embedding_service.index_signature,
        source_count
    )
    print(
        f"Migrated {source_count} chunks into '{target_name}' "
        f"using {embedding_service.index_signature}. "
        f"The source collection '{source_name}' was preserved."
    )
    return target_name


if __name__ == "__main__":
    migrate()
