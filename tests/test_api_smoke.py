import pytest
from fastapi.testclient import TestClient

from backend import app as appmod
from backend.providers import todos

client = TestClient(appmod.app)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Keep the smoke test offline and off the real ~/.lifeboard store."""
    monkeypatch.setattr(todos, "STORE", tmp_path / "todos.json")
    cfg = {
        "display_name": "Test", "goals": [], "theme": "a",
        "panels": ["today", "feeds"],
        "calendar": {"ical_urls": []},
        "news": {"feeds": [], "max_items": 5},
        "notion": {"token": "", "habits_database_id": "", "parent_page_id": ""},
        "trading": {"jarvis_dir": "/no", "jarvis_api_url": ""},
        "claude": {"projects_dir": str(tmp_path / "noproj")},
    }
    monkeypatch.setattr(appmod, "load_config", lambda: cfg)
    yield


def test_board_returns_panels():
    r = client.get("/api/board")
    assert r.status_code == 200
    body = r.json()
    assert "panels" in body and isinstance(body["panels"], list)
    ids = {p["id"] for p in body["panels"]}
    assert "today_todos" in ids and "feeds_news" in ids


def test_todo_roundtrip():
    r = client.post("/api/todos", json={"text": "smoke item"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["text"] == "smoke item" for i in items)
