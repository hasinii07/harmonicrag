import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.models.schemas import Chunk, DenseSearchResult, LexicalSearchResult
from app.rag.lexical_search import tokenize_music_theory, BM25LexicalIndex
from app.rag.ranking import reciprocal_rank_fusion
from app.rag.retrieval import hybrid_retriever

def test_tokenize_music_theory():
    text = "In ii-V-I cadences, V7 resolves to I6/4 with PAC in SATB."
    tokens = tokenize_music_theory(text)
    assert "ii-v-i" in tokens
    assert "v7" in tokens
    assert "i6/4" in tokens
    assert "pac" in tokens
    assert "satb" in tokens

def test_reciprocal_rank_fusion():
    chunk1 = Chunk(chunk_id="c1", document_id="d1", document_title="T1", content="Text 1", chunk_index=0, char_count=6)
    chunk2 = Chunk(chunk_id="c2", document_id="d1", document_title="T1", content="Text 2", chunk_index=1, char_count=6)

    dense = [
        DenseSearchResult(chunk=chunk1, cosine_score=0.9, rank=1),
        DenseSearchResult(chunk=chunk2, cosine_score=0.7, rank=2)
    ]
    lexical = [
        LexicalSearchResult(chunk=chunk2, bm25_score=5.0, rank=1),
        LexicalSearchResult(chunk=chunk1, bm25_score=3.0, rank=2)
    ]

    fused = reciprocal_rank_fusion(dense_results=dense, lexical_results=lexical, k=60, top_k_final=2)
    assert len(fused) == 2
    # RRF scores should be positive
    assert fused[0].rrf_score > 0.0
    assert fused[1].rrf_score > 0.0
    # Both chunks should be present
    cids = {f.chunk.chunk_id for f in fused}
    assert "c1" in cids
    assert "c2" in cids

def test_hybrid_retrieval_trace():
    results, trace = hybrid_retriever.retrieve("major triad root fifth", top_k=3)
    assert trace.query == "major triad root fifth"
    assert "dense_ms" in trace.latencies_ms
    assert "lexical_ms" in trace.latencies_ms
    assert "total_retrieval_ms" in trace.latencies_ms
    assert isinstance(results, list)
