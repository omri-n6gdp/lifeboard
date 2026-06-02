"""Spotify panel: now-playing + recently played, via the Spotify Web API.

Uses a refresh token stored in settings (obtained once with tools/spotify_auth.py),
the same direct pattern as the Notion habits panel -- the dashboard talks to
Spotify itself; this is not the assistant's MCP."""
import httpx

from backend import cache
from backend.envelope import ok, setup, run_provider

ID, TITLE = "spotify", "Spotify"


def map_current(data):
    if not data or not data.get("item"):
        return None
    it = data["item"]
    album = it.get("album") or {}
    imgs = album.get("images") or []
    return {
        "is_playing": bool(data.get("is_playing")),
        "track": it.get("name"),
        "artist": ", ".join(a.get("name", "") for a in it.get("artists", [])),
        "album": album.get("name"),
        "art": imgs[0]["url"] if imgs else None,
        "progress_ms": data.get("progress_ms"),
        "duration_ms": it.get("duration_ms"),
        "url": (it.get("external_urls") or {}).get("spotify"),
    }


def map_recent(data):
    out = []
    for x in (data.get("items") or []):
        t = x.get("track") or {}
        album = t.get("album") or {}
        imgs = album.get("images") or []
        out.append({
            "track": t.get("name"),
            "artist": ", ".join(a.get("name", "") for a in t.get("artists", [])),
            "url": (t.get("external_urls") or {}).get("spotify"),
            "art": imgs[-1]["url"] if imgs else None,
            "played_at": x.get("played_at"),
        })
    return out


def _access_token(s):
    r = httpx.post("https://accounts.spotify.com/api/token",
                   data={"grant_type": "refresh_token", "refresh_token": s["refresh_token"]},
                   auth=(s["client_id"], s["client_secret"]), timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def provider(cfg):
    s = cfg.get("spotify") or {}
    if not (s.get("client_id") and s.get("client_secret") and s.get("refresh_token")):
        return setup(ID, TITLE, "Connect Spotify — run  .venv/bin/python tools/spotify_auth.py  once to authorize.")

    def _do():
        token = _access_token(s)
        h = {"Authorization": "Bearer " + token}
        now = None
        rc = httpx.get("https://api.spotify.com/v1/me/player/currently-playing", headers=h, timeout=10)
        if rc.status_code == 200 and rc.content:
            now = map_current(rc.json())
        rr = httpx.get("https://api.spotify.com/v1/me/player/recently-played",
                       headers=h, params={"limit": 6}, timeout=10)
        recent = map_recent(rr.json()) if rr.status_code == 200 else []
        return ok(ID, TITLE, items=recent, value={"now": now})

    return run_provider(ID, TITLE, lambda: cache.ttl_cached("spotify", 15, _do))
