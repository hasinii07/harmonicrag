from google import genai

from app.config import settings
from app.rag.generation import GeminiAnswerGenerator


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
