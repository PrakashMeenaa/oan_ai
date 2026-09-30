from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services import retrieval


class FakeSupabase:
    def __init__(self, text_rows, vector_rows):
        self.text_rows, self.vector_rows = text_rows, vector_rows
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        rows = self.text_rows if name == "search_oan_content" else self.vector_rows
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=rows))


def chunk(chunk_id):
    return {"id": chunk_id, "content": f"c{chunk_id}", "metadata": {"document_type": "product_catalog"}}


@pytest.fixture
def setup(monkeypatch):
    def make(text_rows, vector_rows):
        fake = FakeSupabase(text_rows, vector_rows)
        monkeypatch.setattr(retrieval, "get_supabase", lambda: fake)
        monkeypatch.setattr(retrieval, "create_embedding", lambda q: [0.0])
        monkeypatch.setattr(retrieval, "get_settings", lambda: SimpleNamespace(retrieval_min_similarity=0.0))
        return fake
    return make


def ids(chunks):
    return [c["id"] for c in chunks]


def test_family_merge_keyword_first_and_deduped(setup):
    setup([chunk(1), chunk(2)], [chunk(2), chunk(3)])
    result = retrieval.retrieve_relevant_chunks("What defoamers do you have?")
    assert ids(result) == [1, 2, 3]


def test_family_merge_capped_at_8(setup):
    setup([chunk(i) for i in range(1, 7)], [chunk(i) for i in range(7, 15)])
    result = retrieval.retrieve_relevant_chunks("show me defoamer grades")
    assert ids(result) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_plural_and_multiword_terms_match():
    assert retrieval.get_family_terms("What defoamers do you have?") == ["defoamer"]
    assert retrieval.get_family_terms("any Plasticizers or stearates") == ["plasticizer", "stearate"]
    assert retrieval.get_family_terms("scale inhibitors please") == ["scale inhibitor"]
    assert retrieval.get_family_terms("what is your return policy") == []


def test_threshold_default_is_zero_and_passed_to_vector_search(setup):
    assert Settings.model_fields["retrieval_min_similarity"].default == 0.0
    fake = setup([], [chunk(1)])
    retrieval.retrieve_relevant_chunks("tell me about your company")
    vector_calls = [p for n, p in fake.calls if n == "match_oan_documents"]
    assert vector_calls and all(p["match_threshold"] == 0.0 for p in vector_calls)


def test_product_code_path_returns_keyword_results_only(setup):
    fake = setup([chunk(1)], [chunk(9)])
    result = retrieval.retrieve_relevant_chunks("defoamer OAN D 25 details")
    assert ids(result) == [1]
    assert all(n == "search_oan_content" for n, _ in fake.calls)
