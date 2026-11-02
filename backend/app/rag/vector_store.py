import logging
import hashlib
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.models.schemas import Chunk, DenseSearchResult
from app.rag.embeddings import embedding_service
from app.rag.embedding_registry import get_migrated_collections, register_migrated_collection

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    """
    Persistent vector store using ChromaDB with cosine distance metric.
    Stores chunk text, embeddings, and rich metadata for provenance tracking.
    """

    COLLECTION_NAME = settings.CHROMA_COLLECTION_NAME

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.persist_directory = persist_directory or str(settings.chroma_dir)
        requested_collection = collection_name or settings.CHROMA_COLLECTION_NAME
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=requested_collection,
            metadata={
                "hnsw:space": "cosine",
                "embedding_signature": embedding_service.index_signature
            }
        )
        self.embedding_signature = embedding_service.index_signature
        self.embedding_compatible = self._collection_matches_embedding()
        if not self.embedding_compatible and self.collection.count() == 0:
            signature_hash = hashlib.sha256(
                self.embedding_signature.encode("utf-8")
            ).hexdigest()[:10]
            empty_name = (
                f"{requested_collection}_empty_{signature_hash}"
            )[:63]
            self.collection = self.client.get_or_create_collection(
                name=empty_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_signature": self.embedding_signature,
                    "migration_source": requested_collection
                }
            )
            self.embedding_compatible = self._collection_matches_embedding()
            if self.embedding_compatible:
                register_migrated_collection(
                    empty_name,
                    requested_collection,
                    self.embedding_signature,
                    0
                )
        if not self.embedding_compatible:
            migrated = self._find_migrated_collection(requested_collection)
            if migrated is not None:
                self.collection = migrated
                self.embedding_compatible = True
            else:
                logger.error(
                    "Chroma collection '%s' has no compatible embedding signature. "
                    "Dense retrieval and document writes are disabled until the index is migrated.",
                    requested_collection
                )
        logger.info(f"Initialized ChromaDB vector store at: {self.persist_directory}")

    def _collection_matches_embedding(self) -> bool:
        metadata = self.collection.metadata or {}
        if metadata.get("embedding_signature") != self.embedding_signature:
            return False
        if self.collection.count() == 0:
            return True

        stored = self.collection.get(limit=1, include=["embeddings"])
        vectors = stored.get("embeddings")
        return (
            vectors is not None
            and len(vectors) > 0
            and len(vectors[0]) == embedding_service.dimension
        )

    def _find_migrated_collection(self, source_name: str):
        matching = []
        existing_names = {
            item if isinstance(item, str) else item.name
            for item in self.client.list_collections()
        }
        for name in get_migrated_collections(source_name, self.embedding_signature):
            if name not in existing_names:
                continue
            candidate = self.client.get_collection(name=name)
            if self._collection_has_expected_dimension(candidate):
                matching.append(candidate)

        if len(matching) > 1:
            logger.error(
                "Multiple compatible migrations exist for '%s'; set CHROMA_COLLECTION_NAME "
                "to the intended migrated collection.",
                source_name
            )
            return None
        return matching[0] if matching else None

    @staticmethod
    def _collection_has_expected_dimension(collection) -> bool:
        if collection.count() == 0:
            return True
        stored = collection.get(limit=1, include=["embeddings"])
        vectors = stored.get("embeddings")
        return (
            vectors is not None
            and len(vectors) > 0
            and len(vectors[0]) == embedding_service.dimension
        )

    def add_chunks(self, chunks: List[Chunk], embeddings: Optional[List[List[float]]] = None) -> int:
        """
        Embeds (if needed) and indexes chunks in ChromaDB.
        """
        if not chunks:
            return 0
        if not self.embedding_compatible:
            raise RuntimeError(
                f"Chroma collection '{self.collection.name}' uses an unknown or incompatible "
                "embedding space. Run scripts/migrate_embedding_index.py before indexing documents."
            )

        ids = [c.chunk_id for c in chunks]
        texts = [c.content for c in chunks]
        metadatas = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "document_title": c.document_title,
                "author": c.author or "Unknown",
                "page_number": c.page_number if c.page_number is not None else -1,
                "section": c.section or "",
                "chunk_index": c.chunk_index,
                "char_count": c.char_count
            }
            for c in chunks
        ]

        if embeddings is None:
            embeddings = embedding_service.embed_documents(texts)
        if len(embeddings) != len(chunks) or any(
            len(vector) != embedding_service.dimension for vector in embeddings
        ):
            raise ValueError("Document embedding count or dimension does not match the Chroma index.")

        # Chroma upsert allows safe re-indexing without duplicates
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB collection {self.collection.name}")
        return len(chunks)

    def query_dense(self, query_text: str, top_k: int = 8) -> List[DenseSearchResult]:
        """
        Queries ChromaDB using cosine distance and returns ranked DenseSearchResult items.
        """
        if not query_text.strip():
            return []
        if not self.embedding_compatible:
            logger.warning(
                "Skipping dense retrieval because collection '%s' is not compatible with embedding signature '%s'.",
                self.collection.name,
                self.embedding_signature
            )
            return []

        count = self.collection.count()
        if count == 0:
            return []

        query_emb = embedding_service.embed_query(query_text)
        n_results = min(top_k, count)

        res = self.collection.query(
            query_embeddings=[query_emb],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        results: List[DenseSearchResult] = []
        if not res or not res.get("ids") or not res["ids"][0]:
            return results

        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        distances = res["distances"][0]

        for rank, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, distances), start=1):
            # Chroma cosine distance = 1 - cosine_similarity
            cosine_score = max(0.0, float(1.0 - dist))
            page_num = meta.get("page_number")
            if page_num == -1:
                page_num = None

            chunk = Chunk(
                chunk_id=cid,
                document_id=meta.get("document_id", ""),
                document_title=meta.get("document_title", ""),
                author=meta.get("author"),
                page_number=page_num,
                section=meta.get("section") or None,
                content=doc,
                chunk_index=int(meta.get("chunk_index", 0)),
                char_count=int(meta.get("char_count", len(doc)))
            )
            results.append(DenseSearchResult(
                chunk=chunk,
                cosine_score=round(cosine_score, 4),
                rank=rank
            ))

        return results

    def delete_document(self, document_id: str) -> int:
        """Deletes all chunks associated with a document_id."""
        try:
            # Get matching IDs
            existing = self.collection.get(where={"document_id": document_id})
            ids_to_del = existing.get("ids", [])
            if ids_to_del:
                self.collection.delete(ids=ids_to_del)
                logger.info(f"Deleted {len(ids_to_del)} chunks for document {document_id}")
                return len(ids_to_del)
            return 0
        except Exception as e:
            logger.error(f"Error deleting document {document_id} from vector store: {e}")
            return 0

    def get_document_chunks(self, document_id: str) -> List[Chunk]:
        """Retrieves all chunks for a document."""
        res = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"]
        )
        chunks: List[Chunk] = []
        if not res or not res.get("ids"):
            return chunks

        for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
            page_num = meta.get("page_number")
            if page_num == -1:
                page_num = None
            chunks.append(Chunk(
                chunk_id=cid,
                document_id=meta.get("document_id", document_id),
                document_title=meta.get("document_title", ""),
                author=meta.get("author"),
                page_number=page_num,
                section=meta.get("section") or None,
                content=doc,
                chunk_index=int(meta.get("chunk_index", 0)),
                char_count=int(meta.get("char_count", len(doc)))
            ))
        chunks.sort(key=lambda c: c.chunk_index)
    def get_all_chunks(self) -> List[Chunk]:
        """Retrieves all chunks across all documents stored in ChromaDB."""
        try:
            count = self.collection.count()
            if count == 0:
                return []
            res = self.collection.get(include=["documents", "metadatas"])
            chunks: List[Chunk] = []
            if not res or not res.get("ids"):
                return chunks
            for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
                page_num = meta.get("page_number")
                if page_num == -1:
                    page_num = None
                chunks.append(Chunk(
                    chunk_id=cid,
                    document_id=meta.get("document_id", ""),
                    document_title=meta.get("document_title", ""),
                    author=meta.get("author"),
                    page_number=page_num,
                    section=meta.get("section") or None,
                    content=doc,
                    chunk_index=int(meta.get("chunk_index", 0)),
                    char_count=int(meta.get("char_count", len(doc)))
                ))
            return chunks
        except Exception as e:
            logger.error(f"Error fetching all chunks from vector store: {e}")
            return []

    def get_total_chunks_count(self) -> int:
        return self.collection.count()

    def clear_all(self):
        """Clears all embeddings in collection."""
        collection_name = self.collection.name
        self.client.delete_collection(collection_name)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_signature": self.embedding_signature
            }
        )
        self.embedding_compatible = True

# Global singleton
vector_store = ChromaVectorStore()
