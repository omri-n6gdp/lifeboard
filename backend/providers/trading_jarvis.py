"""Trading panel: a glanceable portfolio summary. Loosely coupled to the existing
jarvis Trading 212 dashboard -- preferred source is that dashboard's running API
(`jarvis_base_url` -> /api/snapshot + /api/securities), which we map into a small
summary. Falls back to a single endpoint or an on-disk snapshot. Never
reimplements the quant engine."""
import json
import pathlib

import httpx

from backend import cache
from backend.envelope import ok, setup, run_provider

ID, TITLE = "trading", "Trading & money"


def _movers(holdings):
    h = [x for x in holdings if x.get("day_change_pct") is not None]
    h.sort(key=lambda x: x["day_change_pct"], reverse=True)
    return h


def _value_block(data):
    return {"total_value": data.get("total_value"),
            "day_change_abs": data.get("day_change_abs"),
            "day_change_pct": data.get("day_change_pct")}


def map_jarvis(snap, secs):
    """Map the jarvis dashboard's /api/snapshot + /api/securities into our panel.
    Total value and today's change come from the portfolio value curve; the list
    is the largest holdings with their overall return."""
    curve = ((snap or {}).get("performance_overall") or {}).get("curve") or []
    total = day_abs = day_pct = None
    if curve:
        last = curve[-1].get("v")
        total = last
        if len(curve) >= 2 and curve[-2].get("v"):
            prev = curve[-2]["v"]
            day_abs = round(last - prev, 2)
            day_pct = round((last - prev) / prev * 100, 2)
    if total is None:
        total = (((snap or {}).get("performance_overall") or {}).get("stats") or {}).get("current_value")
    holdings = sorted([s for s in (secs or []) if s.get("market_value")],
                      key=lambda s: s.get("market_value") or 0, reverse=True)[:6]
    items = [{"ticker": s.get("ticker"),
              "day_change_pct": s.get("return_pct"),
              "value": round((s.get("market_value") or 0), 2)} for s in holdings]
    value = {"total_value": round(total, 2) if total else None,
             "day_change_abs": day_abs, "day_change_pct": day_pct}
    return value, items


def _from_snapshot(jarvis_dir):
    p = pathlib.Path(jarvis_dir) / "portfolio_snapshot.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return ok(ID, TITLE, items=_movers(data.get("holdings", [])), value=_value_block(data))


def provider(cfg):
    t = cfg.get("trading") or {}
    base = t.get("jarvis_base_url")
    api = t.get("jarvis_api_url")
    jdir = t.get("jarvis_dir") or "~/.jarvis"

    if base:
        def _base_do():
            b = base.rstrip("/")
            try:
                snap = httpx.get(b + "/api/snapshot", timeout=8); snap.raise_for_status()
                secs = httpx.get(b + "/api/securities", timeout=8); secs.raise_for_status()
            except Exception:
                return setup(ID, TITLE, "Couldn’t reach your Trading 212 dashboard — make sure it’s running (it lives at ~/trading_212_dashboard).")
            value, items = map_jarvis(snap.json(), secs.json())
            return ok(ID, TITLE, items=items, value=value)
        return cache.ttl_cached("trading", 60, _base_do)

    def _do():
        if api:
            r = httpx.get(api, timeout=8)
            r.raise_for_status()
            data = r.json()
            return ok(ID, TITLE, items=_movers(data.get("holdings", [])), value=_value_block(data))
        snap = _from_snapshot(jdir)
        if snap is None:
            return setup(ID, TITLE, "No trading data yet — point trading.jarvis_base_url at your dashboard, or drop a portfolio_snapshot.json in the jarvis folder.")
        return snap

    return run_provider(ID, TITLE, _do)
