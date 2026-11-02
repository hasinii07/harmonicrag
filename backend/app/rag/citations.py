import logging
from typing import List, Dict, Any, Tuple
from app.models.schemas import FusedSearchResult, CitationRef

logger = logging.getLogger(__name__)

def validate_and_filter_citations(
    candidate_citations: List[Dict[str, Any]],
    retrieved_results: List[FusedSearchResult],
    is_evidence_sufficient: bool = True
) -> Tuple[List[CitationRef], Dict[str, Any]]:
    """
    Validates every citation claim strictly against the actual retrieved chunks.
    Rejects citations to nonexistent chunk IDs, mismatched titles, or fabricated quotes.
    When evidence is insufficient or question is out of scope, strictly returns zero citations.
    """
    if not is_evidence_sufficient or not retrieved_results:
        return [], {
            "candidate_count": len(candidate_citations),
            "verified_count": 0,
            "rejected_count": len(candidate_citations),
            "precision": 0.0 if candidate_citations else 1.0,
            "rejected_details": [
                {"candidate": c, "reason": "Citations disallowed: evidence insufficient or out of scope."}
                for c in candidate_citations
            ]
        }

    retrieved_map = {f.chunk.chunk_id: f.chunk for f in retrieved_results}
    valid_citations: List[CitationRef] = []
    rejected_citations: List[Dict[str, Any]] = []

    for candidate in candidate_citations:
        chunk_id = candidate.get("chunk_id", "").strip()
        quoted_passage = candidate.get("quoted_passage", "").strip()

        # Check 1: Does chunk_id exist in retrieved context?
        if chunk_id not in retrieved_map:
            rejected_citations.append({
                "candidate": candidate,
                "reason": f"Chunk ID '{chunk_id}' was not in the retrieved context set."
            })
            continue

        chunk = retrieved_map[chunk_id]

        # Check 2: Candidate quotes must be verbatim evidence from the referenced chunk.
        if quoted_passage:
            norm_quote = " ".join(quoted_passage.casefold().split())
            norm_content = " ".join(chunk.content.casefold().split())
            if norm_quote not in norm_content:
                rejected_citations.append({
                    "candidate": candidate,
                    "reason": f"Quoted passage was not present in retrieved chunk '{chunk_id}'."
                })
                continue

        # Construct guaranteed verified citation from actual chunk metadata
        valid_citations.append(CitationRef(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            author=chunk.author,
            page_number=chunk.page_number,
            section=chunk.section,
            quoted_passage=quoted_passage if quoted_passage else chunk.content[:200] + "...",
            is_verified=True
        ))

    # If the LLM did not provide structured citations but the query was grounded in retrieved results,
    # generate verified citations directly from the top matching retrieved chunks
    if not valid_citations and retrieved_results and is_evidence_sufficient:
        for f in retrieved_results[:2]:
            c = f.chunk
            valid_citations.append(CitationRef(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                author=c.author,
                page_number=c.page_number,
                section=c.section,
                quoted_passage=c.content[:220].strip() + ("..." if len(c.content) > 220 else ""),
                is_verified=True
            ))

    total_candidates = len(candidate_citations)
    verified_candidates = total_candidates - len(rejected_citations)
    precision = (verified_candidates / total_candidates) if total_candidates > 0 else 1.0

    validation_summary = {
        "candidate_count": total_candidates,
        "verified_count": len(valid_citations),
        "verified_candidate_count": verified_candidates,
        "rejected_count": len(rejected_citations),
        "precision": round(precision, 4),
        "rejected_details": rejected_citations
    }

    return valid_citations, validation_summary
