import logging
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiEmbeddingService:
    """
    Embedding service using Google Gen AI Python SDK.
    Uses Gemini retrieval embeddings with dimensions compatible with the persisted index.
    Uses deterministic normalized token hashing only when API credentials are absent.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.api_key
        self.model_name = model_name or settings.GEMINI_EMBEDDING_MODEL
        self.client = None
        self.is_live = False
        self.fallback_reason: Optional[str] = None
        self.initialization_error: Optional[Exception] = None
        self.last_error: Optional[Exception] = None
        self.dimension = 768

        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self.client = genai.Client(
                    api_key=self.api_key.strip(),
                    http_options={"timeout": settings.GEMINI_REQUEST_TIMEOUT_MS}
                )
                logger.info(
                    "Initialized Google Gen AI embedding client for model %s; "
                    "the first real embedding request will verify connectivity.",
                    self.model_name
                )
            except Exception as e:
                self.initialization_error = e
                self.fallback_reason = (
                    "Gemini embedding client could not be initialized; "
                    "local fallback is disabled while credentials are configured."
                )
                logger.warning(self.fallback_reason, exc_info=True)
        else:
            self.fallback_reason = "No API key configured; using local deterministic token hashing."

    @property
    def local_fallback_allowed(self) -> bool:
        return not bool(self.api_key and self.api_key.strip())

    @property
    def is_available(self) -> bool:
        return self.local_fallback_allowed or (
            self.client is not None and self.last_error is None
        )

    @property
    def index_signature(self) -> str:
        if not self.local_fallback_allowed:
            provider = f"google-genai:{self.model_name}"
        else:
            provider = "local-deterministic-hash-md5-v1"
        return f"{provider}:dim{self.dimension}"

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Deterministic, unit-normalized token-hash vector for offline use only.
        """
        words = text.lower().split()
        vec = np.zeros(self.dimension, dtype=np.float32)
        if not words:
            vec[0] = 1.0
            return vec.tolist()

        for word in words:
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h % 2 == 0) else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def _normalize_embedding(self, values: List[float]) -> List[float]:
        vector = np.asarray(values, dtype=np.float32)
        if vector.size != self.dimension:
            raise ValueError(
                f"Expected {self.dimension}-dimensional embedding, received {vector.size} dimensions."
            )
        if not np.isfinite(vector).all():
            raise ValueError("The embedding service returned non-finite values.")
        norm = np.linalg.norm(vector)
        if norm == 0:
            raise ValueError("The embedding service returned a zero vector.")
        return (vector / norm).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of document texts."""
        if not texts:
            return []

        if not self.local_fallback_allowed:
            if self.client is None:
                raise RuntimeError(
                    "Gemini embedding client is unavailable; refusing to use an incompatible local vector."
                ) from self.initialization_error
            try:
                embeddings: List[List[float]] = []
                batch_size = 20
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    response = self.client.models.embed_content(
                        model=self.model_name,
                        contents=batch,
                        config={
                            "output_dimensionality": self.dimension,
                            "task_type": "RETRIEVAL_DOCUMENT"
                        }
                    )
                    if hasattr(response, 'embeddings') and response.embeddings:
                        for emb in response.embeddings:
                            embeddings.append(self._normalize_embedding(list(emb.values)))
                    else:
                        raise ValueError("No embeddings returned by Gemini API")
                if len(embeddings) != len(texts):
                    raise ValueError(
                        f"Gemini returned {len(embeddings)} embeddings for {len(texts)} documents."
                    )
                self.is_live = True
                self.last_error = None
                self.fallback_reason = None
                return embeddings
            except Exception as e:
                self.last_error = e
                self.fallback_reason = (
                    "Gemini document embedding failed; local fallback is disabled "
                    "while credentials are configured."
                )
                logger.exception("Gemini document embedding failed; refusing to mix embedding spaces.")
                raise RuntimeError("Gemini document embedding failed.") from e

        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """Generates embedding for a single search query."""
        if not self.local_fallback_allowed:
            if self.client is None:
                raise RuntimeError(
                    "Gemini embedding client is unavailable; refusing to use an incompatible local vector."
                ) from self.initialization_error
            try:
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=text,
                    config={
                        "output_dimensionality": self.dimension,
                        "task_type": "RETRIEVAL_QUERY"
                    }
                )
                if response and response.embeddings:
                    vector = self._normalize_embedding(list(response.embeddings[0].values))
                    self.is_live = True
                    self.last_error = None
                    self.fallback_reason = None
                    return vector
                raise ValueError("No embedding returned by Gemini API")
            except Exception as e:
                self.last_error = e
                self.fallback_reason = (
                    "Gemini query embedding failed; local fallback is disabled "
                    "while credentials are configured."
                )
                logger.exception("Gemini query embedding failed; refusing to query with an incompatible fallback vector.")
                raise RuntimeError("Gemini query embedding failed.") from e
        return self._fallback_embed(text)

    def get_model_info(self) -> Dict[str, Any]:
        if self.local_fallback_allowed:
            provider = "Local Deterministic Token Hashing (768-dim)"
            mode = "local_deterministic_fallback"
            model_name = f"{self.model_name} (offline)"
        elif self.is_live:
            provider = "Google Gemini (google-genai SDK)"
            mode = "live_gemini"
            model_name = self.model_name
        else:
            is_unavailable = self.client is None or self.last_error is not None
            provider = (
                "Google Gen AI (unavailable)"
                if is_unavailable
                else "Google Gen AI (configured, not yet verified)"
            )
            mode = "unavailable" if is_unavailable else "configured_not_verified"
            model_name = self.model_name
        return {
            "model_name": model_name,
            "dimension": self.dimension,
            "provider": provider,
            "is_live_api": self.is_live,
            "mode": mode,
            "fallback_reason": self.fallback_reason
        }

# Global singleton
embedding_service = GeminiEmbeddingService()
