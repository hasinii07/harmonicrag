# HarmonicRAG — Music Theory AI Chatbot

HarmonicRAG is an evidence-grounded AI music theory research assistant built with **Python**, **Google Gemini**, **ChromaDB**, **BM25**, and **Reciprocal Rank Fusion (RRF)**. It answers complex questions on classical harmony, voice leading, figured bass, scale theory, and musical form, strictly citing instructional treatises while detecting common musical misconceptions.

---

## 🎹 Key Features

1. **Dual Hybrid Retrieval**:
   - **Dense Semantic Retrieval**: Vector embeddings stored in persistent ChromaDB with cosine similarity.
   - **Lexical Search (BM25)**: Specialized music theory tokenizer that preserves Roman numerals (e.g., `V7`, `I6/4`, `ii-V-I`), accidentals (`#`, `b`, `♯`, `♭`), and figured bass notation.
   - **Reciprocal Rank Fusion (RRF)**: Combines dense and lexical ranks ($RRF\_score = \frac{1}{60 + rank}$) to produce a deduplicated, balanced relevance ranking.

2. **Strict Evidence Grounding & Citation Validation**:
   - Every citation is validated against actual retrieved chunk IDs and source text.
   - Preserves 1-indexed page associations from PDFs and chapter sections from Markdown treatises.
   - Prevents hallucinations: non-retrieved or fabricated sources are rejected.
   - Honest abstention when evidence is insufficient or queries are out of scope.

3. **Musical Misconception Detection**:
   - Automatically detects and corrects common errors (e.g. heptatonic major scale vs 12 chromatic semitones, augmented 4th vs diminished 5th, prohibition of parallel fifths in SATB, compound 6/8 vs simple 3/4 meter).

4. **Interactive Piano & Web Audio Synthesizer**:
   - Interactive SVG/CSS piano keyboard spanning 3 octaves (C3 to B5).
   - Web Audio API polyphonic sound synthesis (sine + triangle harmonics with ADSR envelope).
   - Highlighting of scales and chord voicings with interval degree labels.
   - Playback controls: Play Simultaneous Block Chord, Ascending/Descending Scale, Arpeggio, Tempo BPM slider, and Click-to-Play.

5. **RAG Pipeline Inspector**:
   - Expandable audit trail displaying the exact query, dense search results, BM25 scores, RRF calculations, and stage-by-stage latencies.

6. **Comprehensive 6-Category Evaluation Suite**:
   - Category A: Direct in-corpus factual questions
   - Category B: Multi-passage synthesis
   - Category C: Uncovered or out-of-scope questions
   - Category D: Ambiguous musical questions
   - Category E: Incorrect musical assumptions
   - Category F: Strict citation requirements
   - Real calculated metrics: Pass Rate, Retrieval Success, Citation Precision, Citation Coverage, Abstention Performance, Latency.

---

## 🏛️ Project Structure

