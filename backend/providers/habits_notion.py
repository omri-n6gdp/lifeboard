"""Habits panel, backed by Notion (the source of truth, editable from phone too).

Pure logic (rows_to_items, next_streak) is unit-tested without network; the HTTP
calls are thin wrappers over Notion's REST API. On first run, if no habits
database is configured, one is created under the shared parent page."""
import datetime
import json

import httpx

from backend import config as _config
from backend.envelope import ok, setup, run_provider

ID, TITLE = "today_habits", "Habits"
API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


# ---------- pure logic (tested offline) ----------
def _title(prop):
    arr = (prop or {}).get("title") or []
    return arr[0]["plain_text"] if arr else "(unnamed)"


def rows_to_items(rows, today=None):
    today = today or datetime.date.today()
    out = []
    for r in rows:
        p = r.get("properties", {})
        last = ((p.get("Last done") or {}).get("date") or {})
        last_start = last.get("start")
        done_flag = (p.get("Done today") or {}).get("checkbox", False)
        done_today = bool(done_flag and last_start == today.isoformat())
        out.append({
            "page_id": r.get("id"),
            "name": _title(p.get("Name")),
            "streak": (p.get("Streak") or {}).get("number") or 0,
            "done_today": done_today,
            "last_done": last_start,
        })
    return out


def next_streak(last_start, current, today=None):
    today = today or datetime.date.today()
    if last_start == today.isoformat():
        return current or 0
    if last_start == (today - datetime.timedelta(days=1)).isoformat():
        return (current or 0) + 1
    return 1


# ---------- Notion HTTP (thin wrappers) ----------
def _headers(token):
    return {"Authorization": f"Bearer {token}", "Notion-Version": VERSION,
            "Content-Type": "application/json"}


def _query(token, db_id):
    r = httpx.post(f"{API}/databases/{db_id}/query", headers=_headers(token), json={}, timeout=10)
    r.raise_for_status()
    return r.json().get("results", [])


def _get_page(token, page_id):
    r = httpx.get(f"{API}/pages/{page_id}", headers=_headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def ensure_database(cfg):
    """Create the habits database under the shared parent page; return its id.
    Persists the new id back into the settings file so it's reused next time."""
    n = cfg["notion"]
    token, parent = n.get("token"), n.get("parent_page_id")
    body = {
        "parent": {"type": "page_id", "page_id": parent},
        "title": [{"type": "text", "text": {"content": "Lifeboard Habits"}}],
        "properties": {
            "Name": {"title": {}},
            "Done today": {"checkbox": {}},
            "Last done": {"date": {}},
            "Streak": {"number": {}},
        },
    }
    r = httpx.post(f"{API}/databases", headers=_headers(token), json=body, timeout=15)
    r.raise_for_status()
    db_id = r.json()["id"]
    _persist_db_id(db_id)
    return db_id


def _persist_db_id(db_id):
    path = _config.CONFIG_PATH
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:
            data = {}
    data.setdefault("notion", {})["habits_database_id"] = db_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def tick(cfg, page_id):
    token = cfg["notion"]["token"]
    page = _get_page(token, page_id)
    props = page.get("properties", {})
    last = ((props.get("Last done") or {}).get("date") or {}).get("start")
    streak = (props.get("Streak") or {}).get("number") or 0
    today = datetime.date.today()
    body = {"properties": {
        "Done today": {"checkbox": True},
        "Last done": {"date": {"start": today.isoformat()}},
        "Streak": {"number": next_streak(last, streak, today)},
    }}
    r = httpx.patch(f"{API}/pages/{page_id}", headers=_headers(token), json=body, timeout=10)
    r.raise_for_status()
    return r.json()


def provider(cfg):
    n = cfg.get("notion") or {}
    token = n.get("token")
    db_id = n.get("habits_database_id")
    parent = n.get("parent_page_id")
    if not token:
        return setup(ID, TITLE, "Add your Notion integration token in settings to track habits.")
    if not db_id and not parent:
        return setup(ID, TITLE, "Notion connected — share a page and add its id as notion.parent_page_id so Lifeboard can create your habits database.")

    def _do():
        nonlocal db_id
        if not db_id:
            db_id = ensure_database(cfg)
        return ok(ID, TITLE, items=rows_to_items(_query(token, db_id)))

    return run_provider(ID, TITLE, _do)
