import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.models.schemas import Chunk, DenseSearchResult
from app.rag.embeddings import embedding_service

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    """
    Persistent vector store using ChromaDB with cosine distance metric.
    Stores chunk text, embeddings, and rich metadata for provenance tracking.
    """

    COLLECTION_NAME = "harmonic_rag_chunks"

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or str(settings.chroma_dir)
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Initialized ChromaDB vector store at: {self.persist_directory}")

    def add_chunks(self, chunks: List[Chunk], embeddings: Optional[List[List[float]]] = None) -> int:
        """
        Embeds (if needed) and indexes chunks in ChromaDB.
        """
        if not chunks:
            return 0

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

        # Chroma upsert allows safe re-indexing without duplicates
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB collection {self.COLLECTION_NAME}")
        return len(chunks)

    def query_dense(self, query_text: str, top_k: int = 8) -> List[DenseSearchResult]:
        """
        Queries ChromaDB using cosine distance and returns ranked DenseSearchResult items.
        """
        if not query_text.strip():
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
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

# Global singleton
vector_store = ChromaVectorStore()
