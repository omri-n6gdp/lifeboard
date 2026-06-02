#!/bin/bash
# Lifeboard launcher — starts the engine if it isn't running, then opens the board.
# Used by both the Terminal and the Dock app.
DIR="$HOME/code/lifeboard"
PORT=8787
URL="http://localhost:$PORT/"
LOG="$HOME/.lifeboard/server.log"
PIDF="$HOME/.lifeboard/server.pid"
mkdir -p "$HOME/.lifeboard"

# Already running? Just open it.
if curl -s -o /dev/null --max-time 2 "http://localhost:$PORT/api/board"; then
  open "$URL"; exit 0
fi

cd "$DIR" || { osascript -e 'display alert "Lifeboard" message "Could not find ~/code/lifeboard"'; exit 1; }
nohup .venv/bin/python -m uvicorn backend.app:app --port "$PORT" >"$LOG" 2>&1 &
echo $! > "$PIDF"

# Wait until the engine answers (up to ~20s), then open the browser.
for i in $(seq 1 40); do
  curl -s -o /dev/null --max-time 2 "http://localhost:$PORT/api/board" && break
  sleep 0.5
done
open "$URL"
