from fastapi.testclient import TestClient

from app import main


def test_health_head_returns_200_when_healthy(monkeypatch):
    monkeypatch.setattr(main, "get_embedding_model", lambda: object())

    class FakeTable:
        def select(self, *_):
            return self

        def limit(self, *_):
            return self

        def execute(self):
            return None

    monkeypatch.setattr(main, "get_supabase", lambda: SimpleTable(FakeTable()))
    client = TestClient(main.app)
    assert client.head("/health").status_code == 200
    assert client.get("/health").status_code == 200


class SimpleTable:
    def __init__(self, table):
        self._table = table

    def table(self, _name):
        return self._table
