import asyncio
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import store
from app.config import COGNEE_DATASET, COGNEE_SERVICE_URL
from app.ingest import __main__ as ingest
from app.ingest import align


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    yield


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
        return await ingest.ingest(reset=reset)


@app.get("/sources")
def sources():
    return store.list_sources()


@app.get("/graph")
async def graph(focus: str | None = None, depth: int = Query(2, ge=1, le=4)):
    return await align.graph(focus, depth, store.get_aliases())
