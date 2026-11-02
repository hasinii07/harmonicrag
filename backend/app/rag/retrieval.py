import re
import time
import logging
from typing import List, Tuple, Dict, Any, Optional
from app.config import settings
from app.models.schemas import (
    Chunk,
    DenseSearchResult,
    LexicalSearchResult,
    FusedSearchResult,
    RetrievalTrace
)
from app.rag.vector_store import vector_store
from app.rag.lexical_search import lexical_index, tokenize_music_theory, MUSIC_QUERY_STOPWORDS
from app.rag.ranking import reciprocal_rank_fusion

logger = logging.getLogger(__name__)

# Out-of-scope keywords that indicate questions outside traditional music theory treatises
OUT_OF_SCOPE_TERMS = [
    "synthesizer", "moog", "patch", "wendy carlos", "ableton", "daw", "sidechain",
    "808", "vst", "plugin", "compression", "eq", "fl studio", "logic pro", "pro tools",
    "serum", "massive", "audio interface", "midi controller"
]

EVIDENCE_QUERY_FRAMING_TERMS = MUSIC_QUERY_STOPWORDS | {
    "requirements", "requirement", "conditions", "condition", "criteria",
    "notes", "make", "up", "list", "describe", "definition", "mean",
    "meaning", "explain", "tell", "me", "about", "does"
}

