from types import SimpleNamespace
import logging

import pytest
from google import genai
from google.genai.errors import ServerError

from app.config import settings
from app.models.schemas import Chunk, FusedSearchResult, RetrievalTrace
from app.rag.generation import (
    GeminiAnswerGenerator,
    GeminiGenerationUnavailableError,
)

def _retrieved_result():
    chunk = Chunk(
        chunk_id="pac_chunk",
        document_id="cadence_manual",
        document_title="Manual of Harmony",
        author="A. Author",
        page_number=12,
        section="Cadences",
        content="A perfect authentic cadence moves from dominant harmony to tonic.",
        chunk_index=0,
        char_count=70,
    )
    return FusedSearchResult(chunk=chunk, rrf_score=0.03, final_rank=1)


def _sufficient_trace():
    return RetrievalTrace(
        query="What is a perfect authentic cadence?",
        preprocessed_query="perfect authentic cadence",
        dense_count=1,
        lexical_count=1,
        fused_count=1,
        is_evidence_sufficient=True,
    )


def test_generation_client_does_not_make_an_api_call_during_startup(monkeypatch):
    class FakeClient:
        def __init__(self, api_key, http_options):
            self.api_key = api_key
            self.http_options = http_options

    monkeypatch.setattr(genai, "Client", FakeClient)

    generator = GeminiAnswerGenerator(api_key="test-key")

    assert generator.client is not None
    assert generator.is_live is False
    assert generator.client.http_options["timeout"] == settings.GEMINI_REQUEST_TIMEOUT_MS


def test_successful_gemini_generation_preserves_normal_answer_and_citation():
    generator = GeminiAnswerGenerator(api_key=None)
    chunk = _retrieved_result().chunk
    requests = []
    response_text = (
        '{"direct_answer":"A PAC moves from dominant to tonic.",'
        '"explanation":"The dominant resolves to tonic.",'
        '"is_evidence_sufficient":true,"knowledge_source":"retrieved_sources",'
        '"candidate_citations":[{"chunk_id":"pac_chunk",'
        '"quoted_passage":"A perfect authentic cadence moves from dominant harmony to tonic."}]}'
    )
    def generate_content(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(text=response_text)

    generator.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=generate_content
        )
    )

    result = generator.generate_answer(
        query="What is a perfect authentic cadence?",
        retrieved_results=[_retrieved_result()],
        trace=_sufficient_trace(),
        conversation_id="test",
    )

    assert result.direct_answer == "A PAC moves from dominant to tonic."
    assert result.knowledge_source == "google_gemini_api"
    assert result.citations[0].chunk_id == chunk.chunk_id
    assert result.citations[0].document_title == chunk.document_title
    assert requests[0]["config"]["thinking_config"] == {"thinking_level": "LOW"}
    assert requests[0]["config"]["max_output_tokens"] == 2048
    assert requests[0]["config"]["response_mime_type"] == "application/json"


def test_quota_exhaustion_returns_verbatim_retrieval_only_response():
    generator = GeminiAnswerGenerator(api_key=None)

    def fail_generation(**kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    generator.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fail_generation)
    )
    result_chunk = _retrieved_result().chunk

    result = generator.generate_answer(
        query="What is a perfect authentic cadence?",
        retrieved_results=[_retrieved_result()],
        trace=_sufficient_trace(),
        conversation_id="test",
    )

    assert result.direct_answer.startswith("Retrieval-only response")
    assert result.knowledge_source == "retrieval_only"
    assert result.explanation == result_chunk.content
    assert len(result.citations) == 1
    assert result.citations[0].quoted_passage == result_chunk.content


def test_quota_fallback_preserves_citation_metadata_from_retrieved_chunk():
    generator = GeminiAnswerGenerator(api_key=None)

    def fail_generation(**kwargs):
        raise RuntimeError("RESOURCE_EXHAUSTED")

    generator.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fail_generation)
    )
    chunk = _retrieved_result().chunk

    result = generator.generate_answer(
        query="What is a perfect authentic cadence?",
        retrieved_results=[_retrieved_result()],
        trace=_sufficient_trace(),
        conversation_id="test",
    )

    citation = result.citations[0]
    assert citation.document_id == chunk.document_id
    assert citation.document_title == chunk.document_title
    assert citation.author == chunk.author
    assert citation.page_number == chunk.page_number
    assert citation.section == chunk.section
    assert citation.is_verified


