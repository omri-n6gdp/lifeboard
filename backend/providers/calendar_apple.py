"""Calendar panel via the local Apple Calendar app (the user prefers it).

macOS keeps the calendar store behind a privacy wall, so we ask Calendar.app for
today's events through JXA (osascript). First run triggers a one-time Automation
permission prompt. Results are cached briefly so the board stays snappy."""
import datetime
import json
import subprocess
import time

from backend.envelope import ok, setup, error

ID, TITLE = "today_calendar", "Calendar"

_JXA = r"""
function run() {
  var app = Application('Calendar');
  var now = new Date();
  var s = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
  var e = new Date(s.getTime() + 24*3600*1000);
  var sLow = new Date(s.getTime() - 1000);
  var out = [];
  var cals = app.calendars;
  var cn = cals.length;
  for (var i=0; i<cn; i++) {
    var c = cals[i];
    var evs;
    try { evs = c.events.whose({_and:[{startDate:{_greaterThan:sLow}},{startDate:{_lessThan:e}}]})(); }
    catch(err){ continue; }
    for (var j=0; j<evs.length; j++) {
      var ev = evs[j];
      try {
        out.push({
          title: ev.summary(),
          start: ev.startDate().toISOString(),
          location: ev.location() || null,
          all_day: ev.alldayEvent()
        });
      } catch(e2) {}
    }
  }
  return JSON.stringify(out);
}
"""

_CACHE = {"at": 0, "raw": None}
_TTL = 60  # seconds


def parse_jxa(raw):
    data = json.loads(raw or "[]")
    items = [{
        "title": d.get("title") or "(no title)",
        "start": d.get("start"),
        "location": d.get("location") or None,
        "all_day": bool(d.get("all_day")),
    } for d in data]
    items.sort(key=lambda x: x["start"] or "")
    return items


def _run_jxa(timeout=25):
    p = subprocess.run(["osascript", "-l", "JavaScript", "-e", _JXA],
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "").strip() or "osascript failed")
    return p.stdout.strip()


def _cached_jxa():
    now = time.time()
    if _CACHE["raw"] is not None and now - _CACHE["at"] < _TTL:
        return _CACHE["raw"]
    raw = _run_jxa()
    _CACHE["raw"] = raw
    _CACHE["at"] = now
    return raw


def provider(cfg):
    try:
        raw = _cached_jxa()
    except Exception as exc:  # noqa: BLE001 - never crash the board
        msg = str(exc)
        low = msg.lower()
        if "1743" in msg or "not allow" in low or "authoriz" in low or "access" in low:
            return setup(ID, TITLE, "Allow Calendar access: System Settings → Privacy & Security → Automation → enable Calendar for Lifeboard, then refresh.")
        return error(ID, TITLE, msg)
    return ok(ID, TITLE, items=parse_jxa(raw))
