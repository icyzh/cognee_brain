import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, StringConstraints

from app import cognee_client, store
from app.config import COGNEE_DATASET, COGNEE_SERVICE_URL
from app.ingest import __main__ as ingest
from app.ingest import align
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "cognee_version": version("cognee"),
        "cognee_configured": bool(COGNEE_SERVICE_URL),
        "dataset": COGNEE_DATASET,
        "llm_model": "tenant-managed",
    }


_ingest_lock = asyncio.Lock()


@app.post("/ingest")
async def ingest_seed(reset: bool = False):
    """Batch ingest of data/seed (single-file upload lands in P4). Takes minutes on a fresh graph."""
    if _ingest_lock.locked():
        raise HTTPException(409, "ingest already running")
    async with _ingest_lock:
        stats = await ingest.ingest(reset=reset)
        await _refresh_paths()
        return stats


class AskRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class FeedbackRequest(BaseModel):
    qa_id: int
    helpful: bool
    comment: str | None = Field(None, max_length=1000)


@app.post("/ask")
async def ask(req: AskRequest):
    try:
        return await ask_pipeline.ask(req.question)
    except httpx.TimeoutException:
        raise HTTPException(504, {"error": "knowledge layer timed out", "retryable": True})
    except httpx.HTTPError as e:  # connect / transport errors
        logging.warning("ask transport error: %r", e)
        raise HTTPException(502, {"error": "knowledge layer unreachable", "retryable": True}) from e
    except RuntimeError as e:  # Cognee HTTP errors, raised by cognee_client
        logging.exception("ask failed")
        raise HTTPException(502, {"error": "knowledge layer error", "retryable": True}) from e


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    try:
        store.add_feedback(req.qa_id, req.helpful, req.comment)
    except sqlite3.IntegrityError:  # foreign key: unknown qa_id
        raise HTTPException(404, "unknown qa_id")
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
