import asyncio
import logging
import re
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import httpx
import yaml
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from app import cognee_client, store
from app.analysis import timeline as decision_timeline
from app.config import COGNEE_DATASET, COGNEE_SERVICE_URL, DATA_DIR
from app.ingest import __main__ as ingest
from app.ingest import align, loaders, structural
from app.logs import jlog, request_id
from app.query import ask as ask_pipeline
from app.query import paths


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    await _refresh_paths()
    yield


async def _refresh_paths() -> None:
    try:
        await asyncio.wait_for(paths.refresh(), 30)
    except Exception as e:  # no graph yet / cloud slow or unreachable: /ask still answers, just without a path
        logging.warning("path cache not built: %s", e)


app = FastAPI(title="Cognee Brain API", lifespan=lifespan)


@app.middleware("http")
async def request_log(request: Request, call_next):
    """One JSON line per request (id, endpoint, status, latency); /ask adds grounded + tokens itself."""
    rid = re.sub(r"[^A-Za-z0-9-]", "", request.headers.get("x-request-id", ""))[:64] or uuid.uuid4().hex[:12]
    request_id.set(rid)
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # anything unhandled: log it, never send a stack trace to the client
        logging.exception("unhandled error rid=%s", rid)
        response = JSONResponse({"detail": {"error": "internal error", "retryable": False, "request_id": rid}}, 500)
    response.headers["x-request-id"] = rid
    jlog("request", method=request.method, path=request.url.path, status=response.status_code,
         latency_ms=round((time.perf_counter() - t0) * 1000))
    return response


# Added after the logging middleware = outermost, so even its catch-all 500 carries CORS headers
# (otherwise the browser hides the {error, retryable} body behind a network error).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)


