from backend.providers import todos


def test_add_toggle_delete(tmp_path, monkeypatch):
    store = tmp_path / "todos.json"
    monkeypatch.setattr(todos, "STORE", store)
    todos.add("buy milk")
    items = todos.provider({})["items"]
    assert items[0]["text"] == "buy milk" and items[0]["done"] is False
    tid = items[0]["id"]
    todos.toggle(tid)
    assert todos.provider({})["items"][0]["done"] is True
    todos.delete(tid)
    assert todos.provider({})["items"] == []
