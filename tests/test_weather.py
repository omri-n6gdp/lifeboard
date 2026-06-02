import datetime
from backend.providers import weather as w

SAMPLE = {
    "current": {"temperature_2m": 14.3, "apparent_temperature": 12.9, "weather_code": 3, "wind_speed_10m": 11.0},
    "daily": {"temperature_2m_max": [17.2], "temperature_2m_min": [9.1], "weather_code": [61]},
    "hourly": {
        "time": ["2026-06-02T13:00", "2026-06-02T14:00", "2026-06-02T15:00"],
        "temperature_2m": [14.0, 15.1, 15.9],
        "weather_code": [3, 2, 0],
    },
}


def test_code_info():
    assert w.code_info(0)["emoji"] == "☀️"
    assert w.code_info(95)["label"].startswith("Thunder")


def test_parse_current():
    v = w.parse_current(SAMPLE, "London", "°C")
    assert v["temp"] == 14 and v["high"] == 17 and v["low"] == 9
    assert v["place"] == "London" and v["emoji"] == "☁️"  # code 3 overcast


def test_parse_hourly_from_now():
    h = w.parse_hourly(SAMPLE, count=2, now=datetime.datetime(2026, 6, 2, 14, 5))
    assert h[0]["time"] == "14:00" and h[0]["temp"] == 15
    assert h[0]["emoji"] == "⛅"  # code 2
    assert len(h) == 2


def test_setup_without_location():
    assert w.provider({"weather": {}})["status"] == "setup"
