"""Trading panel: a glanceable portfolio summary. Loosely coupled to the existing
jarvis trading system -- prefers a configured running API, else reads a snapshot
JSON from the jarvis dir. Deliberately does NOT reimplement the quant engine."""
import json
import pathlib

import httpx

from backend.envelope import ok, setup, run_provider

ID, TITLE = "trading", "Trading & money"


def _movers(holdings):
    h = [x for x in holdings if x.get("day_change_pct") is not None]
    h.sort(key=lambda x: x["day_change_pct"], reverse=True)
    return h


def _value_block(data):
    return {
        "total_value": data.get("total_value"),
        "day_change_abs": data.get("day_change_abs"),
        "day_change_pct": data.get("day_change_pct"),
    }


def _from_snapshot(jarvis_dir):
    p = pathlib.Path(jarvis_dir) / "portfolio_snapshot.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return ok(ID, TITLE, items=_movers(data.get("holdings", [])), value=_value_block(data))


def provider(cfg):
    t = cfg.get("trading") or {}
    api = t.get("jarvis_api_url")
    jdir = t.get("jarvis_dir") or "~/.jarvis"

    def _do():
        if api:
            r = httpx.get(api, timeout=8)
            r.raise_for_status()
            data = r.json()
            return ok(ID, TITLE, items=_movers(data.get("holdings", [])), value=_value_block(data))
        snap = _from_snapshot(jdir)
        if snap is None:
            return setup(ID, TITLE, "No trading snapshot found yet — point trading.jarvis_api_url at your running dashboard, or drop a portfolio_snapshot.json in the jarvis folder.")
        return snap

    return run_provider(ID, TITLE, _do)
