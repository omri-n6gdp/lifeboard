from backend.envelope import ok, error, setup, run_provider


def test_ok_envelope_shape():
    e = ok("todos", "To-do", items=[{"text": "x"}], value=None)
    assert e["id"] == "todos" and e["status"] == "ok"
    assert e["items"] == [{"text": "x"}] and e["error"] is None
    assert "updated_at" in e


def test_error_envelope():
    e = error("news", "News", "boom")
    assert e["status"] == "error" and e["error"] == "boom" and e["items"] == []


def test_setup_envelope():
    e = setup("habits", "Habits", "connect Notion")
    assert e["status"] == "setup" and e["hint"] == "connect Notion"


def test_run_provider_catches_exceptions():
    def boom():
        raise ValueError("nope")

    e = run_provider("x", "X", boom)
    assert e["status"] == "error" and "nope" in e["error"]
