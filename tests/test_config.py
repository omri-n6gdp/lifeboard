import json
from backend.config import load_config


def test_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.config.CONFIG_PATH", tmp_path / "nope.json")
    cfg = load_config()
    assert cfg["panels"] == ["today", "trading", "feeds"]
    assert cfg["news"]["feeds"]  # defaults present


def test_user_values_override_and_merge(tmp_path, monkeypatch):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"display_name": "Omri", "news": {"max_items": 3}}))
    monkeypatch.setattr("backend.config.CONFIG_PATH", p)
    cfg = load_config()
    assert cfg["display_name"] == "Omri"
    assert cfg["news"]["max_items"] == 3
    assert cfg["news"]["feeds"]  # still merged from defaults


def test_paths_expanded(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.config.CONFIG_PATH", tmp_path / "nope.json")
    cfg = load_config()
    assert "~" not in cfg["claude"]["projects_dir"]
    assert "~" not in cfg["trading"]["jarvis_dir"]
