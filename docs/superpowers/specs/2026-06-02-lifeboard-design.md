# Lifeboard — Personal Life Dashboard

**Date:** 2026-06-02
**Status:** Design approved, pending spec review
**Owner:** Omri

> *"A personal dashboard that tracks absolutely everything in my life in one
> place — habits, university, calendar, trading, Claude projects, to-do lists,
> news — and that I can keep adding to."*

---

## 1. Vision & guiding principle

Lifeboard is a single page Omri opens every day that pulls his whole life into
one view. The defining requirement is **"that I can add to"** — so the product
is not a fixed set of features, it is a **living board** built around a panel
(card) system. Version one ships a working, good-looking board with the three
highest-value panels; every life area after that snaps in as a new card without
touching the rest of the board.

Two principles, both carried over from how Omri likes these builds:

1. **Data layer first, then several distinct frontends.** Build and verify the
   engine and its data once, then produce **2–3 genuinely different visual
   designs** over the same data and let Omri pick.
2. **Nothing personal in the code.** Every personal or account-specific value
   (name, calendar link, news feeds, trading key location, goals) lives in one
   **editable settings file**, seeded from an example template, so the tool is
   generic and shareable.

This mirrors the architecture of his Trading 212 / "jarvis" dashboard, which is
the proven pattern on this machine.

---

## 2. Goals & non-goals

### Goals (v1)
- A local, single-user dashboard that runs on Omri's Mac and opens in a browser.
- A **panel system** that makes adding a new life area a ~10-minute job.
- Three working panels: **Today / planner**, **Trading & money**, **Feeds**.
- **Always-live** data where it applies, fetched by the engine itself (no manual
  refresh): calendar via a private link, news via public feeds, trading from the
  existing jarvis data, Claude projects from disk.
- Things Omri types (to-dos, habit check-offs) **persist** between sessions.
- One editable settings file; nothing personal hardcoded.
- 2–3 distinct frontend designs sharing one data layer.
- Copy-paste run instructions matching his other dashboards.

### Non-goals (v1 — explicitly deferred)
- University panel (chosen to come later; design must accommodate it).
- Email, Spotify now-playing, weather, and other future panels (backlog in §11).
- Multi-user, authentication, cloud hosting, mobile-native app.
- Writing back to external services (e.g. creating Google Calendar events). v1
  reads the calendar; it does not edit it.
- Full Google OAuth. Calendar uses the private iCal secret link instead (far
  less setup for a non-technical user).

---

## 3. Architecture

Four cleanly separated units, each with one job:

```
                ┌──────────────────────────────────────────────┐
   Browser ───▶ │  Frontend (the board)                        │
                │  - 2-3 distinct designs                      │
                │  - shared data layer (lifeboard-core.js)     │
                │  - renders panels as cards                    │
                └───────────────▲──────────────────────────────┘
                                │  reads from / writes to  (/api/*)
                ┌───────────────┴──────────────────────────────┐
                │  Engine (Python web server, like jarvis)      │
                │  - serves the board + the /api surface        │
                │  - one provider module per panel              │
                └───┬───────────────┬───────────────┬──────────┘
                    │               │               │
          ┌─────────▼──┐   ┌────────▼─────┐   ┌─────▼───────────┐
          │ Live fetch │   │ Read on-disk │   │ Local user data │
          │ - calendar │   │ - jarvis     │   │ - to-dos        │
          │   (iCal)   │   │   trading    │   │ - habits/streaks│
          │ - news RSS │   │ - .claude    │   │ (saved file)    │
          └────────────┘   │   projects   │   └─────────────────┘
                           └──────────────┘
              All personal values come from one settings file.
```

### 3.1 The engine (backend)
A small Python web server (FastAPI + uvicorn, the same stack Omri already runs).
Responsibilities:
- Serve the board and the design variants.
- Expose a small `/api` surface (one read endpoint per panel; read+write for
  panels that accept input).
- Fetch live data **server-side** (calendar iCal, news RSS) so there are no
  browser CORS problems and no keys exposed to the page.
