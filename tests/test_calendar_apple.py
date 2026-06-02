from backend.providers import calendar_apple as ca
from backend.providers import calendar_panel


def test_parse_jxa():
    raw = '[{"title":"Lecture","start":"2026-06-02T09:00:00.000Z","location":"Room 4","all_day":false}]'
    items = ca.parse_jxa(raw)
    assert items[0]["title"] == "Lecture"
    assert items[0]["location"] == "Room 4" and items[0]["all_day"] is False


def test_parse_jxa_empty():
    assert ca.parse_jxa("[]") == []
    assert ca.parse_jxa("") == []


def test_dispatcher_ical_source():
    env = calendar_panel.provider({"calendar": {"source": "ical", "ical_urls": []}})
    assert env["status"] == "setup" and env["id"] == "today_calendar"
