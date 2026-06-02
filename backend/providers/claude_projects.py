"""Feeds panel (part 1): recent activity across ~/.claude/projects, read from disk.
Each project folder is named after its path; we show a friendly tail + last-active."""
import datetime
import pathlib

from backend import cache
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
            rows.append({
                "name": _friendly(d.name),
                "raw": d.name,
                "sessions": len(files),
                "last_active": datetime.datetime.fromtimestamp(mtime).isoformat(timespec="seconds"),
            })
        rows.sort(key=lambda r: r["last_active"], reverse=True)
        return ok(ID, TITLE, items=rows[:8])

    return run_provider(ID, TITLE, lambda: cache.ttl_cached("claude:" + str(root), 120, _do))
