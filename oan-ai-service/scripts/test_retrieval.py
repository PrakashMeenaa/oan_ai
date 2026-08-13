import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.embeddings import create_embedding
from app.core.supabase import get_supabase


def test_retrieval(query: str) -> None:
    print(f"\nQuery: {query}")
    print("Creating embedding...")
    embedding = create_embedding(query)
    print(f"Embedding dimensions: {len(embedding)}")

    supabase = get_supabase()

    print("\nTesting with threshold 0.5:")
    result = supabase.rpc("match_oan_documents", {
        "query_embedding": embedding,
        "match_threshold": 0.5,
        "match_count": 5,
    }).execute()
    print(f"Results found: {len(result.data)}")

    print("\nTesting with threshold 0.2:")
    result = supabase.rpc("match_oan_documents", {
        "query_embedding": embedding,
        "match_threshold": 0.2,
        "match_count": 5,
    }).execute()
    print(f"Results found: {len(result.data)}")
    for i, chunk in enumerate(result.data):
        print(f"\n--- Chunk {i + 1} (similarity: {chunk['similarity']:.3f}) ---")
        print(chunk["content"][:200])

    print("\nTesting with threshold 0.0 (all results):")
    result = supabase.rpc("match_oan_documents", {
        "query_embedding": embedding,
        "match_threshold": 0.0,
        "match_count": 3,
    }).execute()
    print(f"Total results at 0.0 threshold: {len(result.data)}")
    if result.data:
        print(f"Best similarity score: {result.data[0]['similarity']:.3f}")
        print(f"Worst similarity score: {result.data[-1]['similarity']:.3f}")


if __name__ == "__main__":
    test_retrieval("defoamer products phosphoric acid")