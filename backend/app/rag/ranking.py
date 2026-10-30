from typing import List, Dict, Optional
from app.config import settings
from app.models.schemas import (
    DenseSearchResult,
    LexicalSearchResult,
    FusedSearchResult,
    Chunk
)

def reciprocal_rank_fusion(
    dense_results: List[DenseSearchResult],
    lexical_results: List[LexicalSearchResult],
    k: int = 60,
    top_k_final: int = 5,
    relevance_threshold: float = 0.005,
    dense_weight: float = 1.0,
    lexical_weight: float = 1.0
) -> List[FusedSearchResult]:
    """
    Combines dense semantic and lexical BM25 rankings using Reciprocal Rank Fusion:
    RRF_score(d) = w_dense / (k + dense_rank) + w_lexical / (k + lexical_rank)
    
    Returns deduplicated, fused results ranked by combined score.
    """
    fused_scores: Dict[str, float] = {}
    dense_info: Dict[str, tuple[int, float]] = {}  # chunk_id -> (rank, score)
    lexical_info: Dict[str, tuple[int, float]] = {}  # chunk_id -> (rank, score)
    chunks_by_id: Dict[str, Chunk] = {}

    for d in dense_results:
        cid = d.chunk.chunk_id
        chunks_by_id[cid] = d.chunk
        dense_info[cid] = (d.rank, d.cosine_score)
        fused_scores[cid] = fused_scores.get(cid, 0.0) + (dense_weight / (k + d.rank))

    for l in lexical_results:
        cid = l.chunk.chunk_id
        chunks_by_id[cid] = l.chunk
        lexical_info[cid] = (l.rank, l.bm25_score)
        fused_scores[cid] = fused_scores.get(cid, 0.0) + (lexical_weight / (k + l.rank))

    # Sort descending by fused RRF score
    sorted_items = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

    fused_results: List[FusedSearchResult] = []
    final_rank = 1

    for cid, rrf_score in sorted_items:
        if rrf_score < relevance_threshold:
            continue

        chunk = chunks_by_id[cid]
        d_rank, d_score = dense_info.get(cid, (None, None))
        l_rank, l_score = lexical_info.get(cid, (None, None))

        fused_results.append(FusedSearchResult(
            chunk=chunk,
            rrf_score=round(rrf_score, 6),
            dense_rank=d_rank,
            dense_score=round(d_score, 4) if d_score is not None else None,
            lexical_rank=l_rank,
            lexical_score=round(l_score, 4) if l_score is not None else None,
            final_rank=final_rank
        ))
        final_rank += 1
        if len(fused_results) >= top_k_final:
            break

    return fused_results
