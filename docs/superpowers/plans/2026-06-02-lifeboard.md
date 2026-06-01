# Lifeboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, single-user "living" life dashboard that starts with three panels (Today/planner, Trading & money, Feeds) and is structured so new life-area panels snap in with one provider + one card + one settings line.

**Architecture:** A small Python (FastAPI + uvicorn) engine serves a static board and a `/api` surface. One **provider** module per panel returns a common data envelope; the engine fetches live data server-side (calendar iCal, news RSS, Notion habits), reads on-disk data (jarvis trading, `~/.claude/projects`), and reads/writes a local to-do store. All personal values come from `~/.lifeboard/config.json`. Two-plus distinct frontends share one data layer (`lifeboard-core.js`).

**Tech Stack:** Python 3.13 (miniconda) in a project `.venv` (`--system-site-packages` so `httpx`/`pandas` are reused); FastAPI + uvicorn; `icalendar` + `recurring-ical-events` (calendar); `feedparser` (RSS); `httpx` (HTTP incl. Notion REST); vanilla HTML/CSS/JS frontends; pytest.

---

## File Structure

```
~/code/lifeboard/
  run.sh                         # one-line launcher (uses .venv)
  requirements.txt
  README.md                      # non-technical setup + run + calendar/Notion steps
  backend/
    __init__.py
    app.py                       # FastAPI app: wires /api endpoints + serves static
    config.py                    # load ~/.lifeboard/config.json (+ defaults)
    envelope.py                  # Panel envelope helper (uniform shape + error wrap)
    data/
      lifeboard.config.example.json
    providers/
      __init__.py
      calendar_ical.py           # fetch + parse iCal -> today/upcoming events
      news_rss.py                # fetch + merge RSS feeds -> headlines
      trading_jarvis.py          # read jarvis snapshot -> value/day-change/movers
      claude_projects.py         # read ~/.claude/projects -> recent activity
      todos.py                   # local JSON store: list/add/toggle/delete
      habits_notion.py           # Notion REST: list habits, today check-offs, tick
  frontend/
    index.html                   # launcher: links to each design
    shared/
      lifeboard-core.js          # data layer: fetch /api, state, tiny chart helper
      panels.js                  # generic panel/card renderers from the envelope
    a/ index.html style.css app.js   # Design A: Calm & personal
    b/ index.html style.css app.js   # Design B: Mission control
    c/ index.html style.css app.js   # Design C: Editorial   (built if budget allows)
  tests/
    conftest.py
    fixtures/                    # sample.ics, sample_rss.xml, fake jarvis files
    test_config.py
    test_envelope.py
    test_calendar_ical.py
    test_news_rss.py
    test_trading_jarvis.py
    test_claude_projects.py
    test_todos.py
    test_habits_notion.py
    test_api_smoke.py
```

**Data contract — the panel envelope** (every provider returns this shape):
```json
{
  "id": "todos",
  "title": "To-do",
  "status": "ok",            // "ok" | "error" | "setup"
  "updated_at": "2026-06-02T10:00:00Z",
  "value": null,              // optional headline (e.g. trading value)
  "items": [],                // list of small dicts the card renders
  "error": null,              // human message when status == "error"
  "hint": null                // setup guidance when status == "setup"
}
```

---

## Task 0: Project scaffolding + venv

**Files:** Create `requirements.txt`, `run.sh`, `backend/__init__.py`, `backend/providers/__init__.py`, `tests/conftest.py`, `.gitignore`.

- [ ] **Step 1: Write `.gitignore`**
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: Write `requirements.txt`**
```
fastapi
uvicorn[standard]
icalendar
recurring-ical-events
feedparser
httpx
pytest
```

- [ ] **Step 3: Create venv reusing system packages + install**
Run:
```bash
cd ~/code/lifeboard
/opt/miniconda3/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python -c "import fastapi, uvicorn, icalendar, recurring_ical_events, feedparser, httpx; print('deps ok')"
```
Expected: `deps ok`

