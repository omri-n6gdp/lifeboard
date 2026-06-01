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
