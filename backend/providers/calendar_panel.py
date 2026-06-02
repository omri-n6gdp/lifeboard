"""Calendar dispatcher: picks Apple Calendar (default, what Omri uses) or a
generic iCal URL based on `calendar.source` in settings. Both return the same
panel id so the designs render either identically."""
from backend.providers import calendar_apple, calendar_ical


def provider(cfg):
    src = ((cfg.get("calendar") or {}).get("source") or "apple").lower()
    if src == "ical":
        return calendar_ical.provider(cfg)
    return calendar_apple.provider(cfg)
