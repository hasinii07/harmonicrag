import pytest
from types import SimpleNamespace
from google import genai

from app.config import _normalize_embedding_model
from app.rag.embeddings import GeminiEmbeddingService


class FakeEmbeddingModels:
    def __init__(self):
        self.calls = []

    def embed_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        count = len(contents) if isinstance(contents, list) else 1
        vector = [3.0] + [0.0] * 767
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=vector)
                for _ in range(count)
            ]
        )


def test_gemini_embeddings_use_retrieval_tasks_and_768_dimensions():
    service = GeminiEmbeddingService.__new__(GeminiEmbeddingService)
    service.dimension = 768
    service.model_name = "gemini-embedding-001"
    service.is_live = True
    service.api_key = "test-key"
    models = FakeEmbeddingModels()
    service.client = SimpleNamespace(models=models)

    document_vector = service.embed_documents(["A harmony document"])[0]
    query_vector = service.embed_query("What is a cadence?")

    assert len(document_vector) == 768
    assert len(query_vector) == 768
    assert sum(value * value for value in document_vector) == 1.0
    assert sum(value * value for value in query_vector) == 1.0
    assert models.calls[0]["config"] == {
        "output_dimensionality": 768,
        "task_type": "RETRIEVAL_DOCUMENT"
    }
    assert models.calls[1]["config"] == {
        "output_dimensionality": 768,
        "task_type": "RETRIEVAL_QUERY"
    }


def test_retired_embedding_model_is_normalized():
    assert _normalize_embedding_model("text-embedding-004") == "gemini-embedding-001"
    assert _normalize_embedding_model("gemini-embedding-001") == "gemini-embedding-001"


def test_embedding_client_does_not_make_a_network_request_during_initialization(monkeypatch):
    class FakeModels:
        def embed_content(self, **kwargs):
            raise AssertionError("Embedding request must be deferred until use.")

    class FakeClient:
        def __init__(self, api_key, http_options):
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)
    service = GeminiEmbeddingService(api_key="test-key")

    assert service.client is not None
    assert service.is_live is False
    assert service.index_signature == "google-genai:gemini-embedding-001:dim768"
    assert service.get_model_info()["mode"] == "configured_not_verified"


def test_configured_gemini_probe_failure_does_not_use_local_vectors(monkeypatch):
    class FailingModels:
        def embed_content(self, **kwargs):
            raise TimeoutError("API unavailable")

    class FakeClient:
        def __init__(self, api_key, http_options):
            self.models = FailingModels()

    monkeypatch.setattr(genai, "Client", FakeClient)
    service = GeminiEmbeddingService(api_key="test-key")

    with pytest.raises(RuntimeError, match="Gemini query embedding failed"):
        service.embed_query("What is a cadence?")
    assert service.index_signature == "google-genai:gemini-embedding-001:dim768"
    assert service.get_model_info()["mode"] == "unavailable"


def test_live_embedding_failure_does_not_fall_back_to_another_vector_space():
    class FailingModels:
        def embed_content(self, **kwargs):
            raise TimeoutError("API unavailable")

    service = GeminiEmbeddingService.__new__(GeminiEmbeddingService)
    service.dimension = 768
    service.model_name = "gemini-embedding-001"
    service.is_live = True
    service.client = SimpleNamespace(models=FailingModels())
    service.api_key = "test-key"

    with pytest.raises(RuntimeError, match="Gemini query embedding failed"):
        service.embed_query("What is a cadence?")


def test_deterministic_fallback_has_stable_dimension_and_normalization():
    service = GeminiEmbeddingService.__new__(GeminiEmbeddingService)
    service.dimension = 768
    service.api_key = None

    vector = service._fallback_embed("A perfect authentic cadence")

    assert len(vector) == 768
    assert sum(value * value for value in vector) == pytest.approx(1.0)
