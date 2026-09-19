#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

(cd backend && uv sync)
(cd frontend && npm install)

echo "Ready. Run backend: cd backend && uv run uvicorn app.main:app --reload --port 8000"
echo "       frontend: cd frontend && npm run dev"
