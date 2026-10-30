import json
import urllib.request
import sys

def test_carnatic_query():
    print("=" * 60)
    print("Testing Query: 'Who is the father of Carnatic music?'")
    print("=" * 60)
    payload = {
        "message": "Who is the father of Carnatic music?",
        "conversation_id": "test-carnatic-session"
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    print("Direct Answer:", data.get("direct_answer"))
    print("\nMusical Example:", data.get("musical_example"))
    print("\nKnowledge Source:", data.get("knowledge_source"))
    print("\nCitations:")
    for idx, c in enumerate(data.get("citations", []), 1):
        print(f"  - [{idx}] {c.get('document_title')} (Page: {c.get('page_number')})")
        print(f"    Passage quote: {c.get('quoted_passage', '')[:120]}...")

    print("\nVisualizer Data:")
    viz = data.get("visualizer")
    if viz:
        print(f"  Type: {viz.get('type')}, Root: {viz.get('root')}, Description: {viz.get('description')}")
        print(f"  Notes: {viz.get('notes')}")
        print(f"  Formula: {viz.get('formula')}")

    trace = data.get("retrieval_trace", {})
    print(f"\nRetrieved Fused Results ({len(trace.get('fused_results', []))} passages):")
    for idx, r in enumerate(trace.get("fused_results", []), 1):
        print(f"  Passage {idx}: '{r.get('document_title')}' (Page: {r.get('page_number')}, Score: {r.get('rrf_score')})")

    # Assertions
    direct_ans = data.get("direct_answer", "").lower()
    assert "purandara" in direct_ans or "dasa" in direct_ans or "pitamaha" in direct_ans, "Did not identify Purandara Dasa!"
    first_doc = trace.get("fused_results", [])[0].get("document_title", "").lower()
    assert "carnatic" in first_doc or "music theory questions" in first_doc, f"Top doc is not Carnatic: {first_doc}"
    print("\n>>> CARNATIC QUERY TEST PASSED SUCCESSFULLY! <<<\n")

if __name__ == "__main__":
    test_carnatic_query()
