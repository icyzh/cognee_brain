import sqlite3
from contextlib import closing

from app.config import APP_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    path TEXT PRIMARY KEY,
    ref TEXT NOT NULL,  -- canonical ID, e.g. ADR-007; grounding checks cited refs against this
    type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    data_id TEXT,  -- Cognee data_id from /add; maps retrieved chunks back to this file
    ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS aliases (
    name TEXT PRIMARY KEY,  -- lowercased LLM entity name, e.g. "priya"
    canonical_id TEXT NOT NULL  -- e.g. Person:priya
);
CREATE TABLE IF NOT EXISTS qa_log (
    id INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT,
    response_json TEXT,
    grounded INTEGER,
    tokens_est INTEGER,
    latency_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY,
    qa_id INTEGER NOT NULL REFERENCES qa_log(id),
    helpful INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    new_ref TEXT,
    existing_ref TEXT,
    service TEXT,
    reason TEXT,
    confidence REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS eval_runs (
    id INTEGER PRIMARY KEY,
    grounded_ok INTEGER NOT NULL,
    total INTEGER NOT NULL,
    hallucinated_sources INTEGER NOT NULL,
    ref_recall REAL,
    results_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(APP_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with closing(connect()) as conn, conn:
        conn.executescript(SCHEMA)
