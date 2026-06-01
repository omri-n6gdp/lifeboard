"""Calendar panel: fetch one or more Google "secret iCal" links server-side,
expand recurring events, and return today's events. Live, read-only."""
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
