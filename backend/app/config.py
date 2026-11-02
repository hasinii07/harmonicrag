from pathlib import Path
from typing import Optional
import os
import logging
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

def _normalize_embedding_model(value: str) -> str:
    if isinstance(value, str) and value.strip().lower() == "text-embedding-004":
        logger.warning(
            "GEMINI_EMBEDDING_MODEL=text-embedding-004 is no longer available; "
            "using gemini-embedding-001. Re-embed the existing index before dense retrieval."
        )
        return "gemini-embedding-001"
    return value


# Base directories anchored to this file's physical location
BASE_BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_BACKEND_DIR.parent
CANONICAL_DATA_DIR = PROJECT_ROOT / "data"

def _resolve_canonical_dir(configured_path: str, default_subdir: str) -> Path:
    """
    Ensures storage paths always resolve to the canonical project data directory
    regardless of the current working directory from which uvicorn or python is executed.
    """
    target_canonical = CANONICAL_DATA_DIR / default_subdir
    if not configured_path or not configured_path.strip():
        target_canonical.mkdir(parents=True, exist_ok=True)
        return target_canonical

    p = Path(configured_path.strip())
    # If absolute path provided, use it
    if p.is_absolute():
        p.mkdir(parents=True, exist_ok=True)
        return p

    # If relative path matches or contains the subdirectory name, anchor strictly to CANONICAL_DATA_DIR
    target_canonical.mkdir(parents=True, exist_ok=True)
    return target_canonical

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Keys
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None  # Alternative alias

    # Gemini Models (Use models supported by active Gemini API)
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_REQUEST_TIMEOUT_MS: int = 30000
    CHROMA_COLLECTION_NAME: str = "harmonic_rag_chunks"
    API_BASE_URL: str = ""
    CORS_ALLOWED_ORIGINS: str = ""

    @field_validator("GEMINI_EMBEDDING_MODEL", mode="before")
    @classmethod
    def replace_retired_embedding_model(cls, value: str) -> str:
        return _normalize_embedding_model(value)

    # Storage Paths (configured values or defaults)
    CHROMA_PERSIST_DIRECTORY: str = str(CANONICAL_DATA_DIR / "chroma")
    DOCUMENT_STORAGE_DIRECTORY: str = str(CANONICAL_DATA_DIR / "documents")
    METADATA_STORAGE_DIRECTORY: str = str(CANONICAL_DATA_DIR / "metadata")
    FRONTEND_DIRECTORY: str = str(PROJECT_ROOT / "frontend")

    # Ingestion Limits
    MAX_UPLOAD_SIZE_MB: int = 25
    CHUNK_SIZE_CHARS: int = 1400
    CHUNK_OVERLAP_CHARS: int = 250

    # RAG Retrieval Hyperparameters
    TOP_K_DENSE: int = 8
    TOP_K_LEXICAL: int = 8
    TOP_K_FINAL: int = 5
    RRF_K: int = 60
    RELEVANCE_THRESHOLD: float = 0.005

    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: str | bool) -> bool:
        """Coerce various environment representations to a boolean.
        Accepts traditional truthy strings ("true", "1", "yes") and treats any
        other non‑empty value (including the legacy "release" flag) as ``False``.
        """
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            lowered = v.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
        # Anything else – including "release" or empty – is considered False
        return False

    @property
    def api_key(self) -> Optional[str]:
        """Prefer GEMINI_API_KEY while retaining legacy GOOGLE_API_KEY support."""
        return (
            self.GEMINI_API_KEY
            or os.getenv("GEMINI_API_KEY")
            or self.GOOGLE_API_KEY
            or os.getenv("GOOGLE_API_KEY")
        )

    @property
    def api_base_url(self) -> str:
        return self.API_BASE_URL.strip().rstrip("/")

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def PROJECT_ROOT(self) -> Path:
        return PROJECT_ROOT

    @property
    def chroma_dir(self) -> Path:
        return _resolve_canonical_dir(self.CHROMA_PERSIST_DIRECTORY, "chroma")

    @property
    def documents_dir(self) -> Path:
        return _resolve_canonical_dir(self.DOCUMENT_STORAGE_DIRECTORY, "documents")

    @property
    def metadata_dir(self) -> Path:
        return _resolve_canonical_dir(self.METADATA_STORAGE_DIRECTORY, "metadata")

    @property
    def frontend_dir(self) -> Path:
        p = Path(self.FRONTEND_DIRECTORY)
        if not p.is_absolute():
            p = (PROJECT_ROOT / "frontend").resolve()
        return p

settings = Settings()
