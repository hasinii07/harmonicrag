import json
import uuid
import urllib.request
import urllib.error
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_workflow_test():
    print("=" * 70)
    print("TESTING COMPLETE WORKFLOW: UPLOAD -> INDEX -> QUERY -> CITATION")
    print("=" * 70)

    # Step 1: Query initial health
    req = urllib.request.Request(f"{BASE_URL}/api/health")
    with urllib.request.urlopen(req) as resp:
        health_before = json.loads(resp.read().decode("utf-8"))
    
    initial_chroma_chunks = health_before["vector_store"]["indexed_chunks_count"]
    initial_bm25_chunks = health_before["lexical_index"]["indexed_chunks_count"]
    initial_docs = health_before["documents"]["total_documents"]
    print(f"Initial State: {initial_docs} docs, {initial_chroma_chunks} vector chunks, {initial_bm25_chunks} BM25 chunks.")

    session_key = str(uuid.uuid4())[:6]
    doc_title = f"Modal Interchange and Borrowed Chords ({session_key})"
    doc_payload = {
        "title": doc_title,
        "author": "Harmonic Research Guild",
        "category": "Harmony Study Guide",
        "content": (
            f"Document Key: {session_key}. "
            "Modal interchange (also called mode mixture) is a harmonic technique where chords "
            "from a parallel mode (typically the parallel minor) are borrowed and used within the primary "
            "mode (typically the major key). The most common borrowed chord in major keys is the minor "
            "subdominant triad (iv) and minor subdominant seventh chord (iv7), such as F minor (F-Ab-C) "
            "in C major, which introduces the distinctive flat-sixth scale degree (Le, Ab) resolving downward "
            "to scale degree 5 (Sol, G). Another ubiquitous borrowed chord is the flat-submediant major chord "
            "(bVI, Ab-C-Eb in C major) and the flat-seventh major triad (bVII, Bb-D-F in C major), commonly "
            "termed the subtonic chord. These borrowed chords add emotional darkness and harmonic color without "
            "modulating away from the tonic center."
        )
    }

    print(f"\n1. Ingesting new document: '{doc_title}'...")
    req = urllib.request.Request(
        f"{BASE_URL}/api/documents/text",
        data=json.dumps(doc_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        ingest_res = json.loads(resp.read().decode("utf-8"))

    doc_id = ingest_res.get("id")
    chunks_created = ingest_res.get("chunk_count")
    print(f"   Success! Document ID: {doc_id}, Chunks indexed: {chunks_created}")
    assert chunks_created is not None and chunks_created > 0, f"No chunks were indexed! Result: {ingest_res}"

    # Step 3: Verify index counts increased
    req = urllib.request.Request(f"{BASE_URL}/api/health")
    with urllib.request.urlopen(req) as resp:
        health_after = json.loads(resp.read().decode("utf-8"))

    after_chroma_chunks = health_after["vector_store"]["indexed_chunks_count"]
    after_bm25_chunks = health_after["lexical_index"]["indexed_chunks_count"]
    after_docs = health_after["documents"]["total_documents"]
    print(f"\n2. Verifying Index Expansion:")
    print(f"   Documents: {initial_docs} -> {after_docs}")
    print(f"   Vector Chunks: {initial_chroma_chunks} -> {after_chroma_chunks}")
    print(f"   BM25 Chunks: {initial_bm25_chunks} -> {after_bm25_chunks}")
    assert after_chroma_chunks == initial_chroma_chunks + chunks_created, "ChromaDB count did not increase by chunks_created!"
    assert after_bm25_chunks == initial_bm25_chunks + chunks_created, "BM25 count did not increase by chunks_created!"
    assert after_docs == initial_docs + 1, "Document registry count did not increment!"

    # Step 4: Ask a question answered specifically in the uploaded document
    query_payload = {
        "message": "What is the most common borrowed chord in major keys during modal interchange?",
        "conversation_id": "test-workflow-session"
    }
    print("\n3. Asking Chatbot Question:")
    print(f"   Query: '{query_payload['message']}'")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=json.dumps(query_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        chat_res = json.loads(resp.read().decode("utf-8"))

    print("\n4. Response Verification:")
    print(f"   Direct Answer: {chat_res.get('direct_answer')}")
    print(f"   Knowledge Source: {chat_res.get('knowledge_source')}")
    print(f"   Musical Example: {chat_res.get('musical_example')}")

    citations = chat_res.get("citations", [])
    print(f"\n5. Inspecting Citations ({len(citations)} citations returned):")
    for idx, c in enumerate(citations, 1):
        print(f"   Citation {idx}:")
        print(f"     Document Title: {c.get('document_title')}")
        print(f"     Document ID:    {c.get('document_id')}")
        print(f"     Chunk ID:       {c.get('chunk_id')}")
        print(f"     Quoted Passage: {c.get('quoted_passage')[:100]}...")
        print(f"     Is Verified:    {c.get('is_verified')}")

    trace = chat_res.get("retrieval_trace", {})
    fused_results = trace.get("fused_results", [])
    print(f"\n6. Inspecting Retrieved Passages ({len(fused_results)} retrieved):")
    for idx, p in enumerate(fused_results, 1):
        print(f"   Passage {idx}: '{p.get('document_title')}' (RRF Score: {p.get('rrf_score')})")

    # Assertions
    top_doc = fused_results[0].get("document_title")
    assert "Modal Interchange" in top_doc, f"Expected uploaded doc as top passage, but got: {top_doc}"
    assert len(citations) > 0, "No citations returned!"
    citation_titles = [c.get("document_title") for c in citations]
    assert any("Modal Interchange" in t for t in citation_titles), f"Uploaded doc not in citations: {citation_titles}"

    print("\n" + "=" * 70)
    print(">>> WORKFLOW TEST COMPLETED SUCCESSFULLY! ALL ASSERTIONS PASSED! <<<")
    print("=" * 70)

if __name__ == "__main__":
    run_workflow_test()