def analyze_and_expand_query(query: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Analyzes music theory query semantics, detects ambiguities, and provides
    targeted query expansion keywords to improve hybrid retrieval while preserving
    the original user query for answer generation and trace reporting.

    Returns:
        (search_query, detected_intent, interpretation_note)
    """
    q_lower = query.lower().strip()
    intent = None
    interpretation = None
    expansion_terms = []

    # 1. "7 chords" vs "seventh chords" ambiguity
    # e.g. "What are the 7 chords?", "7 chords in major", "seven chords"
    if re.search(r'\b(?:the\s+)?(?:7|seven)\s+chords?\b', q_lower) and not re.search(r'\b(?:seventh|7th)\s+chords?\b', q_lower):
        intent = "seven_diatonic_triads"
        interpretation = (
            "Interpreting 'the 7 chords' as the seven diatonic triads of a major key (I, ii, iii, IV, V, vi, vii°). "
            "If four-note seventh chords were intended, please clarify."
        )
        expansion_terms = [
            "diatonic triads seven scale degrees major key I ii iii IV V vi vii",
            "tonic supertonic mediant subdominant dominant submediant leading-tone",
            "major minor diminished"
        ]

    # 2. Seventh chords (four-note chords)
    elif re.search(r'\b(?:seventh|7th|four-note)\s+chords?\b', q_lower):
        intent = "seventh_chords"
        interpretation = "Interpreting query as four-note seventh chords and their chord qualities."
        expansion_terms = [
            "seventh chords four notes major 7th dominant 7th minor 7th half-diminished diminished 7th",
            "maj7 7 m7 m7b5 dim7 root third fifth seventh"
        ]

    # 3. Chords in a specific key (e.g. "What are the chords in C major?", "chords in G")
    elif re.search(r'\bchords\s+(?:in|of)\s+([A-Ga-g][#b♯♭]?)\s*(?:major|minor)?\b', q_lower):
        intent = "key_diatonic_chords"
        key_match = re.search(r'\bchords\s+(?:in|of)\s+([A-Ga-g][#b♯♭]?)\s*(major|minor)?\b', q_lower)
        root_key = key_match.group(1).upper() if key_match else "C"
        mode = key_match.group(2) or "major"
        interpretation = f"Interpreting query as the diatonic chords in {root_key} {mode}."
        expansion_terms = [
            f"diatonic chords triads in {root_key} {mode}",
            "I ii iii IV V vi vii tonic supertonic mediant subdominant dominant submediant leading-tone"
        ]

    # 4. Dominant seventh chord / V7
    elif re.search(r'\b(?:v7|dominant\s+seventh)\b', q_lower):
        intent = "dominant_seventh_resolution"
        expansion_terms = [
            "dominant seventh chord V7 voice leading resolution leading tone third seventh SATB"
        ]

    # 5. Modal interchange / borrowed chords
    elif re.search(r'\b(?:modal\s+interchange|mode\s+mixture|borrowed\s+chords?)\b', q_lower):
        intent = "modal_interchange"
        expansion_terms = [
            "modal interchange mode mixture borrowed chords parallel minor iv bVI bVII subdominant"
        ]

    # 6. Triad inversions / Figured bass
    elif re.search(r'\b(?:triad\s+)?inversions?\b|\b6/4\b|\b6/3\b', q_lower):
        intent = "triad_inversions"
        expansion_terms = [
            "triad inversions first inversion 6/3 second inversion 6/4 root position figured bass bass voice"
        ]

    # 7. Cadences
    elif re.search(r'\b(?:pac|authentic\s+cadence|cadences?|half\s+cadence)\b', q_lower):
        intent = "cadences"
        expansion_terms = [
            "cadence PAC perfect authentic cadence V to I root position soprano tonic"
        ]

    search_query = f"{query} {' '.join(expansion_terms)}".strip() if expansion_terms else query
    return search_query, intent, interpretation

class HybridRetriever:
    """
    Hybrid retriever combining dense vector search and BM25 lexical search
    with Reciprocal Rank Fusion (RRF). Produces a full audit trail (RetrievalTrace).
    """

    def __init__(
        self,
        top_k_dense: Optional[int] = None,
        top_k_lexical: Optional[int] = None,
        top_k_final: Optional[int] = None,
        rrf_k: Optional[int] = None,
        relevance_threshold: Optional[float] = None
    ):
        self.top_k_dense = top_k_dense or settings.TOP_K_DENSE
        self.top_k_lexical = top_k_lexical or settings.TOP_K_LEXICAL
        self.top_k_final = top_k_final or settings.TOP_K_FINAL
        self.rrf_k = rrf_k or settings.RRF_K
        self.relevance_threshold = relevance_threshold or settings.RELEVANCE_THRESHOLD

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> Tuple[List[FusedSearchResult], RetrievalTrace]:
        """
        Executes hybrid retrieval and generates an exhaustive retrieval trace.
        """
        final_k = top_k or self.top_k_final
        start_total = time.perf_counter()

        # 1. Query understanding and expansion
        search_query, intent, interpretation_note = analyze_and_expand_query(query)
        tokens = tokenize_music_theory(search_query)
        preprocessed_query = " ".join(tokens)
        q_lower = query.lower()

        # Check for explicitly uncovered/out-of-scope subjects
        is_explicitly_out_of_scope = any(
            re.search(rf"(?<!\w){re.escape(term)}(?!\w)", q_lower)
            for term in OUT_OF_SCOPE_TERMS
        )

        # 2. Dense retrieval
        t_dense_start = time.perf_counter()
        dense_results = vector_store.query_dense(search_query, top_k=self.top_k_dense)
        dense_ms = (time.perf_counter() - t_dense_start) * 1000

        # 3. Lexical BM25 retrieval
        t_lex_start = time.perf_counter()
        lexical_results = lexical_index.query_lexical(search_query, top_k=self.top_k_lexical)
        lexical_ms = (time.perf_counter() - t_lex_start) * 1000

        # 4. Reciprocal Rank Fusion
        t_fuse_start = time.perf_counter()
        raw_fused_results = reciprocal_rank_fusion(
            dense_results=dense_results,
            lexical_results=lexical_results,
            k=self.rrf_k,
            top_k_final=final_k,
            relevance_threshold=self.relevance_threshold,
            dense_weight=1.0,
            lexical_weight=1.2
        )
        fuse_ms = (time.perf_counter() - t_fuse_start) * 1000
        total_retrieval_ms = (time.perf_counter() - start_total) * 1000

        # 5. Evidence sufficiency evaluation and topical filtering
        query_content_tokens = [
            token for token in tokenize_music_theory(query)
            if token not in EVIDENCE_QUERY_FRAMING_TERMS
        ]
        if query_content_tokens and raw_fused_results:
            evidence_context = " ".join(
                f"{result.chunk.document_title} {result.chunk.content}"
                for result in raw_fused_results[:3]
            ).lower()
            matched_tokens = [
                token for token in query_content_tokens if token in evidence_context
            ]
            match_ratio = len(matched_tokens) / len(query_content_tokens)
        else:
            match_ratio = 0.0

        # Disallow sufficiency if only an incidental fraction of query terms matched (e.g. isolated word "harmonic")
        has_adequate_coverage = match_ratio >= 0.40 or len(query_content_tokens) <= 1

        has_lexical_grounding = len(lexical_results) > 0 and (lexical_results[0].bm25_score >= 2.0)
        has_strong_dense = (raw_fused_results[0].dense_score or 0.0) >= 0.60 if raw_fused_results else False
        has_moderate_hybrid = (
            len(lexical_results) > 0
            and lexical_results[0].bm25_score >= 1.5
            and (raw_fused_results[0].dense_score or 0.0) >= 0.30
        ) if raw_fused_results else False

        is_evidence_sufficient = (
            (has_lexical_grounding or has_strong_dense or has_moderate_hybrid)
            and has_adequate_coverage
            and not is_explicitly_out_of_scope
            and len(raw_fused_results) > 0
        )

        # If evidence is insufficient or out of scope, do not supply candidate chunks for citation
        fused_results = raw_fused_results if is_evidence_sufficient else []

        # Format trace data for inspection
        dense_trace = [
            {
                "chunk_id": d.chunk.chunk_id,
                "document_title": d.chunk.document_title,
                "page_number": d.chunk.page_number,
                "section": d.chunk.section,
                "cosine_score": d.cosine_score,
                "rank": d.rank,
                "preview": d.chunk.content[:160] + "..." if len(d.chunk.content) > 160 else d.chunk.content
            }
            for d in dense_results
        ]

        lexical_trace = [
            {
                "chunk_id": l.chunk.chunk_id,
                "document_title": l.chunk.document_title,
                "page_number": l.chunk.page_number,
                "section": l.chunk.section,
                "bm25_score": l.bm25_score,
                "rank": l.rank,
                "preview": l.chunk.content[:160] + "..." if len(l.chunk.content) > 160 else l.chunk.content
            }
            for l in lexical_results
        ]

        fused_trace = [
            {
                "chunk_id": f.chunk.chunk_id,
                "document_title": f.chunk.document_title,
                "page_number": f.chunk.page_number,
                "section": f.chunk.section,
                "rrf_score": f.rrf_score,
                "dense_rank": f.dense_rank,
                "dense_score": f.dense_score,
                "lexical_rank": f.lexical_rank,
                "lexical_score": f.lexical_score,
                "final_rank": f.final_rank,
                "content": f.chunk.content
            }
            for f in raw_fused_results
        ]

        selected_trace = [
            {
                "chunk_id": f.chunk.chunk_id,
                "document_title": f.chunk.document_title,
                "page_number": f.chunk.page_number,
                "section": f.chunk.section,
                "rrf_score": f.rrf_score,
                "final_rank": f.final_rank
            }
            for f in fused_results
        ]

        trace = RetrievalTrace(
            query=query,
            preprocessed_query=preprocessed_query,
            expanded_query=search_query if search_query != query else None,
            interpretation_note=interpretation_note,
            dense_count=len(dense_results),
            lexical_count=len(lexical_results),
            fused_count=len(fused_results),
            dense_results=dense_trace,
            lexical_results=lexical_trace,
            fused_results=fused_trace,
            selected_chunks=selected_trace,
            latencies_ms={
                "dense_ms": round(dense_ms, 2),
                "lexical_ms": round(lexical_ms, 2),
                "fusion_ms": round(fuse_ms, 2),
                "total_retrieval_ms": round(total_retrieval_ms, 2)
            },
            is_evidence_sufficient=is_evidence_sufficient,
            citation_validation={}
        )

        return fused_results, trace

# Global singleton
hybrid_retriever = HybridRetriever()
