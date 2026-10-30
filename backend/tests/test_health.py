import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "HarmonicRAG"
    assert "vector_store" in data
    assert "lexical_index" in data
    assert "embedding_service" in data
    assert data["vector_store"]["type"] == "ChromaDB"
    assert data["lexical_index"]["type"] == "BM25Okapi"
