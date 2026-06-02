"""Calendar panel via Apple's native EventKit (fast, self-contained — no other app
needed). The first read after boot can be slow while macOS warms its calendar
cache, so we fetch in the background (stale-while-revalidate) and the board never
blocks on it. Access is a one-time macOS Calendar permission."""
import datetime

from backend import cache
from backend.envelope import ok, setup, error

ID, TITLE = "today_calendar", "Calendar"
_KEY, _TTL = "apple_calendar", 300

try:
    import EventKit
    import Foundation
    _HAVE = True
except Exception:  # not on macOS / pyobjc missing
    _HAVE = False

_store = None


def _get_store():
    global _store
    if _store is None:
        _store = EventKit.EKEventStore.alloc().init()
        if EventKit.EKEventStore.authorizationStatusForEntityType_(0) == 0:
            done = {}
            def _cb(granted, err):
                done["g"] = granted
            try:
                _store.requestFullAccessToEventsWithCompletion_(_cb)
            except AttributeError:
                _store.requestAccessToEntityType_completion_(0, _cb)
            import time as _t
            rl = Foundation.NSRunLoop.currentRunLoop()
            t0 = _t.time()
            while "g" not in done and _t.time() - t0 < 8:
                rl.runMode_beforeDate_(Foundation.NSDefaultRunLoopMode,
                                       Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.05))
    return _store


def _fetch(day=None):
    day = day or datetime.date.today()
    start = datetime.datetime.combine(day, datetime.time.min)
    end = start + datetime.timedelta(days=1)
    store = _get_store()
    sd = Foundation.NSDate.dateWithTimeIntervalSince1970_(start.timestamp())
    ed = Foundation.NSDate.dateWithTimeIntervalSince1970_(end.timestamp())
    pred = store.predicateForEventsWithStartDate_endDate_calendars_(sd, ed, None)
    events = store.eventsMatchingPredicate_(pred) or []
    out = []
    for e in events:
        st = datetime.datetime.fromtimestamp(e.startDate().timeIntervalSince1970())
        out.append({
            "title": str(e.title() or "(no title)"),
            "location": str(e.location()) if e.location() else None,
            "start": st.isoformat(),
            "all_day": bool(e.isAllDay()),
        })
    out.sort(key=lambda x: x["start"])
    return out


def prewarm():
    """Kick the (possibly slow) first fetch in the background at startup."""
    if _HAVE:
        try:
            cache.swr(_KEY, _TTL, _fetch)
        except Exception:
            pass


def provider(cfg):
    if not _HAVE:
        return setup(ID, TITLE, "Apple Calendar needs the EventKit library — pip install pyobjc-framework-EventKit.")
    try:
        items = cache.swr(_KEY, _TTL, _fetch)
    except Exception as exc:  # noqa: BLE001
        return error(ID, TITLE, exc)
    if items is None:
        return setup(ID, TITLE, "Loading your calendar…")
    return ok(ID, TITLE, items=items)
