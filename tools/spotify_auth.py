#!/usr/bin/env python3
"""One-time Spotify authorization for Lifeboard.

Run once:  .venv/bin/python tools/spotify_auth.py

You need a (free) Spotify app from https://developer.spotify.com/dashboard with
redirect URI  http://127.0.0.1:8765/callback  added to it. This script opens your
browser, captures the approval, and saves a refresh token into
~/.lifeboard/config.json so the Spotify panel works on its own from then on.
"""
import base64
import http.server
import json
import os
import pathlib
import threading
import urllib.parse
import webbrowser

import httpx

CONFIG = pathlib.Path(os.path.expanduser("~/.lifeboard/config.json"))
REDIRECT = "http://127.0.0.1:8765/callback"
SCOPES = "user-read-currently-playing user-read-recently-played user-read-playback-state"
_code_holder = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.urlparse(self.path)
        if q.path != "/callback":
            self.send_response(404); self.end_headers(); return
        params = urllib.parse.parse_qs(q.query)
        _code_holder["code"] = (params.get("code") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Spotify connected. You can close this tab and return to Lifeboard.</h2>")

    def log_message(self, *a):
        pass


def _load_config():
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text())
        except Exception:
            return {}
    return {}


def _save_refresh(client_id, client_secret, refresh_token):
    data = _load_config()
    data.setdefault("spotify", {})
    data["spotify"].update({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    })
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(data, indent=2))


def main():
    cfg = _load_config().get("spotify", {})
    client_id = cfg.get("client_id") or input("Spotify Client ID: ").strip()
    client_secret = cfg.get("client_secret") or input("Spotify Client Secret: ").strip()

    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id, "response_type": "code",
        "redirect_uri": REDIRECT, "scope": SCOPES,
    })

    server = http.server.HTTPServer(("127.0.0.1", 8765), _Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()

    print("\nMake sure your Spotify app has this redirect URI:\n  " + REDIRECT)
    print("\nOpening your browser to authorize…")
    print("If it doesn't open, paste this into your browser:\n" + auth_url + "\n")
    webbrowser.open(auth_url)

    # wait for the single callback
    import time
    for _ in range(120):
        if _code_holder.get("code"):
            break
        time.sleep(1)
    code = _code_holder.get("code")
    if not code:
        print("Timed out waiting for authorization. Please run it again.")
        return

    tok = httpx.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT},
        headers={"Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()},
        timeout=15,
    )
    tok.raise_for_status()
    refresh = tok.json().get("refresh_token")
    if not refresh:
        print("No refresh token returned. Response: " + tok.text)
        return
    _save_refresh(client_id, client_secret, refresh)
    print("\n✅ Spotify connected and saved to ~/.lifeboard/config.json — refresh Lifeboard.")


if __name__ == "__main__":
    main()