```
HarmonicRAG/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application & static mounting
│   │   ├── config.py                # Pydantic Settings & environment paths
│   │   ├── api/
│   │   │   ├── chat.py              # Chat endpoints & session history
│   │   │   ├── documents.py         # Upload, list, delete, & reindex
│   │   │   ├── evaluation.py        # Benchmark runner & metrics endpoints
│   │   │   └── health.py            # Health diagnostics & model status
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic schemas (Chunks, Citations, Traces)
│   │   ├── rag/
│   │   │   ├── chunking.py          # Page-preserving semantic chunker
│   │   │   ├── embeddings.py        # Gemini embedding service & local fallback
│   │   │   ├── vector_store.py      # ChromaDB persistent cosine store
│   │   │   ├── lexical_search.py    # BM25Okapi with music notation tokenizer
│   │   │   ├── ranking.py           # Reciprocal Rank Fusion (RRF)
│   │   │   ├── retrieval.py         # Hybrid search engine & audit trace
│   │   │   ├── generation.py        # Answer synthesis & misconception checks
│   │   │   └── citations.py         # Citation validation & grounding checks
│   │   └── services/
│   │       ├── chat_service.py       # Orchestration & conversation history
│   │       ├── document_service.py   # Upload & file handling
│   │       └── evaluation_service.py # 6-Category benchmark engine
│   ├── tests/
│   │   ├── test_health.py           # Health endpoint tests
│   │   ├── test_chunking.py         # Music token & page preservation tests
│   │   ├── test_retrieval.py        # BM25 & RRF fusion tests
│   │   ├── test_citations.py        # Anti-hallucination citation validator tests
│   │   └── test_api.py              # Full FastAPI integration tests
│   ├── requirements.txt             # Backend dependencies
│   └── .env.example                 # Environment configuration template
├── frontend/
│   ├── index.html                   # Semantic HTML5 single-page application
│   ├── css/
│   │   └── style.css                # Dark-mode styling, glassmorphism, piano
│   └── js/
│       ├── app.js                   # Application state & navigation routing
│       ├── chat.js                  # Chat messaging & citation drawers
│       ├── documents.js             # Knowledge base & file upload controller
│       ├── inspector.js             # RAG Pipeline Inspector
│       ├── piano.js                 # Web Audio API polyphonic synthesizer
│       └── evaluation.js            # Benchmark dashboard & metrics charts
├── data/
│   ├── documents/                   # Textbooks, Markdown treatises, & PDFs
│   ├── chroma/                      # Persistent ChromaDB vector database
│   └── metadata/                    # Document registries, BM25 index, eval logs
├── scripts/
│   ├── generate_sample_pdf.py       # Generates multi-page PDF with page numbers
│   ├── ingest_documents.py          # Batch ingestion CLI script
│   └── run_evaluation.py            # Automated benchmark CLI runner
├── .gitignore
└── README.md
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.11 or 3.12 installed on your system.

### 2. Install Dependencies
```bash
cd d:\Gen-AI\HarmonicRAG\backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create `.env` from the example only when it does not already exist. These PowerShell commands preserve any existing credentials:
```powershell
Set-Location D:\Gen-AI\HarmonicRAG\backend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```
Edit `.env` to configure your settings:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_REQUEST_TIMEOUT_MS=30000
MAX_UPLOAD_SIZE_MB=25
TOP_K_DENSE=8
TOP_K_LEXICAL=8
TOP_K_FINAL=5
RRF_K=60
HOST=127.0.0.1
PORT=8000
```
Without a Gemini API key, the application uses deterministic local token-hash embeddings and its offline response path. The Gemini client is initialized without a network request; the first real embedding operation verifies the configured model and connectivity. With credentials configured, embedding failures are surfaced rather than silently switching vector spaces. Gemini and local embeddings are different vector spaces; the application checks the Chroma collection's embedding signature and will not query or add vectors to an incompatible index. When a Gemini key is configured but answer generation fails (for example, because of quota limits), `/api/chat` returns HTTP 503 instead of presenting a synthetic response as a successful Gemini answer.

### Migrating an existing ChromaDB index

The retired `text-embedding-004` setting is normalized to `gemini-embedding-001`, but existing vectors are never modified automatically. If `/api/health` reports `vector_store.embedding_compatible: false`, run this migration from the project root using the configured Gemini key. It creates a new, separately named collection, verifies the chunk count and 768-dimensional vectors, and leaves the original collection untouched:

```powershell
Set-Location D:\Gen-AI\HarmonicRAG\backend
..\.venv\Scripts\python.exe ..\scripts\migrate_embedding_index.py
```

The application records completed migrations in `data/metadata/embedding_index_registry.json` and automatically selects a single migrated collection matching the active model. If multiple completed migrations exist, set `CHROMA_COLLECTION_NAME` to the intended collection name. If migration fails, the original collection remains available and unchanged; unregistered partial targets are never selected. Keep the registry alongside the persistent Chroma data.

---

## 🏃 Running the Application

### Start the FastAPI Server:
From any PowerShell directory, use an explicit path to enter the backend directory:
```powershell
Set-Location D:\Gen-AI\HarmonicRAG\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
If the terminal is already in `D:\Gen-AI\HarmonicRAG\backend`, do not run `cd backend` again; run only the Uvicorn command. Do not add `--reload` for normal startup. If port 8000 is already occupied, identify its owner before deciding whether to stop it; to run a separate local instance without disturbing it, use port 8001 instead:
```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```
The frontend uses same-origin `/api/...` requests, so it follows whichever local port serves the page.

Or run directly with python:
```powershell
..\.venv\Scripts\python.exe -m app.main
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### Production Deployment (Docker / Render)

The frontend is plain HTML, CSS, and JavaScript served by the FastAPI application; it is not a standalone static-site build. Do not deploy it as a static-only Vercel site: the client requires FastAPI routes. The container uses Python 3.11 and the pinned runtime dependencies in `backend/requirements-runtime.txt`. Its startup command initializes an empty ChromaDB/BM25 knowledge base from the bundled `data/documents/` files, then starts Uvicorn.

Build and run locally with a persistent Docker volume:

```powershell
docker build -t harmonicrag .
docker volume create harmonicrag-data
docker run --rm -p 10000:10000 `
  --env-file C:\path\outside\the\project\harmonicrag.env `
  -e HOST=0.0.0.0 -e PORT=10000 `
  -e CHROMA_PERSIST_DIRECTORY=/var/data/chroma `
  -e DOCUMENT_STORAGE_DIRECTORY=/var/data/documents `
  -e METADATA_STORAGE_DIRECTORY=/var/data/metadata `
  -v harmonicrag-data:/var/data harmonicrag
