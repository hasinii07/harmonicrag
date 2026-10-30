import json
from app.rag.retrieval import HybridRetriever
from app.rag.lexical_search import tokenize_music_theory
from app.rag.generation import answer_generator

def trace(query: str):
    print("=" * 80)
    print(f"QUERY: '{query}'")
    print("=" * 80)
    tokens = tokenize_music_theory(query)
    print(f"Tokens: {tokens}")

    retriever = HybridRetriever()
    fused, tr = retriever.retrieve(query)

    print(f"\nIs evidence sufficient: {tr.is_evidence_sufficient}")
    print("\n--- DENSE RESULTS ---")
    for d in tr.dense_results:
        print(f"Rank {d['rank']}: ID={d['chunk_id']} Doc='{d['document_title']}' Pg={d['page_number']} Score={d['cosine_score']}")
        print(f"  Preview: {d['preview'][:120]}...\n")

    print("\n--- LEXICAL RESULTS ---")
    for l in tr.lexical_results:
        print(f"Rank {l['rank']}: ID={l['chunk_id']} Doc='{l['document_title']}' Pg={l['page_number']} BM25={l['bm25_score']}")
        print(f"  Preview: {l['preview'][:120]}...\n")

    print("\n--- FUSED RESULTS (RRF) ---")
    for f in tr.fused_results:
        print(f"Final Rank {f['final_rank']}: ID={f['chunk_id']} Doc='{f['document_title']}' Pg={f['page_number']} RRF={f['rrf_score']} DenseRank={f['dense_rank']} LexRank={f['lexical_rank']}")
        print(f"  Content snippet: {f['content'][:150]}...\n")

    resp = answer_generator.generate_answer(query, fused, tr, "trace-test")
    print("\n--- GENERATED ANSWER ---")
    print(f"Direct Answer: {resp.direct_answer}")
    print(f"Explanation: {resp.explanation[:300]}...")
    print(f"Knowledge Source: {resp.knowledge_source}")

if __name__ == "__main__":
    trace("What are the 7 chords?")
