"""The panel envelope: every provider returns this uniform shape so the board
can render any panel generically and one failing panel never sinks the board."""
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _base(id, title, status):
    return {
        "id": id,
        "title": title,
        "status": status,
        "updated_at": _now(),
        "value": None,
        "items": [],
        "error": None,
        "hint": None,
    }


def ok(id, title, items=None, value=None):
    e = _base(id, title, "ok")
    e["items"] = items or []
    e["value"] = value
    return e


def error(id, title, message):
    e = _base(id, title, "error")
    e["error"] = str(message)
    return e


def setup(id, title, hint):
    e = _base(id, title, "setup")
    e["hint"] = hint
    return e


def run_provider(id, title, fn):
    """Call a provider that returns a full envelope; wrap any exception as error.

    Panels must never crash the board, so we deliberately catch broadly.
    """
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - intentional: isolate panel failures
        return error(id, title, exc)