```

Keep the environment file outside the project and out of source control. Configure `GEMINI_API_KEY`, `GEMINI_MODEL`, and `GEMINI_EMBEDDING_MODEL` with values supported by the selected Google AI account. Legacy `GOOGLE_API_KEY` remains a fallback when `GEMINI_API_KEY` is absent. Use `gemini-embedding-001` for the existing 768-dimensional migrated index. When no Gemini key is configured, the app uses local token-hash embeddings and deterministic answer generation. When a key is configured, provider failures are reported rather than silently switching embedding spaces; quota exhaustion permits a clearly labelled retrieval-only answer when retrieved evidence is sufficient.

The regular `/api/health` check never calls Gemini. To explicitly test credentials, model availability, network access, and generation permission (one small real request that may consume quota), send:
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/health/gemini/diagnostic `
  -ContentType 'application/json' -Body '{"confirm":true}'
```
The response contains a sanitized category (`ok`, `invalid_credentials`, `model_unavailable`, `quota_exhausted`, `network_error`, or `other_api_failure`) and safe message, never credentials or raw provider errors. Model access is account-specific.

The supported deployment serves the frontend and API together from FastAPI, so leave `API_BASE_URL` and `CORS_ALLOWED_ORIGINS` empty and use same-origin requests. Although the backend exposes these settings, the current static frontend has no separate-host build-time configuration; setting `API_BASE_URL` in the backend alone does not configure a separately hosted frontend. Do not deploy the frontend as a separate static site unless you add and verify an explicit frontend configuration/build step.

For a managed deployment, Render's Docker web service is a suitable fit:

1. Create a **Web Service** from the repository and select **Docker** with the repository-root `Dockerfile` (Docker build context is the repository root).
2. Attach one persistent disk mounted at `/var/data`.
3. Configure `HOST=0.0.0.0`, the three storage paths shown in the Docker command, `GEMINI_API_KEY` as a secret, `GEMINI_MODEL` as an account-supported generation model, and `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`. Render supplies `PORT`; the container command consumes it. Leave `API_BASE_URL` and `CORS_ALLOWED_ORIGINS` empty for the integrated frontend.
4. Set the health-check path to `/api/health`, deploy, and verify the service reports a compatible embedding index and matching Chroma/BM25 counts.
5. Keep the service to one instance: ChromaDB uses local persistent storage and is not a multi-instance shared database.

The persistent disk must hold ChromaDB, uploaded documents, and metadata together. Keep any existing compatible data and its `embedding_index_registry.json` together; do not attach an empty disk expecting it to contain local developer data automatically.

**Do not expose this service publicly until authentication, per-user conversation isolation, authorization for document mutation, and request rate limits are implemented.** The current API is unauthenticated, and conversation history is held in a process-wide in-memory store. A persistent disk does not make that state private or multi-instance safe. No service is deployed by these instructions.

---

## 🧪 Testing and Benchmarks

### 1. Run Automated Unit & Integration Tests
Execute the pytest suite:
```bash
python -m pytest d:\Gen-AI\HarmonicRAG\backend\tests -v
```
The backend pytest suite validates:
- System health and diagnostics
- Preservation of page numbers during chunking
- Music theory token preservation in BM25
- Reciprocal Rank Fusion ranking
- Anti-hallucination citation rejection
- Full API chat and upload flows

### 2. Run the 6-Category Evaluation Suite
```bash
python d:\Gen-AI\HarmonicRAG\scripts\run_evaluation.py
```
Output includes:
- Pass Rate
- Retrieval Success Rate
- Citation Precision & Coverage
- Abstention Performance
- Breakdown by categories A through F

---

## 📚 Adding Reference Treatises

To ingest additional harmony and music theory treatises:
1. Place PDF, Markdown (`.md`), or Text (`.txt`) files in `data/documents/`.
2. Run the batch ingestion script:
   ```bash
   python d:\Gen-AI\HarmonicRAG\scripts\ingest_documents.py
   ```
3. Or use the **Knowledge Base** tab in the web UI to drag-and-drop files or paste text notes directly.
