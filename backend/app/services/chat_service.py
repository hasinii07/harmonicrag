import uuid
import logging
from typing import Dict, List, Optional, Any
from app.models.schemas import ChatRequest, ChatResponse
from app.rag.retrieval import hybrid_retriever
from app.rag.generation import answer_generator

logger = logging.getLogger(__name__)

class ChatService:
    """
    Coordinates chat conversations, orchestrates hybrid retrieval,
    answer generation, and stores conversation history.
    """

    def __init__(self):
        # In-memory conversation store: conversation_id -> list of turn dicts
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}

    def process_message(self, request: ChatRequest) -> ChatResponse:
        conv_id = request.conversation_id or str(uuid.uuid4())[:8]
        if conv_id not in self.conversations:
            self.conversations[conv_id] = []

        query = request.message.strip()
        if not query:
            raise ValueError("Query cannot be empty.")

        # 1. Retrieve hybrid results and trace
        fused_results, trace = hybrid_retriever.retrieve(
            query=query,
            top_k=request.top_k
        )

        # 2. Generate grounded answer and validate citations
        response = answer_generator.generate_answer(
            query=query,
            retrieved_results=fused_results,
            trace=trace,
            conversation_id=conv_id
        )

        # 3. Store conversation turn
        self.conversations[conv_id].append({
            "role": "user",
            "content": query
        })
        self.conversations[conv_id].append({
            "role": "assistant",
            "response": response.model_dump()
        })

        return response

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        return self.conversations.get(conversation_id, [])

    def list_conversations(self) -> List[Dict[str, Any]]:
        summaries = []
        for cid, turns in self.conversations.items():
            first_user_msg = next((t["content"] for t in turns if t["role"] == "user"), "New Conversation")
            summaries.append({
                "conversation_id": cid,
                "title": first_user_msg[:45] + ("..." if len(first_user_msg) > 45 else ""),
                "message_count": len(turns)
            })
        return summaries

    def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

# Global singleton
chat_service = ChatService()
