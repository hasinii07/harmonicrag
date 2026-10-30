import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.config import settings

client = TestClient(app)

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
