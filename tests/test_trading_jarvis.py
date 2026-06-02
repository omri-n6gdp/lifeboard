import pathlib
from backend.providers import trading_jarvis as tr

FIX = pathlib.Path(__file__).parent / "fixtures" / "fake_jarvis"


def test_summary_from_snapshot():
    env = tr.provider({"trading": {"jarvis_dir": str(FIX), "jarvis_api_url": ""}})
    assert env["status"] == "ok"
    assert env["value"]["total_value"] == 1603.20
    movers = env["items"]
    assert movers[0]["ticker"] == "RKLB"  # best mover first
    assert movers[-1]["ticker"] == "LEU"


def test_missing_dir_is_setup():
    env = tr.provider({"trading": {"jarvis_dir": "/no/such", "jarvis_api_url": ""}})
    assert env["status"] in ("setup", "error")


def test_map_jarvis():
    snap = {"performance_overall": {
        "curve": [{"t": "2026-06-01", "v": 1584.9}, {"t": "2026-06-02", "v": 1580.13}],
        "stats": {"current_value": 1585.73}}}
    secs = [{"ticker": "VWRP", "market_value": 683.51, "return_pct": 8.3},
            {"ticker": "RKLB", "market_value": 210.0, "return_pct": 40.0}]
    value, items = tr.map_jarvis(snap, secs)
    assert value["total_value"] == 1580.13
    assert value["day_change_abs"] == -4.77 and value["day_change_pct"] == -0.30
    assert items[0]["ticker"] == "VWRP"  # largest holding first
