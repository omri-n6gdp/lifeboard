"""To-do panel: a tiny local JSON store you type into. Writes are atomic so a
crash mid-save can't corrupt the file. (Could move to Notion later, like habits.)"""
import json
import os
import pathlib
import tempfile
import uuid

from backend.envelope import ok, run_provider

ID, TITLE = "today_todos", "To-do"
STORE = pathlib.Path(os.path.expanduser("~/.lifeboard/todos.json"))


def _load():
    if STORE.exists():
        try:
            return json.loads(STORE.read_text())
        except Exception:
            return []
    return []


def _save(items):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(STORE.parent))
    with os.fdopen(fd, "w") as f:
        json.dump(items, f)
    os.replace(tmp, STORE)  # atomic


def add(text):
    items = _load()
    items.append({"id": uuid.uuid4().hex[:8], "text": text, "done": False})
    _save(items)
    return items


def toggle(tid):
    items = _load()
    for it in items:
        if it["id"] == tid:
            it["done"] = not it["done"]
    _save(items)
    return items


def delete(tid):
    items = [i for i in _load() if i["id"] != tid]
    _save(items)
    return items


def provider(cfg):
    return run_provider(ID, TITLE, lambda: ok(ID, TITLE, items=_load()))
