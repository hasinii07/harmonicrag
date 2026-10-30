import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.models.schemas import ChatRequest
from app.rag.retrieval import hybrid_retriever
from app.rag.generation import GeminiAnswerGenerator
from app.services.chat_service import chat_service
from app.rag.vector_store import vector_store

def test_01_seven_chords_retrieves_diatonic_triads():
    """1. 'What are the 7 chords?' retrieves diatonic triad material and avoids modal interchange."""
    fused, trace = hybrid_retriever.retrieve("What are the 7 chords?", top_k=3)
    assert len(fused) > 0
    top_doc = fused[0].chunk.document_title
    # Must retrieve diatonic harmony, NOT modal interchange
    assert "Modal Interchange" not in top_doc
    assert "Harmony and Voice Leading" in top_doc or "Questions and Analysis" in top_doc

    req = ChatRequest(message="What are the 7 chords?")
    resp = chat_service.process_message(req)
    combined = (resp.direct_answer + " " + resp.explanation).lower()

    # Must explain diatonic triads
    assert "triad" in combined
    assert "major" in combined
    assert "modal interchange" not in combined
    assert resp.is_evidence_sufficient is True
    assert len(resp.citations) > 0
    assert all(c.is_verified for c in resp.citations)

def test_02_seventh_chords_retrieves_four_note_chords():
    """2. 'What are seventh chords?' retrieves four-note chord material."""
    req = ChatRequest(message="What are seventh chords?")
    resp = chat_service.process_message(req)
    combined = (resp.direct_answer + " " + resp.explanation).lower()

    assert "four-note" in combined or "four note" in combined or "seventh" in combined
    assert "dominant 7th" in combined or "major 7th" in combined or "seventh chord" in combined
    assert resp.is_evidence_sufficient is True

def test_03_chords_in_c_major():
    """3. 'What are the chords in C major?' produces the correct seven triads."""
    req = ChatRequest(message="What are the chords in C major?")
    resp = chat_service.process_message(req)
    combined = (resp.direct_answer + " " + resp.explanation).lower()

    assert "c major" in combined or "c (" in combined
    assert "d minor" in combined or "dm" in combined
    assert "b diminished" in combined or "bdim" in combined
    assert resp.is_evidence_sufficient is True

def test_04_modal_interchange_retrieval():
    """4. 'Explain modal interchange' retrieves modal interchange material."""
    fused, trace = hybrid_retriever.retrieve("Explain modal interchange", top_k=3)
    assert len(fused) > 0
    top_doc = fused[0].chunk.document_title
    assert "Modal Interchange" in top_doc

    req = ChatRequest(message="Explain modal interchange.")
    resp = chat_service.process_message(req)
    combined = (resp.direct_answer + " " + resp.explanation).lower()
    assert "modal interchange" in combined
    assert "borrowed" in combined
    assert resp.is_evidence_sufficient is True

def test_05_v7_chord_retrieves_dominant_seventh():
    """5. 'What is a V7 chord?' retrieves dominant seventh material."""
    fused, trace = hybrid_retriever.retrieve("What is a V7 chord?", top_k=3)
    assert len(fused) > 0
    top_doc = fused[0].chunk.document_title
    assert "Harmony and Voice Leading" in top_doc

    req = ChatRequest(message="What is a V7 chord?")
    resp = chat_service.process_message(req)
    combined = (resp.direct_answer + " " + resp.explanation).lower()
    assert "dominant" in combined
    assert "fifth" in combined or "v7" in combined
    assert resp.is_evidence_sufficient is True

def test_06_out_of_scope_no_fabricated_citations():
    """6. An out-of-scope question does not receive fabricated citations."""
    req = ChatRequest(message="What exact Moog modular synthesizer patch settings did Wendy Carlos use on Brandenburg Concerto No. 3?")
    resp = chat_service.process_message(req)
    assert resp.is_evidence_sufficient is False
    assert len(resp.citations) == 0
    assert "does not contain" in resp.direct_answer.lower() or "insufficient" in resp.direct_answer.lower()

def test_07_missing_source_triggers_honest_limitation():
    """7. Missing source material triggers an honest limitation response."""
    req = ChatRequest(message="What are the harmonic acoustics of the lost underwater organ of Atlantis in 432Hz?")
    resp = chat_service.process_message(req)
    assert resp.is_evidence_sufficient is False
    assert len(resp.citations) == 0
    assert "does not contain" in resp.direct_answer.lower() or "insufficient" in resp.direct_answer.lower()

def test_08_citation_metadata_corresponds_to_actual_chunks():
    """8. Citation metadata corresponds to actual retrieved chunks."""
    req = ChatRequest(message="What is a Perfect Authentic Cadence (PAC)?")
    resp = chat_service.process_message(req)
    assert resp.is_evidence_sufficient is True
    assert len(resp.citations) > 0

    all_chunks = {c.chunk_id: c for c in vector_store.get_all_chunks()}
    for cit in resp.citations:
        assert cit.is_verified is True
        assert cit.chunk_id in all_chunks
        actual_chunk = all_chunks[cit.chunk_id]
        assert cit.document_title == actual_chunk.document_title
        if actual_chunk.page_number is not None:
            assert cit.page_number == actual_chunk.page_number

def test_09_retrieval_diagnostics_expose_dense_bm25_rrf():
    """9. Retrieval diagnostics expose dense, BM25, and RRF results."""
    fused, trace = hybrid_retriever.retrieve("major triad root fifth", top_k=3)
    assert trace.dense_count > 0
    assert trace.lexical_count > 0
    assert trace.fused_count > 0

    assert len(trace.dense_results) > 0
    assert "cosine_score" in trace.dense_results[0]

    assert len(trace.lexical_results) > 0
    assert "bm25_score" in trace.lexical_results[0]

    assert len(trace.fused_results) > 0
    assert "rrf_score" in trace.fused_results[0]

    assert "dense_ms" in trace.latencies_ms
    assert "lexical_ms" in trace.latencies_ms
    assert "fusion_ms" in trace.latencies_ms
    assert "total_retrieval_ms" in trace.latencies_ms

def test_10_pipeline_fallback_when_gemini_unavailable():
    """10. The pipeline continues working when Gemini is unavailable, using the project's supported fallback behavior."""
    offline_generator = GeminiAnswerGenerator(api_key=None)
    assert offline_generator.is_live is False

    fused, trace = hybrid_retriever.retrieve("What is a V7 chord?", top_k=2)
    resp = offline_generator.generate_answer(
        query="What is a V7 chord?",
        retrieved_results=fused,
        trace=trace,
        conversation_id="test_offline_conv"
    )
    assert resp is not None
    assert "dominant" in resp.direct_answer.lower()
    assert resp.is_evidence_sufficient is True
    assert len(resp.citations) > 0
    assert resp.visualizer is not None
