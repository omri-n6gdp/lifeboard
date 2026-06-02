from backend.providers import spotify as sp

CUR = {"is_playing": True, "progress_ms": 1000, "item": {
    "name": "Song", "duration_ms": 200000,
    "artists": [{"name": "A"}, {"name": "B"}],
    "album": {"name": "Alb", "images": [{"url": "u1"}, {"url": "u2"}]},
    "external_urls": {"spotify": "http://t"}}}

RECENT = {"items": [{"track": {
    "name": "R1", "artists": [{"name": "X"}],
    "album": {"images": [{"url": "a"}, {"url": "b"}]},
    "external_urls": {"spotify": "u"}}, "played_at": "t"}]}


def test_map_current():
    m = sp.map_current(CUR)
    assert m["track"] == "Song" and m["artist"] == "A, B"
    assert m["art"] == "u1" and m["is_playing"] is True


def test_map_current_none_when_idle():
    assert sp.map_current({}) is None
    assert sp.map_current(None) is None


def test_map_recent():
    r = sp.map_recent(RECENT)
    assert r[0]["track"] == "R1" and r[0]["artist"] == "X"
    assert r[0]["art"] == "b"  # smallest/last image


def test_setup_without_creds():
    assert sp.provider({"spotify": {}})["status"] == "setup"
