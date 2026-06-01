# Lifeboard

Your whole life on one page — calendar, to-dos, habits, trading, news, and your
Claude projects — running locally on your Mac, just for you. It's a **living
board**: you keep adding new panels over time.

There are three looks to choose from (you can switch any time):
**Daybreak** (calm), **Mission Control** (dark command-center), and
**The Ledger** (newspaper). They all show the same information.

---

## Run it

Open Terminal and paste:

```bash
cd ~/code/lifeboard
./run.sh
```

Then open **http://localhost:8787** in your browser. Pick a design and you're in.

To stop it, click the Terminal window and press `Control + C`.
To use a different port: `./run.sh 9000` → open http://localhost:9000.

---

## Your settings

Everything personal lives in one file: **`~/.lifeboard/config.json`**.
Open it in any text editor. Nothing is hidden in the code — this one file is
all of it. (A blank starter is created for you the first time.)

Out of the box you already get: **live world news**, your **Claude projects**,
and a working **to-do list**. The calendar, habits, and trading panels show a
friendly "set up" note until you add the bits below.

### Calendar (2 minutes, no account-linking)

1. Open **Google Calendar** in a browser → click the ⚙️ gear → **Settings**.
2. On the left, under *Settings for my calendars*, click the calendar you want.
3. Scroll to **Integrate calendar** → copy the **Secret address in iCal format**
   (the long link ending in `.ics`).
4. Paste it into `~/.lifeboard/config.json` like this:

   ```json
   "calendar": { "ical_urls": ["PASTE-YOUR-SECRET-LINK-HERE"] }
   ```
5. Save the file and refresh the page. Today's events appear.

> The "secret" link is read-only and private to you. Keep it to yourself.

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

### Trading

If your Trading 212 / jarvis dashboard is running, point Lifeboard at it:

```json
"trading": { "jarvis_dir": "~/.jarvis", "jarvis_api_url": "http://localhost:PORT/api/portfolio" }
```

…or drop a `portfolio_snapshot.json` (with `total_value`, `day_change_abs`,
`day_change_pct`, and a `holdings` list) into `~/.jarvis`. Until then the panel
just shows a "hook up your portfolio" note.

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

That's it — the engine core and the other panels don't change. Ideas already
sketched for later: University, email, Spotify now-playing, weather, fitness.

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