def test_quota_exhaustion_with_insufficient_evidence_keeps_user_friendly_error():
    generator = GeminiAnswerGenerator(api_key=None)

    def fail_generation(**kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    generator.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fail_generation)
    )
    trace = _sufficient_trace()
    trace.is_evidence_sufficient = False

    with pytest.raises(
        GeminiGenerationUnavailableError,
        match="quota or rate limit has been reached.*insufficient",
    ):
        generator.generate_answer(
            query="What is a perfect authentic cadence?",
            retrieved_results=[_retrieved_result()],
            trace=trace,
            conversation_id="test",
        )


def test_generation_deadline_is_classified_logged_and_not_treated_as_quota(caplog):
    generator = GeminiAnswerGenerator(api_key="test-secret")
    error = ServerError(
        code=504,
        response_json={
            "error": {
                "code": 504,
                "message": "Deadline expired before operation could complete.",
                "status": "DEADLINE_EXCEEDED",
            }
        },
    )

    def fail_generation(**kwargs):
        raise error

    generator.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fail_generation)
    )

    with caplog.at_level(logging.WARNING, logger="app.rag.generation"):
        with pytest.raises(
            GeminiGenerationUnavailableError,
            match="temporarily unavailable or timed out",
        ):
            generator.generate_answer(
                query="What is a perfect authentic cadence?",
                retrieved_results=[_retrieved_result()],
                trace=_sufficient_trace(),
                conversation_id="test",
            )

    assert error.code == 504
    assert error.status == "DEADLINE_EXCEEDED"
    assert "exception_class=ServerError" in caplog.text
    assert "http_status=504" in caplog.text
    assert "Deadline expired before operation could complete." in caplog.text
    assert "test-secret" not in caplog.text


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (RuntimeError("API_KEY_INVALID"), "invalid_credentials"),
        (RuntimeError("404 NOT_FOUND: model unavailable"), "model_unavailable"),
        (RuntimeError("429 RESOURCE_EXHAUSTED"), "quota_exhausted"),
        (
            ServerError(
                code=504,
                response_json={
                    "error": {
                        "code": 504,
                        "message": "Deadline expired.",
                        "status": "DEADLINE_EXCEEDED",
                    }
                },
            ),
            "transient_provider_error",
        ),
        (TimeoutError("request timed out"), "network_error"),
        (RuntimeError("internal provider error"), "other_api_failure"),
    ],
)
def test_opt_in_connection_diagnostic_returns_sanitized_categories(error, category):
    generator = GeminiAnswerGenerator(api_key="test-key")

    def fail_generation(**kwargs):
        raise error

    generator.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fail_generation)
    )

    result = generator.diagnose_connection()

    assert result["configured"] is True
    assert result["tested"] is True
    assert result["success"] is False
    assert result["category"] == category
    assert "test-key" not in str(result)
    assert str(error) not in result["message"]


def test_opt_in_connection_diagnostic_sends_one_minimal_request():
    generator = GeminiAnswerGenerator(api_key="test-key", model_name="gemini-test")
    requests = []

    def generate_content(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(text="OK")

    generator.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )

    result = generator.diagnose_connection()

    assert result["success"] is True
    assert result["tested"] is True
    assert result["category"] == "ok"
    assert result["model"] == "gemini-test"
    assert len(requests) == 1
    assert requests[0]["model"] == "gemini-test"
    assert requests[0]["contents"] == "Reply with OK."


def test_connection_diagnostic_without_credentials_does_not_make_request():
    generator = GeminiAnswerGenerator(api_key=None)

    result = generator.diagnose_connection()

    assert result["configured"] is False
    assert result["tested"] is False
    assert result["category"] == "not_configured"


def test_connection_diagnostic_classifies_sdk_connect_errors_as_network_errors():
    class ConnectError(Exception):
        pass

    def fail_generation(**kwargs):
        raise ConnectError("connection refused")

    generator = GeminiAnswerGenerator(api_key="test-key")
    generator.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fail_generation)
    )

    result = generator.diagnose_connection()

    assert result["category"] == "network_error"
