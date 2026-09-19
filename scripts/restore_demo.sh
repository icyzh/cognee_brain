#!/usr/bin/env bash
# Demo state: the seed graph without the live meeting, and app.db as it was when saved.
#   scripts/restore_demo.sh save   # after the final seed ingest + eval: snapshot app.db
#   scripts/restore_demo.sh        # before each run (backend stopped): restore app.db, un-ingest MTG-0402
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
SNAP=../snapshots/demo/app.db
# sqlite's backup API takes the proper locks (a plain cp can copy a half-written db)
backup() { uv run python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" "$1" "$2"; }

if curl -sf -m 2 localhost:8000/health >/dev/null; then
  echo "stop the backend first (it holds app.db and an in-memory path cache)" >&2
  exit 1
fi

if [ "${1:-}" = "save" ]; then
  [ -f app.db ] || { echo "no backend/app.db to save: run the ingest first" >&2; exit 1; }
  mkdir -p "$(dirname "$SNAP")"
  backup app.db "$SNAP"
  echo "saved app.db → snapshots/demo/app.db"
  exit 0
fi

if [ -f "$SNAP" ]; then
  backup "$SNAP" app.db
  echo "restored app.db from snapshots/demo/app.db"
else
  echo "no snapshot yet (run: scripts/restore_demo.sh save); kept current app.db"
fi
# after the restore: a Cognee hiccup here must not leave app.db half-reset
uv run python -m app.ingest --forget ../data/live/MTG-0402.md || echo "WARNING: --forget failed (Cognee reachable?); re-run before the demo" >&2
echo "demo state ready: start the backend (scripts/dev.sh), then drop data/live/MTG-0402.md in the UI"
