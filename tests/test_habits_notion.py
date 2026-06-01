import datetime
from backend.providers import habits_notion as hb


def _row(name, last_done, streak, done_today):
    return {"id": "p1", "properties": {
        "Name": {"title": [{"plain_text": name}]},
        "Last done": {"date": {"start": last_done} if last_done else None},
        "Streak": {"number": streak},
        "Done today": {"checkbox": done_today},
    }}


def test_map_rows_to_items():
    today = datetime.date(2026, 6, 2)
    rows = [_row("Read", "2026-06-02", 5, True), _row("Run", "2026-05-30", 2, False)]
    items = hb.rows_to_items(rows, today=today)
    assert items[0]["name"] == "Read" and items[0]["done_today"] is True
    assert items[0]["streak"] == 5
    # stale "done today" from a previous day is treated as not-done
    assert items[1]["done_today"] is False


def test_next_streak():
    today = datetime.date(2026, 6, 2)
    assert hb.next_streak("2026-06-01", 4, today) == 5   # done yesterday -> +1
    assert hb.next_streak("2026-06-02", 4, today) == 4   # already today -> same
    assert hb.next_streak("2026-05-20", 4, today) == 1   # gap -> reset
    assert hb.next_streak(None, 0, today) == 1


def test_setup_state_without_token():
    env = hb.provider({"notion": {"token": ""}})
    assert env["status"] == "setup"
