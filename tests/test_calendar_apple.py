from backend.providers import calendar_panel


def test_dispatcher_ical_source():
    # ical source with no urls -> setup, offline, same panel id as Apple path
    env = calendar_panel.provider({"calendar": {"source": "ical", "ical_urls": []}})
    assert env["status"] == "setup" and env["id"] == "today_calendar"