- Read existing on-disk data (jarvis trading, `~/.claude/projects`).
- Read and write the local user-data store (to-dos, habits).
- Load all personal values from the settings file.

### 3.2 The settings file
`~/.lifeboard/config.json`, copied once from
`backend/data/lifeboard.config.example.json`. Holds: display name, calendar
secret link(s), chosen news feeds, location of the trading data/key, goals, and
which panels are enabled + their order. No personal data anywhere else.

### 3.3 The local user-data store
A small local file (JSON to start; SQLite if it grows) under `~/.lifeboard/`
that persists everything Omri types — to-do items and their done-state, habit
definitions, and daily check-offs / streaks. Read and written only through the
engine.

### 3.4 The frontend (the board)
Static HTML/CSS/JS served by the engine. A shared `lifeboard-core.js` provides
the data layer (fetch from `/api`, simple state, a small chart helper). On top
of it sit **2–3 distinct designs** as separate routes (e.g. `/a`, `/b`, `/c`)
with a launcher at `/`. Each design renders the same panels; they differ only in
look and interaction.

---

## 4. The panel system (the "living" core)

This is the most important part of the design, because "I can add to it" is the
whole point. A **panel** is a self-contained unit defined by three small pieces:

1. **A provider** (backend): one module that returns the panel's data (and
   accepts input, if the panel takes any). One file per panel, no shared state
   with other panels.
2. **A card** (frontend): one component that renders the panel's data inside the
   board grid. One per design, but driven by the same data shape.
3. **A settings entry**: a line in `config.json` that enables the panel, sets its
   order/size, and supplies any per-panel config (e.g. which news feeds).

**Adding a new life area later = add one provider + one card + one settings
line.** No change to the engine core, the board shell, or the other panels. The
spec's success is measured by how true this stays.

Each panel's data is returned in a small common envelope so the board can render
any panel generically (title, status/last-updated, items or value, optional
error). This keeps cards uniform and makes a brand-new panel render correctly
before it has any bespoke styling.

---

## 5. Version-one panels

### 5.1 Today / planner
The daily heart of the board. Three sub-sections in one card (or three small
cards in a "Today" group, design-dependent):

- **Calendar (live, read-only):** today's events pulled from the engine, which
  fetches Omri's private iCal secret link(s) from Google Calendar and parses
  them. Shows time, title, and location for today (and optionally the next few
  upcoming). Refreshed on load and on a timer.
- **To-do list (read + write):** add an item, tick it done, delete it. Saved to
  the local user-data store so it persists. Optional due-date/sort later.
- **Habits (read + write):** a set of daily habits (defined in settings or via
  the UI); tap to check off today; the engine tracks streaks and recent history.

### 5.2 Trading & money
A glanceable summary of Omri's portfolio, **reusing the jarvis data already on
disk** (`~/.jarvis/`) rather than rebuilding any trading logic. Loosely coupled:
Lifeboard reads a portfolio snapshot from the jarvis data layer (the same source
the trading dashboard maintains from the T212 key). Shows:
- Total portfolio value and today's change (£ and %).
- A short list of top movers (best / worst today).
- A small value sparkline if the price history is readily available.

Boundary note: Lifeboard does **not** duplicate the trading dashboard's Monte
Carlo / quant engine. It surfaces a lightweight snapshot. The exact read
mechanism (snapshot file vs. a light call to the running jarvis API vs. a thin
T212 fetch) is finalized in the implementation plan; the panel provider hides it
behind one function.

### 5.3 Feeds
The "what's happening" corner, two sub-sections:
- **Claude projects activity:** recent activity across `~/.claude/projects`
  (project names, last-active time, maybe latest session topic). Read from disk.
- **Global news:** headlines from a few free public RSS feeds chosen in settings,
  fetched server-side. Title, source, time, link.

---

## 6. Configuration & personalization

`config.json` (copied from the `.example`) is the single source of personal
truth. Expected keys:

- `display_name` — greeting on the board.
- `calendar.ical_urls` — one or more Google "secret address in iCal format"
  links. One-time copy-paste; documented with exact click-path in the README.
- `news.feeds` — list of RSS feed URLs (sensible defaults provided).
- `trading.jarvis_dir` — path to the jarvis data (default `~/.jarvis`).
- `goals` — optional free-text goals shown on the board.
- `panels` — ordered list of enabled panels + per-panel options (size, feeds,
  habit definitions, etc.).
- `theme` — selected design (`a` / `b` / `c`) and any per-design preference.

The example template ships with placeholders and safe defaults so the board runs
(with empty/placeholder panels) before Omri fills anything in.

---

## 7. Live fetching & persistence details

- **Calendar (iCal):** engine fetches each `ical_urls` entry, parses the ICS,
  filters to today/upcoming, returns a clean event list. Network/parse failures
  return an error in the panel envelope (card shows "couldn't reach calendar",
  board stays up).
- **News (RSS):** engine fetches each feed, merges, sorts by time, caps count.
  Cached briefly so the board feels instant and feeds aren't hammered.
- **Trading:** read from jarvis data on disk; if unavailable, panel shows a clear
  "no trading data found" state.
- **Claude projects:** read directory metadata from `~/.claude/projects`.
- **User data (to-dos/habits):** written to the local store on every change;
  read on load. Writes are validated and atomic enough that a crash mid-write
  doesn't corrupt the file.

Every panel degrades independently: one failing data source never blanks the
board, it just shows that one card's error state.

---

## 8. Frontends (2–3 distinct designs)

Once the engine and `/api` are verified against real data, build **2–3 distinct
designs** over the shared data layer, then let Omri choose. Candidate directions
(final set decided at build time):
- **Calm & personal** — spacious, soft, a pleasant daily check-in.
- **Mission control** — dense, glowing, everything at once (his maximalist taste).
- **Editorial** — typographic, magazine-like, considered.

All share `lifeboard-core.js`; they differ only in CSS and card layout. Launcher
at `/` links to each; the chosen one is remembered in settings.

---

## 9. Running it

One command in Omri's existing style, then open a link:

```
cd ~/code/lifeboard
python -m uvicorn backend.app:app --port <PORT>
```

…then open `http://localhost:<PORT>`. The README gives the exact copy-paste
steps, the one-time calendar-link setup, and how to pick a design — written for a
non-technical reader, no jargon.

---

## 10. Error handling & testing

- **Error handling:** per-panel isolation (see §7). The engine never crashes on a
  bad feed/link; it returns an error envelope and logs it. Missing settings fall
  back to example defaults with a visible "set this up" hint on the card.
- **Testing:** each provider is unit-tested with sample data (a saved ICS file, a
  saved RSS sample, a fake jarvis snapshot, a temp user-data file) so tests are
  fast and offline. A thin smoke test boots the engine and hits each `/api`
  endpoint. Frontends are verified by loading the board against the real engine.

---

## 11. Future panels (backlog — not built in v1)

Each is "one provider + one card + one settings line" by design:
University (courses, deadlines, assignments) · Email summary · Spotify
now-playing & recent · Weather · Fitness/health · Finances beyond trading
(bank/spend) · Reading/notes · Anything else Omri thinks of.

---

## 12. Open questions / decisions to confirm in the plan

1. **Project name & location.** Working name **Lifeboard**, folder
   `~/code/lifeboard`, settings `~/.lifeboard/`. (Could instead live under the
   "jarvis" umbrella since trading already does. Default: keep Lifeboard separate
   and have it *read* jarvis.)
2. **Trading read mechanism** — snapshot file vs. live jarvis API vs. thin T212
   fetch. Pick the simplest that gives a correct value + day change.
3. **User-data store** — JSON to start, with a clear upgrade path to SQLite if
   to-dos/habits history grows.
4. **Habit definitions** — defined in settings, in the UI, or both. Lean toward
   UI-add with settings as optional seed.
