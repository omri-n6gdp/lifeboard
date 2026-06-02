import time
from backend import cache


def test_ttl_cached_memoizes(monkeypatch):
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return calls["n"]
    a = cache.ttl_cached("t1", 100, fn)
    b = cache.ttl_cached("t1", 100, fn)
    assert a == b == 1 and calls["n"] == 1  # second call served from cache


def test_ttl_cached_expires():
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return calls["n"]
    cache.ttl_cached("t2", 0, fn)
    cache.ttl_cached("t2", 0, fn)
    assert calls["n"] == 2  # ttl 0 -> always recompute


def test_swr_returns_none_then_value():
    cache.invalidate("s1")
    def fn():
        return 42
    first = cache.swr("s1", 100, fn)
    assert first is None  # cold: returns None, refreshes in background
    for _ in range(50):
        if cache.swr("s1", 100, fn) is not None:
            break
        time.sleep(0.02)
    assert cache.swr("s1", 100, fn) == 42


def test_invalidate():
    cache.ttl_cached("s2", 100, lambda: "x")
    cache.invalidate("s2")
    assert cache.ttl_cached("s2", 100, lambda: "y") == "y"