@app.get("/health")
def health():
    """Pre-demo check: Cognee configured, graph loaded (path cache), last eval score."""
    ev = store.latest_eval("decision_brain")
    return {
        "status": "ok",
        "cognee_version": version("cognee"),
        "cognee_configured": bool(COGNEE_SERVICE_URL),
        "dataset": COGNEE_DATASET,
        "llm_model": "tenant-managed",
        "graph": {"nodes": paths._cache.get("nodes"), "verified_edges": sum(map(len, paths._cache.get("adj", {}).values())) // 2},
        "last_eval": ev and {"grounded": f"{ev['grounded_ok']}/{ev['total']}", "path": f"{ev.get('path_ok')}/{ev.get('path_total')}", "run_at": ev["run_at"]},
        "ingest_building": _ingest_lock.locked(),
    }


_ingest_lock = asyncio.Lock()


MAX_UPLOAD = 1_000_000


@app.post("/ingest")
async def ingest_route(reset: bool = False, file: UploadFile | None = File(None)):
    """No file: batch ingest of data/seed (minutes on a fresh graph). With a multipart `file`: live ingest
    of one ADR/meeting/ticket into data/live + contradiction checks → IngestResult."""
    if _ingest_lock.locked():
        raise HTTPException(409, "ingest already running (a live upload's graph build takes ~30 s)")
    await _ingest_lock.acquire()
    handed_off = False
    try:
        if file is None:
            return await ingest.ingest(reset=reset)
        else:
            name = Path(file.filename or "").name  # never trust client paths
            if name.startswith(".") or not name.endswith((".md", ".json")):
                raise HTTPException(400, "upload a .md or .json document")
            data = await file.read(MAX_UPLOAD + 1)
            if len(data) > MAX_UPLOAD:
                raise HTTPException(413, "file too large")
            dest = DATA_DIR / "live" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(f".upload-{name}")  # dotfiles are never loaded as data
            tmp.write_bytes(data)
            try:
                recs = loaders.load(tmp)
            except (ValueError, yaml.YAMLError, KeyError):  # JSONDecodeError is a ValueError
                recs = []
            if not recs:
                tmp.unlink()
                raise HTTPException(400, "not a recognisable document (needs frontmatter/JSON with an id)")
            if recs[0]["ref"] in {r["ref"] for r in loaders.load(DATA_DIR / "seed")}:
                tmp.unlink()
                raise HTTPException(409, f"{recs[0]['ref']} is a seed document; uploads can't replace it")
            previous = dest.read_bytes() if dest.exists() else None
            tmp.replace(dest)
            try:
                result, finish = await ingest.ingest_file(dest)
            except BaseException as e:  # never leave a half-ingested upload on disk as "truth"
                if previous is None:
                    dest.unlink(missing_ok=True)
                else:
                    dest.write_bytes(previous)
                if not isinstance(e, Exception):
                    raise
                logging.exception("live ingest failed")
                raise HTTPException(502, {"error": "ingest or contradiction check failed", "retryable": True}) from e
            task = asyncio.create_task(_finish_in_background(finish))
            _background.add(task)
            task.add_done_callback(_background.discard)
            handed_off = True
            return result
    finally:
        if not handed_off:
            _ingest_lock.release()


_background: set[asyncio.Task] = set()


async def _finish_in_background(finish) -> None:
    """cognify + path refresh for a live upload; holds the ingest lock until the graph is built."""
    try:
        stats = await finish
        logging.info("live ingest graph built: %s nodes, showcase_missing=%s", stats["nodes"], stats["showcase_missing"])
    except Exception:
        logging.exception("live ingest graph build failed; the file stays unrecorded, so a re-upload retries")
    finally:
        _ingest_lock.release()


@app.get("/eval/latest")
def eval_latest():
    """Latest eval run per variant: ours vs the raw-Cognee baseline (uv run python -m eval.run_eval [--baseline])."""
    return {v: store.latest_eval(v) for v in ("decision_brain", "cognee_prompted", "raw_cognee")}


@app.get("/ingest/status")
def ingest_status():
    return {"building": _ingest_lock.locked()}


@app.get("/alerts")
def alerts():
    """Newest first; `people` = owner of the contradicted decision + whoever raised the new claim."""
    records = {r["ref"]: r for r in loaders.load(DATA_DIR)}
    out = []
    for a in store.list_alerts():
        owner = records.get(a["existing_ref"] or "", {}).get("meta", {}).get("owner")
        raisers = [p.get("by") for p in structural._list(records.get(a["new_ref"] or "", {}).get("meta", {}).get("proposals"))]
        out.append(a | {"people": list(dict.fromkeys(p for p in [owner, *raisers] if p))})
    return out


@app.get("/timeline")
def timeline(service: str, as_of: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")):
    """Decision history of one service (ID or alias: "svc-payments", "payments"): validity intervals,
    which decisions were in force on `as_of` (default today), and open contradiction proposals."""
    cid = align.canonical_id(service, store.get_aliases()) or ""
    if not cid.startswith("Service:"):
        raise HTTPException(404, f"unknown service {service!r}")
    svc = cid.split(":", 1)[1]
    return {"service": svc, "as_of": as_of, "entries": decision_timeline.for_service(svc, loaders.load(DATA_DIR), store.list_alerts(), as_of)}


class AskRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class FeedbackRequest(BaseModel):
    qa_id: int
    helpful: bool
    comment: str | None = Field(None, max_length=1000)


@app.post("/ask")
async def ask(req: AskRequest, raw: bool = False):
    """raw=true: plain Cognee on the same question, for the side-by-side demo.

    Cached fallback (P5): if this question was answered before, the live call gets 20 s; on a timeout or
    Cognee error the last answer is served, flagged `cached: true` (and logged), never hidden.
    """
    fallback = None if raw else ask_pipeline.cached(req.question)
    t0 = time.perf_counter()
    try:
        if raw:
            return await ask_pipeline.ask_raw(req.question)
        return await asyncio.wait_for(ask_pipeline.ask(req.question), 20 if fallback else None)
    except Exception as e:
        if fallback:  # any failure, not just Cognee errors: the demo question still answers
            jlog("ask_fallback", reason=repr(e), qa_id=fallback.get("qa_id"))
            return fallback | {"latency_ms": round((time.perf_counter() - t0) * 1000)}  # the real wait
        if not isinstance(e, (TimeoutError, httpx.HTTPError, RuntimeError)):
            raise
        if isinstance(e, (TimeoutError, httpx.TimeoutException)):
            raise HTTPException(504, {"error": "knowledge layer timed out", "retryable": True}) from e
        if isinstance(e, httpx.HTTPError):  # connect / transport errors
            logging.warning("ask transport error: %r", e)
            raise HTTPException(502, {"error": "knowledge layer unreachable", "retryable": True}) from e
        logging.exception("ask failed")  # Cognee HTTP errors, raised by cognee_client as RuntimeError
        raise HTTPException(502, {"error": "knowledge layer error", "retryable": True}) from e


@app.get("/history")
def history(limit: int = Query(6, ge=1, le=20)):
    """Recent grounded answers, one per question: shown on the Ask page before anything is asked."""
    return store.recent_answers(limit)


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    try:
        store.add_feedback(req.qa_id, req.helpful, req.comment)
    except sqlite3.IntegrityError:  # foreign key: unknown qa_id
        raise HTTPException(404, "unknown qa_id") from None
    return {"ok": True}


@app.get("/sources")
def sources():
    return store.list_sources()


@app.get("/graph/cognee")
async def graph_cognee(full: bool = False, query: str | None = None):
    """Proxies Cognee's rendered graph page so the API key stays server-side; the frontend iframes it."""
    params = {"full": full} | ({"query": query} if query else {})
    try:
        return HTMLResponse(await cognee_client.visualize_html(**params))
    except RuntimeError as e:
        logging.exception("visualize failed")
        raise HTTPException(502, {"error": "knowledge layer error", "retryable": True}) from e


@app.get("/graph")
async def graph(focus: str | None = None, depth: int = Query(2, ge=1, le=4)):
    return await align.graph(focus, depth, store.get_aliases())
