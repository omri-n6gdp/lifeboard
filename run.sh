#!/usr/bin/env bash
# Lifeboard launcher. Usage: ./run.sh [port]   (default port 8787)
cd "$(dirname "$0")"
PORT="${1:-8787}"
echo "Lifeboard starting — open http://localhost:${PORT} in your browser"
exec .venv/bin/python -m uvicorn backend.app:app --port "$PORT"
