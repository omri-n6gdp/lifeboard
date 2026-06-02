# Lifeboard

Your whole life on one page — calendar, to-dos, habits, trading, news, and your
Claude projects — running locally on your Mac, just for you. It's a **living
board**: you keep adding new panels over time.

There are three looks to choose from (you can switch any time):
**Daybreak** (calm), **Mission Control** (dark command-center), and
**The Ledger** (newspaper). They all show the same information.

---

## Run it

**Easiest — the Dock app.** Open **Lifeboard** from your Applications folder (drag
it onto the Dock to keep it there). One click starts the engine *and* opens the
board. To (re)build the app after updates:

```bash
cd ~/code/lifeboard
bash tools/build_app.sh
```

**Or from Terminal:**

```bash
cd ~/code/lifeboard
./run.sh
```

Either way the board opens at **http://localhost:8787** — pick a design and
you're in. To stop the Terminal version, press `Control + C`. Different port:
`./run.sh 9000`.

---

## Your settings

Everything personal lives in one file: **`~/.lifeboard/config.json`**.
Open it in any text editor. Nothing is hidden in the code — this one file is
all of it. (A blank starter is created for you the first time.)

Out of the box you already get: **live world news**, **weather** (set to London),
your **Claude projects**, and a working **to-do list**. The calendar, habits,
trading, and Spotify panels show a friendly "set up" note until you do the steps
below.

### Calendar — your Apple Calendar

Lifeboard reads **today's events straight from the Calendar app**. The first time,
macOS asks permission:

1. Open the board. A box pops up: *"Lifeboard wants access to control Calendar."*
   Click **OK**. (Missed it? System Settings → Privacy & Security → **Automation**
   → turn on **Calendar** under Lifeboard.)
2. Refresh — today's events appear. No links to copy.

> Prefer a Google/other calendar by link instead? Set
> `"calendar": { "source": "ical", "ical_urls": ["YOUR-SECRET-ICS-LINK"] }`.

### Weather

Your location is already set to **London** in `~/.lifeboard/config.json`. Change it
to anywhere:

```json
"weather": { "place": "Tel Aviv", "units": "celsius" }
```

Use any place name (or set `"latitude"`/`"longitude"` directly); `"units"` can be
`"fahrenheit"`. No API key needed.

### Habits (lives in Notion, so you can tick them off your phone too)

1. Go to **notion.so/my-integrations** → **New integration** → give it a name
   (e.g. "Lifeboard") → copy the **Internal Integration Secret** (the token).
2. In Notion, make a new empty page (e.g. "Habits"). Open the **•••** menu at the
   top-right → **Connections** → add your "Lifeboard" integration.
3. Copy that page's link; the long code at the end is its **page id**.
4. Put both into `~/.lifeboard/config.json`:

   ```json
   "notion": { "token": "PASTE-TOKEN", "habits_database_id": "", "parent_page_id": "PASTE-PAGE-ID" }
   ```
5. Save and refresh. Lifeboard **creates a "Lifeboard Habits" database** for you
   under that page. Add habit rows in Notion (a `Name` is all you need); tick them
   off from the board or from Notion — they stay in sync, and streaks are counted
   for you.

### Trading 212 (self-contained, live)

Lifeboard talks to Trading 212 **directly** — nothing else needs to be open. In
the Trading 212 web app → gear/Settings → **API (Beta)** → generate a key (it
gives a key *and* a secret; read-only is fine — it never trades). Put both in
`~/.lifeboard/config.json`:

```json
"trading": { "t212_api_key": "YOUR-KEY", "t212_api_secret": "YOUR-SECRET", "t212_base": "https://live.trading212.com" }
```

It shows total value, today's change (tracked locally day-to-day), and your
biggest holdings by profit/loss. Use `https://demo.trading212.com` for a practice
account.

### Spotify (now playing + recently played)

1. Make a free app at **developer.spotify.com/dashboard**. Note its **Client ID**
   and **Client Secret**, and in its settings add this Redirect URI:
   `http://127.0.0.1:8765/callback`.
2. In Terminal, run the one-time helper:

   ```bash
   cd ~/code/lifeboard
   .venv/bin/python tools/spotify_auth.py
   ```
   Paste the Client ID/Secret when asked; your browser opens to approve access.
   The token is saved for you automatically.
3. Refresh the board — your current track and recent plays appear.

---

## Switching designs

The launcher at **http://localhost:8787** links to all three. Or go straight to
`/a` (Daybreak), `/b` (Mission Control), `/c` (The Ledger).

---

## Adding a new panel later (the "living" part)

Lifeboard is built so a new life area is a small, contained job:

1. **A provider** — add `backend/providers/<name>.py` with a `provider(cfg)`
   function that returns an envelope (`ok(...)`, `setup(...)`, or `error(...)`
   from `backend/envelope.py`).
2. **Wire it** — add one line to `PROVIDERS` and `GROUPS` in `backend/app.py`.
3. **Show it** — add a small render function to each design (or just the one you
   use) and a settings line in `config.json`.

That's it — the engine core and the other panels don't change. Ideas for later:
University, email, fitness/health, reading — whatever you think of.

---

## How it's built (for the curious)

- A small Python (FastAPI) engine serves the board and a tiny `/api`. Each panel
  is an independent **provider** returning a uniform "envelope", so one failing
  source never blanks the whole board.
- Live data (calendar, news, Notion) is fetched **server-side**; trading and
  Claude projects are read from disk; to-dos are saved locally.
- Three frontends share one data layer (`frontend/shared/lifeboard-core.js`).
- Tests: `.venv/bin/python -m pytest` (all offline).

Design notes and the full spec live in `docs/superpowers/`.
