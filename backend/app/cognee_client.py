"""The only module that talks to Cognee: Cognee Cloud REST (/api/v1, X-Api-Key).

Not cognee.serve(): the 1.6.0 SDK cloud client drops node_set on add and sessionId
on search (spike S2/S5).
"""

import asyncio
import mimetypes
import re
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
    return await add_file(text.encode(), filename or f"{uuid.uuid4().hex}.txt", node_set, dataset, "text/plain")


async def add_file(data: bytes, filename: str, node_set: list[str], dataset: str, content_type: str | None = None) -> str:
    """/add raw bytes; Cognee picks the loader by extension (pdf, images, audio, video...).
    The TextDocument is named after the file stem, which is how evidence maps back to the source."""
    files = {"data": (filename, data, content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream")}
    async with _client() as c:
        for attempt in range(3):  # Cloud drops connections under parallel load (seen: 409 "connection was closed")
            try:
                resp = await c.post("/add", files=files, data={"datasetName": dataset, "node_set": node_set})
                if resp.status_code not in (409, 429, 500, 502, 503, 504) or attempt == 2:
                    break
            except httpx.TransportError:
                if attempt == 2:
                    raise
            await asyncio.sleep(2 * (attempt + 1))
        body = await _json(resp)
    return body["data_ingestion_info"][0]["data_id"]


async def add_structural(triples: list[tuple[str, str, str]], dataset: str, filename: str | None = None, facts: list[str] = ()) -> str:
    """Canonical triples (+ metadata fact sentences) as text into /add with node_set=["structural"]. Returns the data_id."""
    return await add_text("\n".join([render_triples(triples), *facts]), ["structural"], dataset, filename)


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


async def visualize_html(dataset: str = COGNEE_DATASET, **params) -> str:
    """/visualize: Cognee's own interactive page (Graph/Schema/Memory/Semantic tabs); params: full, query, max_nodes."""
    ds = await dataset_id(dataset)
    if not ds:
        raise RuntimeError(f"dataset {dataset!r} not found")
    async with _client() as c:
        resp = await c.get("/visualize", params={"dataset_id": ds, **params})
    if resp.status_code >= 400:
        await _json(resp)  # raises with the response body
    return resp.text


NOT_FOUND = "NOT_FOUND"
SYSTEM_PROMPT = (
    "Answer only from the provided context. Cite decision, meeting and ticket IDs exactly as written "
    "(e.g. ADR-007, MTG-0312, TCK-142) and name the people involved. If asked who to talk to, name the person "
    f"and their team. Answer in 2-4 sentences. If the context does not contain the answer, reply with exactly: {NOT_FOUND}"
)
# cognify output uses typographic dashes/spaces ("ADR\u2011007"); normalize before any ID matching.
_TYPO = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u00a0": " ", "\u202f": " "})
_HEADER = re.compile(r"^\[(?:DECISION|MEETING|TICKET) ([A-Z]+-\d+)")


def clean(text: str) -> str:
    return (text or "").translate(_TYPO)


async def ask(question: str, dataset: str = COGNEE_DATASET, timeout: float = 40, system_prompt: str | None = SYSTEM_PROMPT) -> RawResult:
    """/search GRAPH_COMPLETION, verbose, fresh sessionId (S5: the default session leaks earlier Q&A).

    chunks[].source_ref = the ref of the file the chunk came from: the TextDocument is named after our
    upload filename ("ADR-007", "ADR-007.triples"), with the text header as fallback.
    system_prompt=None sends Cognee's default prompt (the P4 raw-Cognee baseline).
    """
    payload = {
        "query": question, "searchType": "GRAPH_COMPLETION", "datasets": [dataset], "verbose": True,
        "sessionId": uuid.uuid4().hex,
    }
    if system_prompt:
        payload["systemPrompt"] = system_prompt
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout  # overall budget, retry included (the frontend aborts at 45 s)
    async with _client() as c:
        for attempt in range(2):  # one retry on rate limit / server error, only if it still fits
            resp = await c.post("/search", json=payload, timeout=max(1.0, deadline - loop.time()))
            if resp.status_code not in (429, 500, 502, 503, 504) or attempt or deadline - loop.time() < 12:
                break
            await asyncio.sleep(1)
        try:
            body = (await _json(resp))[0]
            return _parse(body)
        except (KeyError, IndexError, TypeError, ValueError) as e:  # response shape drift
            raise RuntimeError(f"unexpected /search response: {e!r}") from e


def _parse(body: dict) -> RawResult:
    doc_of: dict[str, str] = {}
    chunks: dict[str, str] = {}
    triplets = []
    for o in body.get("objects_result") or []:
        a, b = o["node1"], o["node2"]
        ta, tb = a["node_attributes"].get("type"), b["node_attributes"].get("type")
        for x, tx, y, ty in ((a, ta, b, tb), (b, tb, a, ta)):
            if tx == "DocumentChunk":
                chunks[x["node_id"]] = clean(x["node_attributes"].get("text"))
                if ty == "TextDocument" and y["node_attributes"].get("name"):
                    doc_of[x["node_id"]] = y["node_attributes"]["name"]
        if ta == tb == "Entity":
            triplets.append((clean(a["node_attributes"].get("name")), o["attributes"].get("relationship_name"), clean(b["node_attributes"].get("name"))))
    out_chunks = []
    for cid, text in chunks.items():
        ref = doc_of.get(cid) or ((m := _HEADER.match(text)) and m.group(1)) or None
        out_chunks.append({"text": text, "source_ref": ref})
    answer = body.get("text_result") or [""]
    return {"answer": clean(answer[0] if isinstance(answer, list) else answer), "triplets": triplets, "chunks": out_chunks}
