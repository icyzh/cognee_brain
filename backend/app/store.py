import sqlite3
from contextlib import closing

from app.config import APP_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    path TEXT PRIMARY KEY,
    ref TEXT NOT NULL,  -- canonical ID, e.g. ADR-007; grounding checks cited refs against this
    type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    data_id TEXT,  -- Cognee data_id from /add; used to delete/replace this file in Cognee (evidence maps by ref)
    triples_data_id TEXT,  -- data_id of this file's structural triples doc
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
    variant TEXT NOT NULL,  -- 'decision_brain' | 'raw_cognee' (baseline)
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
        if "triples_data_id" not in {r[1] for r in conn.execute("PRAGMA table_info(sources)")}:
            conn.execute("ALTER TABLE sources ADD COLUMN triples_data_id TEXT")  # app.db from Phase 0


def get_source(path: str) -> sqlite3.Row | None:
    with closing(connect()) as conn:
        return conn.execute("SELECT * FROM sources WHERE path = ?", (path,)).fetchone()


def upsert_source(
    path: str, ref: str, type: str, content_hash: str, data_id: str | None, triples_data_id: str | None
) -> None:
    with closing(connect()) as conn, conn:
        conn.execute(
            """INSERT INTO sources (path, ref, type, content_hash, data_id, triples_data_id) VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET ref=excluded.ref, type=excluded.type, content_hash=excluded.content_hash,
                 data_id=excluded.data_id, triples_data_id=excluded.triples_data_id, ingested_at=CURRENT_TIMESTAMP""",
            (path, ref, type, content_hash, data_id, triples_data_id),
        )


def list_sources() -> list[dict]:
    with closing(connect()) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM sources ORDER BY type, ref")]


def set_aliases(mapping: dict[str, str]) -> None:
    with closing(connect()) as conn, conn:
        conn.executemany(  # OR IGNORE: the first mapping wins; a later single-file ingest can't re-map a name
            "INSERT OR IGNORE INTO aliases (name, canonical_id) VALUES (?, ?)",
            [(name.lower(), cid) for name, cid in mapping.items()],
        )


def get_aliases() -> dict[str, str]:
    with closing(connect()) as conn:
        return dict(conn.execute("SELECT name, canonical_id FROM aliases").fetchall())


def reset_ingest_state() -> None:
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM sources")
        conn.execute("DELETE FROM aliases")


def get_source_by_ref(ref: str) -> sqlite3.Row | None:
    with closing(connect()) as conn:
        return conn.execute("SELECT * FROM sources WHERE ref = ? ORDER BY ingested_at DESC", (ref,)).fetchone()


def log_qa(question: str, answer: str, response_json: str, grounded: bool, tokens_est: int, latency_ms: int) -> int:
    with closing(connect()) as conn, conn:
        return conn.execute(
            "INSERT INTO qa_log (question, answer, response_json, grounded, tokens_est, latency_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (question, answer, response_json, int(grounded), tokens_est, latency_ms),
        ).lastrowid


def add_feedback(qa_id: int, helpful: bool, comment: str | None = None) -> None:
    with closing(connect()) as conn, conn:
        conn.execute("INSERT INTO feedback (qa_id, helpful, comment) VALUES (?, ?, ?)", (qa_id, int(helpful), comment))
