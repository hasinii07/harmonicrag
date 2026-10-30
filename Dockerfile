FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    HOST=0.0.0.0 \
    FRONTEND_DIRECTORY=/app/frontend \
    CHROMA_PERSIST_DIRECTORY=/var/data/chroma \
    DOCUMENT_STORAGE_DIRECTORY=/var/data/documents \
    METADATA_STORAGE_DIRECTORY=/var/data/metadata

WORKDIR /app

COPY backend/requirements-runtime.txt /app/backend/requirements-runtime.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements-runtime.txt

COPY backend/app /app/backend/app
COPY frontend /app/frontend
COPY scripts/ingest_documents.py /app/scripts/ingest_documents.py
COPY scripts/ensure_knowledge_base.py /app/scripts/ensure_knowledge_base.py
COPY data/documents /app/data/documents

RUN mkdir -p /var/data/chroma /var/data/documents /var/data/metadata

EXPOSE 10000

CMD ["sh", "-c", "python /app/scripts/ensure_knowledge_base.py && exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