- [ ] **Step 4: Write `run.sh`** (chmod +x)
```bash
#!/usr/bin/env bash
cd "$(dirname "$0")"
PORT="${1:-8787}"
exec .venv/bin/python -m uvicorn backend.app:app --port "$PORT"
```

- [ ] **Step 5: Write `backend/__init__.py` and `backend/providers/__init__.py`** (empty files).

- [ ] **Step 6: Write `tests/conftest.py`** so `backend` imports resolve:
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
```

- [ ] **Step 7: Commit**
```bash
git add -A && git commit -m "chore: scaffold lifeboard project + venv"
```

---

## Task 1: Panel envelope

**Files:** Create `backend/envelope.py`, `tests/test_envelope.py`.

- [ ] **Step 1: Write failing test** (`tests/test_envelope.py`)
```python
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
```

- [ ] **Step 2: Run, expect fail** — `.venv/bin/python -m pytest tests/test_envelope.py -q` → FAIL (module missing).

- [ ] **Step 3: Implement `backend/envelope.py`**
```python
from datetime import datetime, timezone

def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def _base(id, title, status):
    return {"id": id, "title": title, "status": status, "updated_at": _now(),
            "value": None, "items": [], "error": None, "hint": None}

def ok(id, title, items=None, value=None):
    e = _base(id, title, "ok"); e["items"] = items or []; e["value"] = value; return e

def error(id, title, message):
    e = _base(id, title, "error"); e["error"] = str(message); return e

def setup(id, title, hint):
    e = _base(id, title, "setup"); e["hint"] = hint; return e

