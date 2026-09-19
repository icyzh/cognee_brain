"""The only module that talks to Cognee: Cognee Cloud REST (/api/v1, X-Api-Key).

Not cognee.serve(): the 1.6.0 SDK cloud client drops node_set on add and sessionId
on search (spike S2/S5).
"""

import uuid
from typing import TypedDict

import httpx

from app.config import COGNEE_API_KEY, COGNEE_DATASET, COGNEE_SERVICE_URL


class RawResult(TypedDict):
    answer: str
    triplets: list[tuple[str, str, str]]  # (src, rel, dst)
    chunks: list[dict]  # {text, source_ref}


class GraphDump(TypedDict):
    nodes: list[dict]  # {id, label, type, properties}: cloud shape, ids are UUIDs
    edges: list[dict]  # {source, target, label}


def _client() -> httpx.AsyncClient:
    if not COGNEE_SERVICE_URL:
        raise RuntimeError("COGNEE_SERVICE_URL is not set (backend/.env)")
    return httpx.AsyncClient(
        base_url=f"{COGNEE_SERVICE_URL}/api/v1",
        headers={"X-Api-Key": COGNEE_API_KEY},
        timeout=600,  # synchronous cognify of the whole seed takes minutes
    )


async def _json(resp: httpx.Response):
    if resp.status_code >= 400:
        raise RuntimeError(f"Cognee {resp.request.method} {resp.request.url.path} {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def render_triples(triples: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{s} {r} {o}." for s, r, o in triples)


async def add_text(text: str, node_set: list[str], dataset: str, filename: str | None = None) -> str:
    """/add one document. Returns its data_id (stored in app.db sources)."""
    files = {"data": (filename or f"{uuid.uuid4().hex}.txt", text.encode(), "text/plain")}
    async with _client() as c:
        body = await _json(await c.post("/add", files=files, data={"datasetName": dataset, "node_set": node_set}))
    return body["data_ingestion_info"][0]["data_id"]


async def add_structural(triples: list[tuple[str, str, str]], dataset: str, filename: str | None = None) -> str:
    """Canonical triples rendered as text into /add with node_set=["structural"]. Returns the data_id."""
    return await add_text(render_triples(triples), ["structural"], dataset, filename)


async def build(dataset: str) -> None:
    """/cognify with runInBackground=false."""
    async with _client() as c:
        body = await _json(await c.post("/cognify", json={"datasets": [dataset], "runInBackground": False}))
    bad = [r.get("status") for r in body.values() if r.get("status") != "PipelineRunCompleted"]
    if bad:
        raise RuntimeError(f"cognify did not complete: {bad}")


async def dataset_id(dataset: str = COGNEE_DATASET) -> str | None:
    async with _client() as c:
        return next((d["id"] for d in await _json(await c.get("/datasets/")) if d["name"] == dataset), None)


async def ensure_dataset(dataset: str) -> None:
    """Idempotent create. Parallel /add calls racing to create a new dataset get 409 permission errors."""
    async with _client() as c:
        await _json(await c.post("/datasets/", json={"name": dataset}))


async def delete_dataset(dataset: str) -> None:
    if ds := await dataset_id(dataset):
        async with _client() as c:
            await _json(await c.delete(f"/datasets/{ds}"))


async def delete_data(data_id: str, dataset: str) -> None:
    if ds := await dataset_id(dataset):
        async with _client() as c:
            resp = await c.delete(f"/datasets/{ds}/data/{data_id}")
        if resp.status_code not in (200, 204, 404):
            await _json(resp)


async def graph_dump(dataset: str = COGNEE_DATASET, **params) -> GraphDump:
    """/datasets/{id}/graph; params: seed_node_ids, neighborhood_depth, max_nodes."""
    ds = await dataset_id(dataset)
    if not ds:
        return {"nodes": [], "edges": []}
    async with _client() as c:
        return await _json(await c.get(f"/datasets/{ds}/graph", params=params))


async def ask(question: str) -> RawResult:
    """/search GRAPH_COMPLETION, verbose, fresh sessionId (spike S5). P2."""
    raise NotImplementedError
