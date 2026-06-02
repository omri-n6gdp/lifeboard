"""Lifeboard engine: serves the board and a small /api surface. Each panel id maps
to a provider(cfg) -> envelope. Panels are grouped (today / trading / feeds) and
enabled via config so adding a new life-area panel is one line + one provider."""
import pathlib

from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import load_config
from backend.providers import (calendar_panel, news_rss, trading_jarvis,
                               claude_projects, todos, habits_notion,
                               weather, spotify)

FRONTEND = pathlib.Path(__file__).parent.parent / "frontend"
app = FastAPI(title="Lifeboard")

# panel id -> provider callable(cfg)
PROVIDERS = {
    "today_weather": weather.provider,
    "today_calendar": calendar_panel.provider,
    "today_todos": todos.provider,
    "today_habits": habits_notion.provider,
    "trading": trading_jarvis.provider,
    "feeds_claude": claude_projects.provider,
    "feeds_news": news_rss.provider,
    "spotify": spotify.provider,
}

# group key -> ordered panel ids (a "panel group" is what config enables)
GROUPS = {
    "today": ["today_weather", "today_calendar", "today_todos", "today_habits"],
    "trading": ["trading"],
    "feeds": ["spotify", "feeds_claude", "feeds_news"],
}


def _enabled_panel_ids(cfg):
    ids = []
    for key in cfg.get("panels", []):
        ids += GROUPS.get(key, [])
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
    todos.add(text)
    return todos.provider(load_config())


@app.post("/api/todos/{tid}/toggle")
def toggle_todo(tid: str):
    todos.toggle(tid)
    return todos.provider(load_config())


@app.delete("/api/todos/{tid}")
def del_todo(tid: str):
    todos.delete(tid)
    return todos.provider(load_config())


@app.post("/api/habits/{page_id}/tick")
def tick_habit(page_id: str):
    cfg = load_config()
    habits_notion.tick(cfg, page_id)
    return habits_notion.provider(cfg)


# --- static frontends (mounted only if they exist) ---
for _route in ("a", "b", "c"):
    _d = FRONTEND / _route
    if _d.exists():
        app.mount(f"/{_route}", StaticFiles(directory=str(_d), html=True), name=_route)
if (FRONTEND / "shared").exists():
    app.mount("/shared", StaticFiles(directory=str(FRONTEND / "shared")), name="shared")


@app.get("/")
def launcher():
    index = FRONTEND / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"lifeboard": "running", "hint": "frontend not built yet; try /api/board"}
