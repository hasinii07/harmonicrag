from types import SimpleNamespace

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
