#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

(cd backend && uv sync && { [ -f .env ] || cp .env.example .env; })
(cd frontend && npm install && { [ -f .env.local ] || cp .env.local.example .env.local; })

echo "Ready. Fill COGNEE_* (and LLM_* for contradiction alerts) in backend/.env, then:"
echo "  cd backend && uv run python -m app.ingest --reset   # build the graph once (~5 min)"
echo "  scripts/dev.sh                                      # backend :8000 + frontend :3000"
