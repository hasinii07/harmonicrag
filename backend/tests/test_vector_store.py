import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.models.schemas import Chunk
from app.rag.embeddings import embedding_service
from app.rag.embedding_registry import register_migrated_collection
from app.rag.vector_store import ChromaVectorStore


def _make_chunk() -> Chunk:
    content = "A perfect authentic cadence resolves V to I."
    return Chunk(
        chunk_id="test_chunk",
        document_id="test_document",
        document_title="Test",
        content=content,
        chunk_index=0,
        char_count=len(content)
    )


def test_legacy_collection_is_not_used_for_dense_retrieval_or_writes(tmp_path):
    client = chromadb.PersistentClient(
        path=str(tmp_path),
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    legacy = client.create_collection(
        name="legacy_collection",
        metadata={"hnsw:space": "cosine"}
    )
    legacy.add(
        ids=["legacy_chunk"],
        documents=["Legacy vector"],
        metadatas=[{"document_id": "legacy_document"}],
        embeddings=[[1.0] + [0.0] * (embedding_service.dimension - 1)]
    )

    store = ChromaVectorStore(
        persist_directory=str(tmp_path),
        collection_name="legacy_collection"
    )

    assert store.embedding_compatible is False
    assert store.query_dense("legacy vector") == []
    with pytest.raises(RuntimeError, match="migrate_embedding_index.py"):
        store.add_chunks([_make_chunk()])


def test_vector_store_selects_a_verified_migration_without_changing_legacy_collection(
    tmp_path,
    monkeypatch
):
    monkeypatch.setattr(
        settings,
        "METADATA_STORAGE_DIRECTORY",
        str(tmp_path / "metadata")
    )
    client = chromadb.PersistentClient(
        path=str(tmp_path),
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    legacy = client.create_collection(
        name="legacy_collection",
        metadata={"hnsw:space": "cosine"}
    )
    legacy.add(
        ids=["legacy_chunk"],
        documents=["Legacy vector"],
        metadatas=[{"document_id": "legacy_document"}],
        embeddings=[[1.0] + [0.0] * (embedding_service.dimension - 1)]
    )
    migrated = client.create_collection(
        name="migrated_collection",
        metadata={
            "hnsw:space": "cosine",
            "migration_source": "legacy_collection",
            "embedding_signature": embedding_service.index_signature
        }
    )
    migrated.add(
        ids=["legacy_chunk"],
        documents=["Re-embedded vector"],
        metadatas=[{"document_id": "legacy_document"}],
        embeddings=[[1.0] + [0.0] * (embedding_service.dimension - 1)]
    )
    register_migrated_collection(
        "migrated_collection",
        "legacy_collection",
        embedding_service.index_signature,
        1
    )

    store = ChromaVectorStore(
        persist_directory=str(tmp_path),
        collection_name="legacy_collection"
    )

    assert store.collection.name == "migrated_collection"
    assert store.embedding_compatible is True
    assert legacy.count() == 1
