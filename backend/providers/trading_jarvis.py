"""Trading panel: a glanceable portfolio summary. Loosely coupled to the existing
jarvis Trading 212 dashboard -- preferred source is that dashboard's running API
(`jarvis_base_url` -> /api/snapshot + /api/securities), which we map into a small
summary. Falls back to a single endpoint or an on-disk snapshot. Never
reimplements the quant engine."""
import datetime
import json
import os
import pathlib
import re

import httpx

from backend import cache
from backend.envelope import ok, setup, run_provider

ID, TITLE = "trading", "Trading & money"

# Remembers each day's opening value so we can show a real "today" change without
# any external help (yesterday's last value becomes today's baseline).
_BASELINE = pathlib.Path(os.path.expanduser("~/.lifeboard/portfolio_baseline.json"))


def _daily_change(total):
    if total is None:
        return None, None
    today = datetime.date.today().isoformat()
    data = {}
    if _BASELINE.exists():
        try:
            data = json.loads(_BASELINE.read_text())
        except Exception:
            data = {}
    if data.get("date") != today:
        baseline = data.get("last_value", total)  # yesterday's last = today's open
        data = {"date": today, "baseline": baseline, "last_value": total}
    else:
        data["last_value"] = total
        baseline = data.get("baseline", total)
    try:
        _BASELINE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE.write_text(json.dumps(data))
    except Exception:
        pass
    if not baseline:
        return 0.0, 0.0
    return round(total - baseline, 2), round((total - baseline) / baseline * 100, 2)


def _t212(t):
    """Self-contained: fetch the portfolio straight from Trading 212 (Basic auth:
    key + secret). Total value + today's change (vs a local daily baseline), and
    the biggest holdings by profit/loss with their return."""
    auth = (t.get("t212_api_key"), t.get("t212_api_secret"))
    base = (t.get("t212_base") or "https://live.trading212.com").rstrip("/")
    cash = httpx.get(base + "/api/v0/equity/account/cash", auth=auth, timeout=8)
    cash.raise_for_status()
    cash = cash.json()
    port = httpx.get(base + "/api/v0/equity/portfolio", auth=auth, timeout=8)
    port.raise_for_status()
    port = port.json()
    total = cash.get("total")
    day_abs, day_pct = _daily_change(total)
    rows = []
    for p in port:
        avg, cur = p.get("averagePrice"), p.get("currentPrice")
        ret = ((cur - avg) / avg * 100) if (avg and cur is not None) else None
        if ret is None:
            continue
        tick = re.sub(r"[a-z]+$", "", (p.get("ticker") or "").split("_")[0])  # VWRPl_EQ -> VWRP
        rows.append({"ticker": tick,
                     "day_change_pct": round(ret, 2), "ppl": p.get("ppl") or 0})
    rows.sort(key=lambda r: r["ppl"], reverse=True)
    items = [{"ticker": r["ticker"], "day_change_pct": r["day_change_pct"], "value": None}
             for r in rows[:6]]
    value = {"total_value": round(total, 2) if total else None,
             "day_change_abs": day_abs, "day_change_pct": day_pct}
    return ok(ID, TITLE, items=items, value=value)


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

    if t.get("t212_api_key") and t.get("t212_api_secret"):
        # stale-while-revalidate: one background T212 fetch at a time (no bursts to
        # hit the rate limit), and the board never blocks on it.
        val = cache.swr("trading", 60, lambda: _t212(t))
        return val if val is not None else setup(ID, TITLE, "Loading your portfolio…")

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
