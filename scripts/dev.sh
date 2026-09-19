#!/usr/bin/env bash
# Run backend (:8000) and frontend (:3000) together; Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

(cd backend && uv run uvicorn app.main:app --reload --port 8000) &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT INT TERM
cd frontend && npm run dev
