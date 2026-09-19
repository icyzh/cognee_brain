#!/usr/bin/env bash
# Demo state: the seed graph without the live meeting, and app.db as it was when saved.
#   scripts/restore_demo.sh save   # after the final seed ingest + eval: snapshot app.db
#   scripts/restore_demo.sh        # before each run: un-ingest MTG-0402, restore app.db
# Restart the backend afterwards (its path cache is in memory).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
SNAP=../snapshots/demo/app.db

if [ "${1:-}" = "save" ]; then
  mkdir -p "$(dirname "$SNAP")"
  sqlite_backup() { uv run python -c "import sqlite3,sys; s=sqlite3.connect('app.db'); d=sqlite3.connect(sys.argv[1]); s.backup(d); d.close()" "$1"; }
  sqlite_backup "$SNAP"
  echo "saved app.db → snapshots/demo/app.db"
  exit 0
fi

uv run python -m app.ingest --forget ../data/live/MTG-0402.md
if [ -f "$SNAP" ]; then
  cp "$SNAP" app.db
  echo "restored app.db from snapshots/demo/app.db"
else
  echo "no snapshot yet (run: scripts/restore_demo.sh save); kept current app.db"
fi
echo "demo state ready: restart the backend, then drop data/live/MTG-0402.md in the UI"
