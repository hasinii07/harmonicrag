import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.models.schemas import ChatRequest, ChatResponse
from app.rag.generation import GeminiGenerationUnavailableError
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

@router.post("", response_model=ChatResponse)
def post_chat_message(request: ChatRequest) -> ChatResponse:
    """
    Processes a user query through the HarmonicRAG pipeline:
    1. Hybrid retrieval (ChromaDB dense + BM25 lexical)
    2. Reciprocal Rank Fusion
    3. Grounded answer generation
    4. Citation validation against retrieved chunk IDs
    5. Piano visualizer parameter extraction
    """
    try:
        return chat_service.process_message(request)
    except GeminiGenerationUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Failed to process chat query")
        raise HTTPException(status_code=500, detail="Failed to process query.")

@router.get("/conversations", response_model=List[Dict[str, Any]])
def get_conversations():
    """Lists saved conversation sessions."""
    return chat_service.list_conversations()

@router.get("/conversations/{conversation_id}", response_model=List[Dict[str, Any]])
def get_conversation_history(conversation_id: str):
    """Retrieves full message turn history for a conversation."""
    history = chat_service.get_conversation_history(conversation_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return history

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Deletes a conversation history session."""
    deleted = chat_service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "success", "message": f"Deleted conversation {conversation_id}"}
