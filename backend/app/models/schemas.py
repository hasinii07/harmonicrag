from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# Document and Chunk Models
# ------------------------------------------------------------------------------

class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    author: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    content: str
    chunk_index: int
    char_count: int

class DocumentMetadata(BaseModel):
    id: str
    filename: str
    title: str
    author: Optional[str] = "Unknown"
    file_type: str
    file_size_bytes: int
    page_count: int = 1
    chunk_count: int = 0
    status: str = "indexed"  # "indexed", "indexing", "failed"
    created_at: str
    checksum: str
    error_message: Optional[str] = None

# ------------------------------------------------------------------------------
# Retrieval Models
# ------------------------------------------------------------------------------

class DenseSearchResult(BaseModel):
    chunk: Chunk
    cosine_score: float
    rank: int

class LexicalSearchResult(BaseModel):
    chunk: Chunk
    bm25_score: float
    rank: int

class FusedSearchResult(BaseModel):
    chunk: Chunk
    rrf_score: float
    dense_rank: Optional[int] = None
    dense_score: Optional[float] = None
    lexical_rank: Optional[int] = None
    lexical_score: Optional[float] = None
    final_rank: int

class RetrievalTrace(BaseModel):
    query: str
    preprocessed_query: str
    expanded_query: Optional[str] = None
    interpretation_note: Optional[str] = None
    dense_count: int
    lexical_count: int
    fused_count: int
    dense_results: List[Dict[str, Any]] = []
    lexical_results: List[Dict[str, Any]] = []
    fused_results: List[Dict[str, Any]] = []
    selected_chunks: List[Dict[str, Any]] = []
    latencies_ms: Dict[str, float] = {}
    is_evidence_sufficient: bool = False
    citation_validation: Dict[str, Any] = {}

# ------------------------------------------------------------------------------
# Music Visualizer & Citations
# ------------------------------------------------------------------------------

class MusicVisualizerData(BaseModel):
    type: str = "notes"  # "scale", "chord", "progression", "notes", "interval"
    root: Optional[str] = None
    notes: List[str] = []  # e.g., ["C4", "E4", "G4", "B4"]
    formula: Optional[str] = None  # e.g., "1 - 3 - 5 - 7"
    intervals: Optional[List[str]] = None  # e.g., ["Root", "Major 3rd", "Perfect 5th"]
    description: Optional[str] = None
    octave_start: int = 4
    octave_count: int = 2

class CitationRef(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    author: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    quoted_passage: str
    is_verified: bool = True

# ------------------------------------------------------------------------------
# Chat Request & Response
# ------------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    include_trace: bool = True

class ChatResponse(BaseModel):
    conversation_id: str
    direct_answer: str
    explanation: str
    musical_example: Optional[str] = None
    misconception_correction: Optional[str] = None
    is_evidence_sufficient: bool
    knowledge_source: str  # "retrieved_sources", "general_theory_supplement", "insufficient_evidence"
    citations: List[CitationRef] = []
    visualizer: Optional[MusicVisualizerData] = None
    retrieval_trace: RetrievalTrace

# ------------------------------------------------------------------------------
# Ingestion API Models
# ------------------------------------------------------------------------------

class TextIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: Optional[str] = Field(default="Unknown", max_length=200)
    content: str = Field(min_length=1, max_length=25 * 1024 * 1024)

class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    total_count: int
    total_chunks: int

# ------------------------------------------------------------------------------
# Evaluation Models
# ------------------------------------------------------------------------------

class EvaluationTestCase(BaseModel):
    test_id: str
    category: str  # A, B, C, D, E, F
    category_name: str
    question: str
    expected_behavior: str
    expected_source_ids: Optional[List[str]] = None
    actual_answer: Optional[str] = None
    retrieved_chunk_ids: List[str] = []
    citations: List[str] = []
    status: str = "pending"  # "pass", "fail", "pending"
    criteria: str
    failure_reason: Optional[str] = None
    retrieval_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0

class EvaluationReport(BaseModel):
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate_pct: float
    retrieval_success_rate_pct: float
    citation_precision_pct: float
    citation_coverage_pct: float
    unsupported_answer_rate_pct: float
    abstention_performance_pct: float
    avg_latency_ms: float
    evaluated_at: str
    cases: List[EvaluationTestCase]
