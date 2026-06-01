import datetime
import pathlib
from backend.providers import calendar_ical as cal

ICS = (pathlib.Path(__file__).parent / "fixtures" / "sample.ics").read_text()


def test_parse_events_for_day():
    day = datetime.date(2026, 6, 2)
    events = cal.events_from_ics(ICS, day=day, horizon_days=1)
    assert any(e["title"] == "Lecture: Quantum" for e in events)
    e = events[0]
    assert e["location"] == "Room 4" and "start" in e


def test_provider_setup_state_when_no_urls():
    env = cal.provider({"calendar": {"ical_urls": []}})
    assert env["status"] == "setup" and env["id"] == "today_calendar"
