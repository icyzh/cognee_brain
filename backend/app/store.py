import json
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
    variant TEXT NOT NULL,  -- 'decision_brain' | 'cognee_prompted' | 'raw_cognee' (baselines)
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
        conn.execute("DELETE FROM alerts")


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


def add_alert(kind: str, new_ref: str | None, existing_ref: str | None, service: str | None, reason: str, confidence: float | None) -> dict:
    with closing(connect()) as conn, conn:
        row_id = conn.execute(
            "INSERT INTO alerts (kind, new_ref, existing_ref, service, reason, confidence) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, new_ref, existing_ref, service, reason, confidence),
        ).lastrowid
        return dict(conn.execute("SELECT * FROM alerts WHERE id = ?", (row_id,)).fetchone())


def replace_stale_alerts(rows: list[tuple]) -> None:
    """rows: (new_ref, existing_ref, service, reason)."""
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM alerts WHERE kind = 'stale'")
        conn.executemany("INSERT INTO alerts (kind, new_ref, existing_ref, service, reason) VALUES ('stale', ?, ?, ?, ?)", rows)


def list_alerts() -> list[dict]:
    with closing(connect()) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM alerts ORDER BY created_at DESC, id DESC")]


def clear_contradictions(new_ref: str) -> None:
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM alerts WHERE kind = 'contradiction' AND new_ref = ?", (new_ref,))


def contradictions_for(refs: list[str], services: list[str] = ()) -> list[dict]:
    """Open contradiction alerts on any of these decisions, or on any of these services."""
    if not refs and not services:
        return []
    ph = lambda xs: ",".join("?" * len(xs)) or "NULL"  # noqa: E731
    with closing(connect()) as conn:
        q = (f"SELECT * FROM alerts WHERE kind = 'contradiction' "
             f"AND (existing_ref IN ({ph(refs)}) OR service IN ({ph(services)})) ORDER BY id")
        return [dict(r) for r in conn.execute(q, [*refs, *services])]


def delete_source(path: str) -> None:
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM sources WHERE path = ?", (path,))


def add_eval_run(variant: str, summary: dict, rows: list[dict]) -> None:
    extra = {k: v for k, v in summary.items() if k not in ("grounded_ok", "total", "hallucinated_sources", "ref_recall")}
    with closing(connect()) as conn, conn:
        conn.execute(
            "INSERT INTO eval_runs (variant, grounded_ok, total, hallucinated_sources, ref_recall, results_json) VALUES (?, ?, ?, ?, ?, ?)",
            (variant, summary["grounded_ok"], summary["total"], summary["hallucinated_sources"], summary["ref_recall"],
             json.dumps(extra | {"results": rows})),
        )


def latest_eval(variant: str) -> dict | None:
    with closing(connect()) as conn:
        r = conn.execute("SELECT * FROM eval_runs WHERE variant = ? ORDER BY id DESC LIMIT 1", (variant,)).fetchone()
    if not r:
        return None
    extra = json.loads(r["results_json"] or "{}")
    return {"run_at": r["created_at"], "grounded_ok": r["grounded_ok"], "total": r["total"],
            "hallucinated_sources": r["hallucinated_sources"], "ref_recall": r["ref_recall"], **extra}


def recent_answers(limit: int = 6) -> list[dict]:
    """Latest grounded /ask response per distinct question, newest first (the Ask page's start screen)."""
    with closing(connect()) as conn:
        rows = conn.execute(
            """SELECT question, response_json, created_at FROM qa_log
               WHERE id IN (SELECT MAX(id) FROM qa_log WHERE grounded = 1 GROUP BY lower(trim(question)))
               ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()
    return [{"question": r["question"], "asked_at": r["created_at"], "response": json.loads(r["response_json"])} for r in rows]


def last_answer(question: str) -> dict | None:
    """Most recent completed /ask response for this question (the cached fallback, P5)."""
    with closing(connect()) as conn:
        r = conn.execute(
            "SELECT id, response_json FROM qa_log WHERE lower(trim(question)) = lower(trim(?)) ORDER BY id DESC LIMIT 1",
            (question,),
        ).fetchone()
    return json.loads(r["response_json"]) | {"qa_id": r["id"]} if r else None  # qa_id is assigned after the JSON is stored
