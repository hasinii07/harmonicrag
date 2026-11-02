import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.config import Settings, settings
from app.rag.generation import GeminiGenerationUnavailableError
from app.rag.generation import answer_generator
from app.services.chat_service import chat_service

client = TestClient(app)

def test_gemini_api_key_is_preferred_over_legacy_google_api_key():
    configured = Settings(
        _env_file=None,
        GEMINI_API_KEY="gemini-test-key",
        GOOGLE_API_KEY="legacy-test-key",
    )
    assert configured.api_key == "gemini-test-key"


def test_legacy_google_api_key_remains_supported():
    configured = Settings(_env_file=None, GOOGLE_API_KEY="legacy-test-key")
    assert configured.api_key == "legacy-test-key"


def test_api_chat_flow():
    payload = {
        "message": "What is a Perfect Authentic Cadence (PAC)?",
        "include_trace": True
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "direct_answer" in data
    assert "explanation" in data
    assert "retrieval_trace" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert data["retrieval_trace"]["dense_count"] >= 0
    assert data["retrieval_trace"]["lexical_count"] >= 0

def test_api_chat_request_limits():
    oversized_message = client.post("/api/chat", json={"message": "x" * 4001})
    excessive_top_k = client.post("/api/chat", json={"message": "major triad", "top_k": 21})

    assert oversized_message.status_code == 422
    assert excessive_top_k.status_code == 422


def test_api_config_script_uses_configured_backend_origin(monkeypatch):
    monkeypatch.setattr(settings, "API_BASE_URL", "https://api.example.test/")

    response = client.get("/api/config.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert 'window.HARMONICRAG_API_BASE_URL = "https://api.example.test";' in response.text


def test_api_config_defaults_to_same_origin(monkeypatch):
    monkeypatch.setattr(settings, "API_BASE_URL", "")

    response = client.get("/api/config.js")

    assert response.status_code == 200
    assert response.text == 'window.HARMONICRAG_API_BASE_URL = "";'


def test_cors_origins_are_explicit_and_normalized(monkeypatch):
    monkeypatch.setattr(
        settings,
        "CORS_ALLOWED_ORIGINS",
        " https://frontend.example.test/ , https://admin.example.test ",
    )

    assert settings.cors_allowed_origins == [
        "https://frontend.example.test",
        "https://admin.example.test",
    ]


def test_api_chat_surfaces_gemini_unavailability(monkeypatch):
    def fail_generation(request):
        raise GeminiGenerationUnavailableError(
            "Gemini answer generation is currently unavailable."
        )

    monkeypatch.setattr(chat_service, "process_message", fail_generation)

    response = client.post("/api/chat", json={"message": "What is a major triad?"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Gemini answer generation is currently unavailable."


def test_api_chat_returns_user_friendly_deadline_error(monkeypatch):
    def fail_generation(request):
        raise GeminiGenerationUnavailableError(
            "Gemini is temporarily unavailable or timed out. Please try again later."
        )

    monkeypatch.setattr(chat_service, "process_message", fail_generation)

    response = client.post("/api/chat", json={"message": "What is a major triad?"})

    assert response.status_code == 503
    assert "timed out" in response.json()["detail"]


def test_gemini_diagnostic_requires_explicit_confirmation():
    response = client.post("/api/health/gemini/diagnostic", json={})
    assert response.status_code == 422


def test_gemini_diagnostic_endpoint_is_opt_in_and_sanitized(monkeypatch):
    monkeypatch.setattr(
        answer_generator,
        "diagnose_connection",
        lambda: {
            "configured": True,
            "tested": True,
            "success": False,
            "category": "quota_exhausted",
            "model": "gemini-test",
            "message": "Gemini API quota or rate limit has been reached.",
        },
    )

    response = client.post("/api/health/gemini/diagnostic", json={"confirm": True})

    assert response.status_code == 200
    assert response.json()["category"] == "quota_exhausted"
    assert "key" not in response.text.lower()


def test_health_does_not_claim_untested_gemini_connection(monkeypatch):
    monkeypatch.setattr(answer_generator, "last_connection_test", None)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["gemini_generation"]["configured"] == bool(
        settings.api_key and settings.api_key.strip()
    )
    assert data["gemini_generation"]["connection_tested"] is False

def test_api_documents_listing():
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total_count" in data
    assert "total_chunks" in data
    assert data["total_count"] >= 1

def test_api_text_ingestion():
    payload = {
        "title": "Modal Scales Quick Notes",
        "author": "Test Author",
        "content": "Dorian mode is characterized by a minor third and natural major sixth (1-2-b3-4-5-6-b7)."
    }
    response = client.post("/api/documents/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Modal Scales Quick Notes"
    assert data["chunk_count"] >= 1
    assert data["status"] == "indexed"

def test_api_upload_sanitizes_filename():
    filename = f"..\\..\\upload-{uuid.uuid4().hex}.txt"
    content = f"Upload traversal regression fixture {uuid.uuid4().hex}."

    response = client.post(
        "/api/documents/upload",
        files={"file": (filename, content, "text/plain")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == Path(filename.replace("\\", "/")).name
    stored_path = (settings.documents_dir / data["filename"]).resolve()
    assert stored_path.parent == settings.documents_dir.resolve()
    assert stored_path.is_file()

def test_api_upload_rejects_oversized_file(monkeypatch):
    filename = f"oversized-{uuid.uuid4().hex}.txt"
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)

    response = client.post(
        "/api/documents/upload",
        files={"file": (filename, "too large", "text/plain")}
    )

    assert response.status_code == 400
    assert "maximum size" in response.json()["detail"].lower()
    assert not (settings.documents_dir / filename).exists()

def test_api_evaluation_endpoints():
    # Run evaluation
    run_resp = client.post("/api/evaluation/run")
    assert run_resp.status_code == 200
    report = run_resp.json()
    assert report["total_tests"] >= 12
    assert "pass_rate_pct" in report
    assert "avg_latency_ms" in report

    # Fetch latest evaluation results
    get_resp = client.get("/api/evaluation/results")
    assert get_resp.status_code == 200
    assert get_resp.json()["total_tests"] >= 12
