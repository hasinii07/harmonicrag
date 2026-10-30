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
    Provides graceful fallback to deterministic normalized semantic hashing
    when API credentials are not yet configured or in offline test environments.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.api_key
        self.model_name = model_name or settings.GEMINI_EMBEDDING_MODEL
        self.client = None
        self.is_live = False
        self.fallback_reason: Optional[str] = None
        self.dimension = 768

        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self.client = genai.Client(
                    api_key=self.api_key.strip(),
                    http_options={"timeout": settings.GEMINI_REQUEST_TIMEOUT_MS}
                )
                test_resp = self.client.models.embed_content(
                    model=self.model_name,
                    contents="music theory probe",
                    config={
                        "output_dimensionality": self.dimension,
                        "task_type": "RETRIEVAL_QUERY"
                    }
                )
                if test_resp and test_resp.embeddings:
                    dim = len(test_resp.embeddings[0].values)
                    if dim == self.dimension:
                        self.is_live = True
                        logger.info(f"Initialized Google Gen AI embedding client with model: {self.model_name} (dim: {dim})")
                    else:
                        self.is_live = False
                        self.fallback_reason = (
                            f"Model dimension mismatch (got {dim}, existing Chroma index requires {self.dimension}). "
                            "Using local deterministic 768-dim embeddings for consistency."
                        )
                        logger.warning(self.fallback_reason)
                else:
                    self.is_live = False
                    self.fallback_reason = f"Embedding model '{self.model_name}' returned empty response."
                    logger.warning(self.fallback_reason)
            except Exception as e:
                self.is_live = False
                self.fallback_reason = f"Gemini embedding model '{self.model_name}' unavailable ({e}). Using local deterministic fallback."
                logger.warning(f"Embedding API probe failed: {self.fallback_reason}")
        else:
            self.fallback_reason = "No API key configured."

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Deterministic, unit-normalized 768-dim semantic hash embedding.
        Preserves consistent cosine similarity for local testing and offline execution.
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
        norm = np.linalg.norm(vector)
        if norm == 0:
            raise ValueError("The embedding service returned a zero vector.")
        return (vector / norm).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of document texts."""
        if not texts:
            return []

        if self.is_live and self.client:
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
                return embeddings
            except Exception as e:
                logger.error(f"Gemini embedding API call failed: {e}. Falling back to deterministic embeddings.")

        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """Generates embedding for a single search query."""
        if self.is_live and self.client:
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
                    return self._normalize_embedding(list(response.embeddings[0].values))
                raise ValueError("No embedding returned by Gemini API")
            except Exception as e:
                logger.warning(f"Live query embed failed: {e}. Using deterministic fallback.")
        return self._fallback_embed(text)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name if self.is_live else f"{self.model_name} (offline/unsupported)",
            "dimension": self.dimension,
            "provider": "Google Gemini (google-genai SDK)" if self.is_live else "Local Deterministic Semantic Hashing (768-dim)",
            "is_live_api": self.is_live,
            "mode": "live_gemini" if self.is_live else "local_deterministic_fallback",
            "fallback_reason": self.fallback_reason
        }

# Global singleton
embedding_service = GeminiEmbeddingService()
