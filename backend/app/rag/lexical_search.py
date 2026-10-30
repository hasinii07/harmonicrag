import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from app.config import settings
from app.models.schemas import Chunk, LexicalSearchResult

logger = logging.getLogger(__name__)

# Conversational stopwords that should not inflate lexical BM25 matching
MUSIC_QUERY_STOPWORDS = {
    "what", "are", "the", "is", "a", "an", "of", "in", "for", "and", "or",
    "to", "how", "why", "does", "do", "tell", "me", "about", "can", "you",
    "please", "give", "define", "describe", "explain"
}

# Specialized regex to preserve music theory terms and symbols
# Correctly prioritizes progressions, accidentals, and specific notations with word boundaries
MUSIC_THEORY_TOKEN_PATTERN = re.compile(
    r'(?:'
    # Progressions like ii-V-I, I-IV-V, V-I
    r'\b[iIvV]{1,4}(?:-[iIvV]{1,4})+\b'
    r'|'
    # Figured bass fractions like 6/4, 6/3, 4/3, 4/2
    r'\b\d/\d\b'
    r'|'
    # Pitches with accidental and optional octave: C#, F#, Bb, Eb, C#4, F♯, E♭
    r'\b[A-Ga-g][#b♯♭]+(?:\d)?\b'
    r'|'
    # Pitch with octave number: C4, A4, G3
    r'\b[A-Ga-g]\d\b'
    r'|'
    # Scale degree notation like ^1, ^3, ^7
    r'\^[1-8]'
    r'|'
    # Roman numeral chords with alterations (e.g. V7, I6/4, IV6, vii°7, iiø7, V4/2, bVII)
    # Uses negative lookahead/lookbehind for alpha characters to prevent matching inside English words
    r'(?<![a-zA-Z])[b#♯♭]?(?:VII|vii|III|iii|VI|vi|IV|iv|II|ii|V|v|I|i)(?:[°ø\+])?(?:7|6/4|6/3|6/5|4/3|4/2|6|9)?(?![a-zA-Z])'
    r'|'
    # Standard words and numbers
    r'[a-zA-Z0-9]+(?:[\'-][a-zA-Z0-9]+)*'
    r')',
    re.UNICODE
)

def tokenize_music_theory(text: str) -> List[str]:
    """
    Tokenizes text while preserving Roman numerals, chord formulas,
    figured bass, pitch accidentals, and standard words.
    """
    if not text:
        return []
    tokens = MUSIC_THEORY_TOKEN_PATTERN.findall(text)
    normalized = []
    for t in tokens:
        t_clean = t.strip()
        if t_clean:
            normalized.append(t_clean.lower())
    return normalized

class BM25LexicalIndex:
    """
    Persistent BM25 lexical search index customized for music theory terminology.
    """

    def __init__(self, index_file: Optional[Path] = None):
        self.index_file = index_file or (settings.metadata_dir / "lexical_index.json")
        self.chunks_map: Dict[str, Chunk] = {}  # chunk_id -> Chunk
        self.corpus_chunk_ids: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.load_index()

    def add_chunks(self, chunks: List[Chunk]):
        """Adds or updates chunks in the BM25 index."""
        if not chunks:
            return

        for chunk in chunks:
            self.chunks_map[chunk.chunk_id] = chunk

        self._rebuild_bm25()
        self.save_index()
        logger.info(f"Added {len(chunks)} chunks to BM25 index. Total corpus: {len(self.corpus_chunk_ids)}")

    def delete_document(self, document_id: str) -> int:
        """Removes all chunks belonging to document_id from lexical index."""
        ids_to_remove = [
            cid for cid, c in self.chunks_map.items()
            if c.document_id == document_id
        ]
        for cid in ids_to_remove:
            del self.chunks_map[cid]

        if ids_to_remove:
            self._rebuild_bm25()
            self.save_index()
            logger.info(f"Removed {len(ids_to_remove)} chunks from BM25 index for document {document_id}")
        return len(ids_to_remove)

    def _rebuild_bm25(self):
        """Re-indexes tokenized corpus for BM25Okapi."""
        self.corpus_chunk_ids = list(self.chunks_map.keys())
        self.tokenized_corpus = [
            tokenize_music_theory(self.chunks_map[cid].content)
            for cid in self.corpus_chunk_ids
        ]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def query_lexical(self, query_text: str, top_k: int = 8) -> List[LexicalSearchResult]:
        """
        Executes BM25 keyword query and returns scored and ranked results.
        Filters conversational stop words to prevent generic query prefixes from dominating scores.
        """
        if not query_text.strip() or not self.bm25 or not self.corpus_chunk_ids:
            return []

        all_tokens = tokenize_music_theory(query_text)
        if not all_tokens:
            return []

        # Filter stopwords for BM25 matching, falling back to all tokens if only stopwords were supplied
        content_tokens = [t for t in all_tokens if t not in MUSIC_QUERY_STOPWORDS]
        tokens = content_tokens if content_tokens else all_tokens

        doc_scores = self.bm25.get_scores(tokens)
        scored_pairs = []
        for idx, score in enumerate(doc_scores):
            if score > 0.001:  # Only include non-zero keyword matches
                scored_pairs.append((self.corpus_chunk_ids[idx], float(score)))

        # Sort descending by BM25 score
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        top_pairs = scored_pairs[:top_k]

        results: List[LexicalSearchResult] = []
        for rank, (cid, score) in enumerate(top_pairs, start=1):
            chunk = self.chunks_map.get(cid)
            if chunk:
                results.append(LexicalSearchResult(
                    chunk=chunk,
                    bm25_score=round(score, 4),
                    rank=rank
                ))
        return results

    def save_index(self):
        """Persists indexed chunks metadata to JSON."""
        try:
            data = {
                "chunks": [c.model_dump() for c in self.chunks_map.values()]
            }
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist BM25 index: {e}")

    def load_index(self):
        """Loads persisted indexed chunks from JSON, falling back to ChromaDB if needed."""
        loaded_from_file = False
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                chunks = [Chunk(**item) for item in data.get("chunks", [])]
                if chunks:
                    self.chunks_map = {c.chunk_id: c for c in chunks}
                    self._rebuild_bm25()
                    loaded_from_file = True
                    logger.info(f"Loaded {len(chunks)} chunks into BM25 index from {self.index_file}")
            except Exception as e:
                logger.error(f"Failed to load BM25 index from {self.index_file}: {e}")

        # If index file was missing or empty, reconstruct from persistent vector store!
        if not loaded_from_file or not self.chunks_map:
            try:
                from app.rag.vector_store import vector_store
                stored_chunks = vector_store.get_all_chunks()
                if stored_chunks:
                    self.chunks_map = {c.chunk_id: c for c in stored_chunks}
                    self._rebuild_bm25()
                    self.save_index()
                    logger.info(f"Reconstructed BM25 index with {len(stored_chunks)} chunks directly from ChromaDB.")
            except Exception as e:
                logger.warning(f"Could not load fallback chunks from vector store for BM25: {e}")

    def clear_all(self):
        self.chunks_map.clear()
        self.corpus_chunk_ids.clear()
        self.tokenized_corpus.clear()
        self.bm25 = None
        if self.index_file.exists():
            self.index_file.unlink()

# Global singleton
lexical_index = BM25LexicalIndex()
