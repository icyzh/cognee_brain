#!/usr/bin/env bash
# Run backend (:8000) and frontend (:3000) together; Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# kill 0 = the whole process group: uv, the uvicorn reloader and its worker, and npm/next
trap 'trap - EXIT INT TERM; kill 0' EXIT INT TERM
(cd backend && exec uv run uvicorn app.main:app --reload --port 8000) &
cd frontend && npm run dev
