import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.models.schemas import Chunk, FusedSearchResult
from app.rag.citations import validate_and_filter_citations

def test_citation_validation_genuine_chunk():
    chunk = Chunk(
        chunk_id="chunk_valid_1",
        document_id="doc_1",
        document_title="Manual of Harmony",
        page_number=3,
        section="Chapter III",
        content="Consecutive parallel fifths and octaves are prohibited in strict SATB.",
        chunk_index=0,
        char_count=70
    )
    fused_item = FusedSearchResult(
        chunk=chunk,
        rrf_score=0.03,
        dense_rank=1,
        lexical_rank=1,
        final_rank=1
    )

    candidate_citations = [
        {"chunk_id": "chunk_valid_1", "quoted_passage": "parallel fifths and octaves are prohibited"}
    ]

    valid, summary = validate_and_filter_citations(candidate_citations, [fused_item])
    assert len(valid) == 1
    assert valid[0].chunk_id == "chunk_valid_1"
    assert valid[0].document_title == "Manual of Harmony"
    assert valid[0].page_number == 3
    assert valid[0].is_verified is True
    assert summary["verified_count"] == 1
    assert summary["rejected_count"] == 0

def test_citation_validation_rejects_hallucinated_chunk():
    chunk = Chunk(
        chunk_id="real_chunk_42",
        document_id="doc_real",
        document_title="Real Treatise",
        content="Actual content.",
        chunk_index=0,
        char_count=15
    )
    fused_item = FusedSearchResult(chunk=chunk, rrf_score=0.02, final_rank=1)

    candidate_citations = [
        {"chunk_id": "fabricated_chunk_99", "quoted_passage": "Fictitious quote"}
    ]

    valid, summary = validate_and_filter_citations(candidate_citations, [fused_item])
    # The fabricated chunk must be rejected
    assert summary["rejected_count"] == 1
    assert any("fabricated_chunk_99" in r["reason"] for r in summary["rejected_details"])


def test_citation_validation_rejects_fabricated_quote():
    chunk = Chunk(
        chunk_id="real_chunk_quote",
        document_id="doc_real",
        document_title="Real Treatise",
        content="A perfect cadence moves from dominant to tonic.",
        chunk_index=0,
        char_count=48
    )
    fused_item = FusedSearchResult(
        chunk=chunk,
        rrf_score=0.02,
        final_rank=1
    )

    valid, summary = validate_and_filter_citations(
        [{
            "chunk_id": "real_chunk_quote",
            "quoted_passage": "A perfect cadence resolves to a deceptive chord."
        }],
        [fused_item]
    )

    assert summary["rejected_count"] == 1
    assert summary["precision"] == 0.0
    assert "not present" in summary["rejected_details"][0]["reason"]
    assert valid
    assert valid[0].quoted_passage.startswith("A perfect cadence moves")
