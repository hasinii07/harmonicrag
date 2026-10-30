import shutil
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.rag.lexical_search import lexical_index
from app.rag.vector_store import vector_store


def main() -> None:
    vector_count = vector_store.get_total_chunks_count()
    if vector_count:
        lexical_count = len(lexical_index.corpus_chunk_ids)
        if vector_count != lexical_count:
            raise RuntimeError(
                f"Persistent index mismatch: ChromaDB has {vector_count} chunks, "
                f"BM25 has {lexical_count}."
            )
        print(f"Using existing knowledge base ({vector_count} indexed chunks).")
        return

    bundled_documents = settings.project_root / "data" / "documents"
    storage_directory = settings.documents_dir
    storage_directory.mkdir(parents=True, exist_ok=True)

    if bundled_documents.resolve() != storage_directory.resolve():
        for source in bundled_documents.iterdir():
            if source.is_file() and source.suffix.lower() in {".pdf", ".md", ".markdown", ".txt"}:
                target = storage_directory / source.name
                if not target.exists():
                    shutil.copy2(source, target)

    supported_documents = [
        path for path in storage_directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".pdf", ".md", ".markdown", ".txt"}
    ]
    if not supported_documents:
        raise RuntimeError("No supported source documents are available to initialize the knowledge base.")

    from ingest_documents import main as ingest_documents

    ingest_documents()

    vector_count = vector_store.get_total_chunks_count()
    lexical_count = len(lexical_index.corpus_chunk_ids)
    if vector_count == 0 or vector_count != lexical_count:
        raise RuntimeError(
            f"Knowledge-base initialization failed: ChromaDB has {vector_count} chunks, "
            f"BM25 has {lexical_count}."
        )
    print(f"Initialized knowledge base with {vector_count} indexed chunks.")


if __name__ == "__main__":
    main()