def run_provider(id, title, fn):
    """Call a provider that returns a full envelope; wrap any exception as error."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - panels must never crash the board
        return error(id, title, exc)
```

- [ ] **Step 4: Run, expect pass.** Commit: `git add -A && git commit -m "feat: panel envelope"`

---

## Task 2: Config loader

**Files:** Create `backend/config.py`, `backend/data/lifeboard.config.example.json`, `tests/test_config.py`.

- [ ] **Step 1: Write `backend/data/lifeboard.config.example.json`**
```json
{
  "display_name": "Your name",
  "goals": [],
  "calendar": { "ical_urls": [] },
  "news": { "feeds": [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://hnrss.org/frontpage"
  ], "max_items": 12 },
  "notion": { "token": "", "habits_database_id": "", "parent_page_id": "" },
  "trading": { "jarvis_dir": "~/.jarvis", "jarvis_api_url": "" },
  "claude": { "projects_dir": "~/.claude/projects" },
  "panels": ["today", "trading", "feeds"],
  "theme": "a"
}
```

- [ ] **Step 2: Write failing test** (`tests/test_config.py`)
```python
import json, pathlib
from backend.config import load_config, CONFIG_PATH, DEFAULTS

def test_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.config.CONFIG_PATH", tmp_path / "nope.json")
    cfg = load_config()
    assert cfg["panels"] == ["today", "trading", "feeds"]
    assert cfg["news"]["feeds"]  # defaults present

def test_user_values_override_and_merge(tmp_path, monkeypatch):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"display_name": "Omri", "news": {"max_items": 3}}))
    monkeypatch.setattr("backend.config.CONFIG_PATH", p)
    cfg = load_config()
    assert cfg["display_name"] == "Omri"
    assert cfg["news"]["max_items"] == 3
    assert cfg["news"]["feeds"]  # still merged from defaults
```

- [ ] **Step 3: Run, expect fail.**

- [ ] **Step 4: Implement `backend/config.py`**
```python
import json, os, pathlib, copy

CONFIG_PATH = pathlib.Path(os.path.expanduser("~/.lifeboard/config.json"))
_EXAMPLE = pathlib.Path(__file__).parent / "data" / "lifeboard.config.example.json"
DEFAULTS = json.loads(_EXAMPLE.read_text())

def _deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def load_config():
    user = {}
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text())
        except Exception:
            user = {}
    cfg = _deep_merge(DEFAULTS, user)
    for key in ("jarvis_dir",):
        if cfg["trading"].get(key):
            cfg["trading"][key] = os.path.expanduser(cfg["trading"][key])
    cfg["claude"]["projects_dir"] = os.path.expanduser(cfg["claude"]["projects_dir"])
    return cfg
```

- [ ] **Step 5: Run, expect pass.** Commit: `git add -A && git commit -m "feat: config loader + example template"`

---

## Task 3: Calendar provider (iCal)

**Files:** Create `backend/providers/calendar_ical.py`, `tests/fixtures/sample.ics`, `tests/test_calendar_ical.py`.

- [ ] **Step 1: Write `tests/fixtures/sample.ics`** — a minimal VCALENDAR with one timed event dated far in the future so the "today" filter is deterministic in tests by passing an explicit `today`:
```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:1@test
DTSTAMP:20260101T000000Z
DTSTART:20260602T090000Z
DTEND:20260602T100000Z
SUMMARY:Lecture: Quantum
LOCATION:Room 4
END:VEVENT
END:VCALENDAR
```

- [ ] **Step 2: Write failing test** (`tests/test_calendar_ical.py`)
```python
import datetime, pathlib
from backend.providers import calendar_ical as cal

ICS = (pathlib.Path(__file__).parent / "fixtures" / "sample.ics").read_text()

def test_parse_events_for_day():
    day = datetime.date(2026, 6, 2)
    events = cal.events_from_ics(ICS, day=day, horizon_days=1)
    assert any(e["title"] == "Lecture: Quantum" for e in events)
    e = events[0]
    assert e["location"] == "Room 4" and "start" in e

def test_provider_setup_state_when_no_urls(monkeypatch):
    env = cal.provider({"calendar": {"ical_urls": []}})
    assert env["status"] == "setup" and env["id"] == "today_calendar"
```

- [ ] **Step 3: Run, expect fail.**

- [ ] **Step 4: Implement `backend/providers/calendar_ical.py`**
```python
import datetime
import httpx
import icalendar
import recurring_ical_events
from backend.envelope import ok, setup, run_provider

ID, TITLE = "today_calendar", "Calendar"

def events_from_ics(text, day=None, horizon_days=1):
    day = day or datetime.date.today()
    cal = icalendar.Calendar.from_ical(text)
    start = datetime.datetime.combine(day, datetime.time.min)
    end = start + datetime.timedelta(days=horizon_days)
    out = []
    for comp in recurring_ical_events.of(cal).between(start, end):
        s = comp.get("DTSTART").dt
        title = str(comp.get("SUMMARY", "(no title)"))
        loc = str(comp.get("LOCATION", "")) or None
        out.append({
            "title": title,
            "location": loc,
            "start": s.isoformat() if hasattr(s, "isoformat") else str(s),
            "all_day": not isinstance(s, datetime.datetime),
        })
    out.sort(key=lambda e: e["start"])
    return out

def provider(cfg):
    urls = (cfg.get("calendar") or {}).get("ical_urls") or []
    if not urls:
        return setup(ID, TITLE, "Add your Google Calendar secret iCal link in settings.")
    def _do():
        events = []
        for url in urls:
            r = httpx.get(url, timeout=10, follow_redirects=True)
            r.raise_for_status()
            events += events_from_ics(r.text, horizon_days=1)
        events.sort(key=lambda e: e["start"])
        return ok(ID, TITLE, items=events)
    return run_provider(ID, TITLE, _do)
```

- [ ] **Step 5: Run, expect pass.** Commit.

---

## Task 4: News provider (RSS)

**Files:** Create `backend/providers/news_rss.py`, `tests/fixtures/sample_rss.xml`, `tests/test_news_rss.py`.

- [ ] **Step 1: Write `tests/fixtures/sample_rss.xml`**
```xml
<?xml version="1.0"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Headline One</title><link>http://x/1</link><pubDate>Mon, 02 Jun 2026 08:00:00 GMT</pubDate></item>
<item><title>Headline Two</title><link>http://x/2</link><pubDate>Mon, 02 Jun 2026 09:00:00 GMT</pubDate></item>
</channel></rss>
```

- [ ] **Step 2: Write failing test** (`tests/test_news_rss.py`)
```python
import pathlib
from backend.providers import news_rss as news

XML = (pathlib.Path(__file__).parent / "fixtures" / "sample_rss.xml").read_text()

def test_parse_items_newest_first():
    items = news.items_from_feed_text(XML, source="Test")
    assert items[0]["title"] == "Headline Two"  # newer pubDate first
    assert items[0]["source"] == "Test" and items[0]["link"] == "http://x/2"

def test_cap():
    items = news.merge_and_cap([{"title":"a","ts":1},{"title":"b","ts":2},{"title":"c","ts":3}], max_items=2)
    assert len(items) == 2 and items[0]["title"] == "c"
```

- [ ] **Step 3: Run, expect fail.**

- [ ] **Step 4: Implement `backend/providers/news_rss.py`**
```python
import time
import feedparser
import httpx
from backend.envelope import ok, run_provider

ID, TITLE = "feeds_news", "News"

def _ts(entry):
    for k in ("published_parsed", "updated_parsed"):
        if entry.get(k):
            return time.mktime(entry[k])
    return 0.0

def items_from_feed_text(text, source=""):
    parsed = feedparser.parse(text)
    src = source or (parsed.feed.get("title", "") if parsed.feed else "")
    items = [{
        "title": e.get("title", "(untitled)"),
        "link": e.get("link", ""),
        "source": src,
        "ts": _ts(e),
    } for e in parsed.entries]
    items.sort(key=lambda i: i["ts"], reverse=True)
    return items

def merge_and_cap(items, max_items=12):
    return sorted(items, key=lambda i: i["ts"], reverse=True)[:max_items]

def provider(cfg):
    feeds = (cfg.get("news") or {}).get("feeds") or []
    max_items = (cfg.get("news") or {}).get("max_items", 12)
    def _do():
        all_items = []
        for url in feeds:
            try:
                r = httpx.get(url, timeout=10, follow_redirects=True,
                              headers={"User-Agent": "Lifeboard/1.0"})
                r.raise_for_status()
                all_items += items_from_feed_text(r.text)
            except Exception:
                continue  # one bad feed shouldn't sink the panel
        return ok(ID, TITLE, items=merge_and_cap(all_items, max_items))
    return run_provider(ID, TITLE, _do)
```

- [ ] **Step 5: Run, expect pass.** Commit.

---

## Task 5: Trading provider (jarvis snapshot)

**Approach:** Loose coupling. Prefer a configured `jarvis_api_url` (the running trading dashboard's `/api/securities` or similar); else read a snapshot from `jarvis_dir`. Behind one function with a graceful "no data" state. Exact jarvis source is verified at build time against `~/.jarvis`.

**Files:** Create `backend/providers/trading_jarvis.py`, `tests/fixtures/fake_jarvis/portfolio_snapshot.json`, `tests/test_trading_jarvis.py`.

- [ ] **Step 1: Write `tests/fixtures/fake_jarvis/portfolio_snapshot.json`**
```json
{"total_value": 1603.20, "day_change_abs": 12.40, "day_change_pct": 0.78,
 "holdings": [
   {"ticker": "RKLB", "day_change_pct": 4.1, "value": 210.0},
   {"ticker": "LEU", "day_change_pct": -2.3, "value": 180.0}
 ]}
```

- [ ] **Step 2: Write failing test** (`tests/test_trading_jarvis.py`)
```python
import pathlib
from backend.providers import trading_jarvis as tr

FIX = pathlib.Path(__file__).parent / "fixtures" / "fake_jarvis"

def test_summary_from_snapshot():
    env = tr.provider({"trading": {"jarvis_dir": str(FIX), "jarvis_api_url": ""}})
    assert env["status"] == "ok"
    assert env["value"]["total_value"] == 1603.20
    movers = env["items"]
    assert movers[0]["ticker"] == "RKLB"   # best mover first
    assert movers[-1]["ticker"] == "LEU"

def test_missing_dir_is_setup():
    env = tr.provider({"trading": {"jarvis_dir": "/no/such", "jarvis_api_url": ""}})
    assert env["status"] in ("setup", "error")
```

- [ ] **Step 3: Run, expect fail.**

- [ ] **Step 4: Implement `backend/providers/trading_jarvis.py`**
```python
import json, pathlib
import httpx
from backend.envelope import ok, setup, run_provider

ID, TITLE = "trading", "Trading & money"

def _movers(holdings):
    h = [x for x in holdings if x.get("day_change_pct") is not None]
    h.sort(key=lambda x: x["day_change_pct"], reverse=True)
    return h

def _from_snapshot(jarvis_dir):
    p = pathlib.Path(jarvis_dir) / "portfolio_snapshot.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    value = {"total_value": data.get("total_value"),
             "day_change_abs": data.get("day_change_abs"),
             "day_change_pct": data.get("day_change_pct")}
    return ok(ID, TITLE, items=_movers(data.get("holdings", [])), value=value)

def provider(cfg):
    t = cfg.get("trading") or {}
    api = t.get("jarvis_api_url")
    jdir = t.get("jarvis_dir") or "~/.jarvis"
    def _do():
        if api:
            r = httpx.get(api, timeout=8); r.raise_for_status()
            data = r.json()
            value = {"total_value": data.get("total_value"),
                     "day_change_abs": data.get("day_change_abs"),
                     "day_change_pct": data.get("day_change_pct")}
            return ok(ID, TITLE, items=_movers(data.get("holdings", [])), value=value)
        snap = _from_snapshot(jdir)
        if snap is None:
            return setup(ID, TITLE, "No trading snapshot found in jarvis dir yet.")
        return snap
    return run_provider(ID, TITLE, _do)
```

- [ ] **Step 5: Run, expect pass.** Commit. **Build-time note:** inspect `~/.jarvis` for a real snapshot source; if none exists as JSON, add a tiny `jarvis_api_url` default or a one-shot snapshot writer. Keep the provider's public shape unchanged.

---

## Task 6: Claude projects provider

**Files:** Create `backend/providers/claude_projects.py`, `tests/test_claude_projects.py`.

- [ ] **Step 1: Write failing test**
```python
import pathlib, time
from backend.providers import claude_projects as cp

def test_lists_recent_projects(tmp_path):
    d = tmp_path / "projects"
    (d / "-Users-omri-foo").mkdir(parents=True)
    (d / "-Users-omri-foo" / "x.jsonl").write_text("{}")
    env = cp.provider({"claude": {"projects_dir": str(d)}})
    assert env["status"] == "ok"
    assert env["items"][0]["name"]  # has a friendly name
    assert "last_active" in env["items"][0]
```

- [ ] **Step 2: Run, expect fail.**

- [ ] **Step 3: Implement `backend/providers/claude_projects.py`**
```python
import pathlib, datetime
from backend.envelope import ok, setup, run_provider

ID, TITLE = "feeds_claude", "Claude projects"

def _friendly(name):
    # "-Users-omri-code-backtester" -> "backtester"
    return name.rstrip("-").split("-")[-1] or name

def provider(cfg):
    root = pathlib.Path((cfg.get("claude") or {}).get("projects_dir", "~/.claude/projects"))
    def _do():
        if not root.exists():
            return setup(ID, TITLE, "No Claude projects directory found.")
        rows = []
        for d in root.iterdir():
            if not d.is_dir():
                continue
            files = list(d.glob("*.jsonl"))
            mtime = max([f.stat().st_mtime for f in files], default=d.stat().st_mtime)
            rows.append({"name": _friendly(d.name), "raw": d.name,
                         "sessions": len(files),
                         "last_active": datetime.datetime.fromtimestamp(mtime).isoformat(timespec="seconds")})
        rows.sort(key=lambda r: r["last_active"], reverse=True)
        return ok(ID, TITLE, items=rows[:8])
    return run_provider(ID, TITLE, _do)
```

- [ ] **Step 4: Run, expect pass.** Commit.

---

## Task 7: To-dos store + provider

**Files:** Create `backend/providers/todos.py`, `tests/test_todos.py`.

- [ ] **Step 1: Write failing test**
```python
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
```

- [ ] **Step 2: Run, expect fail.**

- [ ] **Step 3: Implement `backend/providers/todos.py`**
```python
import json, os, pathlib, uuid, tempfile
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
    _save(items); return items

def toggle(tid):
    items = _load()
    for it in items:
        if it["id"] == tid:
            it["done"] = not it["done"]
    _save(items); return items

def delete(tid):
    items = [i for i in _load() if i["id"] != tid]
    _save(items); return items

def provider(cfg):
    return run_provider(ID, TITLE, lambda: ok(ID, TITLE, items=_load()))
```

- [ ] **Step 4: Run, expect pass.** Commit.

---

## Task 8: Notion habits provider

**Approach:** Talk to Notion REST (`https://api.notion.com/v1`, header `Notion-Version: 2022-06-28`) via httpx with the integration token. Pure logic (mapping Notion rows -> habit items, computing today's done-state and streaks) is split out and unit-tested without network; the HTTP calls are thin wrappers. First-run database creation is one guarded helper. If no token: `setup` envelope.

**Habit model:** one Notion database, one row per habit (`Name` title). A separate "log" is modeled as a `Date`-typed property `Last done` + a `Number` `Streak`, OR a per-day checkbox. For v1: a row per habit with `Done today` (checkbox, reset daily by the engine based on `Last done` date) and `Streak` (number). Schema finalized in build; logic tested against dict fixtures shaped like Notion's API.

**Files:** Create `backend/providers/habits_notion.py`, `tests/test_habits_notion.py`.

- [ ] **Step 1: Write failing test** (pure-logic, no network)
```python
import datetime
from backend.providers import habits_notion as hb

def _row(name, last_done, streak, done_today):
    return {"id": "p1", "properties": {
        "Name": {"title": [{"plain_text": name}]},
        "Last done": {"date": {"start": last_done} if last_done else None},
        "Streak": {"number": streak},
        "Done today": {"checkbox": done_today},
    }}

def test_map_rows_to_items():
    today = datetime.date(2026, 6, 2)
    rows = [_row("Read", "2026-06-02", 5, True), _row("Run", "2026-05-30", 2, False)]
    items = hb.rows_to_items(rows, today=today)
    assert items[0]["name"] == "Read" and items[0]["done_today"] is True
    assert items[0]["streak"] == 5
    # stale "done today" from a previous day is treated as not-done
    assert items[1]["done_today"] is False

def test_setup_state_without_token():
    env = hb.provider({"notion": {"token": ""}})
    assert env["status"] == "setup"
```

- [ ] **Step 2: Run, expect fail.**

- [ ] **Step 3: Implement `backend/providers/habits_notion.py`**
```python
import datetime
import httpx
from backend.envelope import ok, setup, run_provider

ID, TITLE = "today_habits", "Habits"
API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

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

def _headers(token):
    return {"Authorization": f"Bearer {token}", "Notion-Version": VERSION,
            "Content-Type": "application/json"}

def _query(token, db_id):
    r = httpx.post(f"{API}/databases/{db_id}/query", headers=_headers(token), json={}, timeout=10)
    r.raise_for_status()
    return r.json().get("results", [])

def tick(cfg, page_id):
    token = cfg["notion"]["token"]
    today = datetime.date.today().isoformat()
    body = {"properties": {
        "Done today": {"checkbox": True},
        "Last done": {"date": {"start": today}},
    }}
    r = httpx.patch(f"{API}/pages/{page_id}", headers=_headers(token), json=body, timeout=10)
    r.raise_for_status()
    return r.json()

def provider(cfg):
    n = cfg.get("notion") or {}
    token, db_id = n.get("token"), n.get("habits_database_id")
    if not token:
        return setup(ID, TITLE, "Add your Notion integration token in settings to track habits.")
    if not db_id:
        return setup(ID, TITLE, "Notion connected — share a page so Lifeboard can create your habits database.")
    return run_provider(ID, TITLE, lambda: ok(ID, TITLE, items=rows_to_items(_query(token, db_id))))
```

- [ ] **Step 4: Run, expect pass.** Commit. **Build-time note:** add `ensure_database(cfg)` that creates the habits DB under `parent_page_id` if `habits_database_id` is blank, with properties Name(title)/Done today(checkbox)/Last done(date)/Streak(number); wire streak increment into `tick`.

---

## Task 9: FastAPI app + endpoints

**Files:** Create `backend/app.py`, `tests/test_api_smoke.py`.

Endpoints: `GET /api/board` (all enabled panels at once), `GET /api/panel/{id}`, `POST /api/todos` `{text}`, `POST /api/todos/{id}/toggle`, `DELETE /api/todos/{id}`, `POST /api/habits/{page_id}/tick`, plus static mounts for `/`, `/a`, `/b`, `/c` and `/shared`.

- [ ] **Step 1: Write failing smoke test** (`tests/test_api_smoke.py`)
```python
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_board_returns_panels():
    r = client.get("/api/board")
    assert r.status_code == 200
    body = r.json()
    assert "panels" in body and isinstance(body["panels"], list)
    ids = {p["id"] for p in body["panels"]}
    assert {"today_todos", "feeds_news"} & ids  # at least some panels present

def test_todo_roundtrip():
    r = client.post("/api/todos", json={"text": "smoke item"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["text"] == "smoke item" for i in items)
```

- [ ] **Step 2: Run, expect fail.**

- [ ] **Step 3: Implement `backend/app.py`**
```python
import pathlib
from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import load_config
from backend.providers import (calendar_ical, news_rss, trading_jarvis,
                               claude_projects, todos, habits_notion)

FRONTEND = pathlib.Path(__file__).parent.parent / "frontend"
app = FastAPI(title="Lifeboard")

# panel id -> provider callable(cfg)
PROVIDERS = {
    "today_calendar": calendar_ical.provider,
    "today_todos": todos.provider,
    "today_habits": habits_notion.provider,
    "trading": trading_jarvis.provider,
    "feeds_claude": claude_projects.provider,
    "feeds_news": news_rss.provider,
}

def _enabled_panel_ids(cfg):
    groups = {"today": ["today_calendar", "today_todos", "today_habits"],
              "trading": ["trading"],
              "feeds": ["feeds_claude", "feeds_news"]}
    ids = []
    for key in cfg.get("panels", []):
        ids += groups.get(key, [])
    return ids

@app.get("/api/board")
def board():
    cfg = load_config()
    panels = [PROVIDERS[pid](cfg) for pid in _enabled_panel_ids(cfg) if pid in PROVIDERS]
    return {"display_name": cfg.get("display_name"), "goals": cfg.get("goals", []),
            "theme": cfg.get("theme", "a"), "panels": panels}

@app.get("/api/panel/{pid}")
def panel(pid: str):
    cfg = load_config()
    if pid not in PROVIDERS:
        return {"id": pid, "status": "error", "error": "unknown panel"}
    return PROVIDERS[pid](cfg)

@app.post("/api/todos")
def add_todo(text: str = Body(..., embed=True)):
    todos.add(text); return todos.provider(load_config())

@app.post("/api/todos/{tid}/toggle")
def toggle_todo(tid: str):
    todos.toggle(tid); return todos.provider(load_config())

@app.delete("/api/todos/{tid}")
def del_todo(tid: str):
    todos.delete(tid); return todos.provider(load_config())

@app.post("/api/habits/{page_id}/tick")
def tick_habit(page_id: str):
    cfg = load_config(); habits_notion.tick(cfg, page_id)
    return habits_notion.provider(cfg)

# static frontends
for route in ("a", "b", "c"):
    d = FRONTEND / route
    if d.exists():
        app.mount(f"/{route}", StaticFiles(directory=str(d), html=True), name=route)
if (FRONTEND / "shared").exists():
    app.mount("/shared", StaticFiles(directory=str(FRONTEND / "shared")), name="shared")

@app.get("/")
def launcher():
    return FileResponse(str(FRONTEND / "index.html"))
```

- [ ] **Step 4: Run, expect pass.** Commit.

---

## Task 10: Frontend data layer + launcher

**Files:** Create `frontend/index.html`, `frontend/shared/lifeboard-core.js`, `frontend/shared/panels.js`.

- [ ] **Step 1: `lifeboard-core.js`** — `LB.board()` fetches `/api/board`; `LB.addTodo/toggleTodo/deleteTodo/tickHabit` call the POST/DELETE endpoints; tiny helpers `el()` and `fmtMoney()`. (Full code written at build time; contract = the envelope above.)
- [ ] **Step 2: `panels.js`** — generic renderers keyed by panel `id`/`status`: render `setup` hint, `error` message, and per-panel item lists (calendar rows, todo rows with check + delete, habit rows with tick, trading value + movers, news/claude lists).
- [ ] **Step 3: `index.html`** — launcher linking to `/a`, `/b`, `/c` with one-line descriptions.
- [ ] **Step 4: Manual check** — boot `run.sh`, open `/`, confirm JSON renders. Commit.

---

## Task 11–13: Frontends A / B / C (use frontend-design skill)

For each design: `frontend/<x>/index.html`, `style.css`, `app.js` (imports the shared core, lays out the same panels in its own visual language).
- **A — Calm & personal:** spacious, soft, a daily check-in.
- **B — Mission control:** dense, glowing, everything at once.
- **C — Editorial:** typographic, magazine-like (build if budget allows).

Each task: build the design, boot the engine, load the page against real data, verify panels render and todo/habit actions work, commit. Use the **frontend-design** skill for these.

---

## Task 14: README (non-technical)

**Files:** Create `README.md`.
- [ ] What it is; how to run (`./run.sh`, open the link).
- [ ] One-time **calendar** setup: Google Calendar → Settings → *Settings for my calendars* → *Integrate calendar* → copy **Secret address in iCal format** → paste into `~/.lifeboard/config.json` under `calendar.ical_urls`.
- [ ] One-time **Notion** setup: create an integration at notion.so/my-integrations → copy token → paste into `notion.token` → create/share a page → paste its id into `notion.parent_page_id` → restart; the board creates the habits database.
- [ ] How to switch designs; how to add a new panel later (provider + card + settings line).
- [ ] Commit.

---

## Self-Review

- **Spec coverage:** living panel system (Task 1, 9 generic dispatch) ✓; Today/planner = calendar (T3) + todos (T7) + habits/Notion (T8) ✓; Trading (T5) ✓; Feeds = Claude projects (T6) + news (T4) ✓; settings file + example (T2) ✓; always-live fetch server-side (T3/T4/T8) ✓; persistence (T7 todos, T8 Notion) ✓; 2–3 frontends over shared data (T10–13) ✓; run instructions + setup (T0 run.sh, T14 README) ✓; per-panel error isolation (envelope `run_provider`, T1) ✓.
- **Placeholder scan:** frontend visual code (T10–13) intentionally deferred to the frontend-design skill with a fixed data contract — not a logic placeholder. Build-time notes on trading source (T5) and Notion DB creation/streaks (T8) are explicit follow-ups with defined function shapes, not vague TODOs.
- **Type consistency:** every provider exposes `provider(cfg) -> envelope`; envelope keys (`id/title/status/updated_at/value/items/error/hint`) consistent across Tasks 1–9; `PROVIDERS` ids in Task 9 match each provider's `ID`.
