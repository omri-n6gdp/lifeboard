"""Tiny in-process cache so the board is fast and never blocks on a slow source.

- ttl_cached: blocking memo with a time-to-live (fast panels).
- swr: stale-while-revalidate — returns the cached value immediately (or None on a
  cold cache) and refreshes in a background thread (the slow calendar panel)."""
import threading
import time

_lock = threading.Lock()
_data = {}        # key -> (value, timestamp)
_inflight = set()  # keys currently being refreshed in the background


def ttl_cached(key, ttl, fn):
    now = time.time()
    with _lock:
        v = _data.get(key)
        if v and now - v[1] < ttl:
            return v[0]
    val = fn()
    with _lock:
        _data[key] = (val, time.time())
    return val


def _spawn(key, fn):
    def run():
        try:
            val = fn()
            with _lock:
                _data[key] = (val, time.time())
        except Exception:
            pass
        finally:
            with _lock:
                _inflight.discard(key)
    threading.Thread(target=run, daemon=True).start()


def swr(key, ttl, fn):
    """Return cached value now (or None if nothing cached yet); refresh in the
    background when missing or older than ttl. Never blocks the caller."""
    now = time.time()
    with _lock:
        v = _data.get(key)
        stale = (v is None) or (now - v[1] >= ttl)
        spawn = stale and key not in _inflight
        if spawn:
            _inflight.add(key)
    if spawn:
        _spawn(key, fn)
    return v[0] if v else None


def peek(key):
    """Return the cached value regardless of age (or None)."""
    with _lock:
        v = _data.get(key)
    return v[0] if v else None


def invalidate(key):
    with _lock:
        _data.pop(key, None)
