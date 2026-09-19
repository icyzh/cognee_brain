"""Throwaway Phase 0 spike against Cognee Cloud REST (COGNEE_SERVICE_URL / COGNEE_API_KEY).

Run: cd backend && uv run python spike/spike_cloud.py
"""

import json
import os
import time
import uuid
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv()

DS = "spike"
TEXTS = {
    "adr": "ADR-007: Payments service moves from MongoDB to Postgres for ACID ledger guarantees. "
    "Decided in the 2026-03-12 architecture sync. Owner: Priya (Platform Team).",
    "ticket": "TCK-142: Migrate ledger tables to Postgres. Assignee: Priya. Service: payments. Refs: ADR-007.",
    "meeting": "2026-03-12 architecture sync. Attendees: Priya, Marco. Priya argued Postgres gives us "
    "transactions; Marco worried about migration downtime. Decision: ADR-007 accepted.",
}
# S3 fallback: structural edges rendered as text triples
TRIPLES = "Decision:ADR-007 affects Service:payments.\nDecision:ADR-007 owned_by Person:priya.\n"
Q = "Why is payments on Postgres and who owns it?"

c = httpx.Client(
    base_url=os.environ["COGNEE_SERVICE_URL"].rstrip("/") + "/api/v1",
    headers={"X-Api-Key": os.environ["COGNEE_API_KEY"]},
    timeout=600,
)


def section(t):
    print(f"\n===== {t} =====", flush=True)


def ok(r):
    if r.status_code >= 400:
        print("HTTP", r.status_code, r.text[:800])
    r.raise_for_status()
    return r.json()


def add(text, node_set):
    files = {"data": (f"{uuid.uuid4().hex}.txt", text.encode(), "text/plain")}
    return ok(c.post("/add", files=files, data={"datasetName": DS, "node_set": node_set}))


def dataset_id():
    return next(d["id"] for d in ok(c.get("/datasets/")) if d["name"] == DS)


def graph(**params):
    g = ok(c.get(f"/datasets/{dataset_id()}/graph", params=params))
    return g, Counter(n.get("type") or n.get("label") for n in g["nodes"])


def search(**kw):
    t = time.perf_counter()
    r = ok(c.post("/search", json={"query": Q, "searchType": "GRAPH_COMPLETION", "datasets": [DS], **kw}))
    return r, time.perf_counter() - t


section("reset")
for d in ok(c.get("/datasets/")):
    if d["name"] == DS:
        print("delete old dataset", c.delete(f"/datasets/{d['id']}").status_code)

section("S2/S7 add(node_set) + cognify (runInBackground=false)")
t = time.perf_counter()
for src, text in TEXTS.items():
    add(text, [src])
add(TRIPLES, ["structural"])
t_add = time.perf_counter() - t
t = time.perf_counter()
res = ok(c.post("/cognify", json={"datasets": [DS], "runInBackground": False}))
print(f"add(4): {t_add:.1f}s  cognify: {time.perf_counter() - t:.1f}s")
print("cognify resp:", json.dumps(res)[:400])

section("S6/S9 graph read")
g, types = graph()
print("graph keys:", list(g), "nodes:", len(g["nodes"]), "edges:", len(g["edges"]))
print("types:", dict(types))
print("sample node:", json.dumps(g["nodes"][0])[:400])
print("sample edge:", json.dumps(g["edges"][0])[:400])
print("edge labels:", Counter(e.get("label") for e in g["edges"]))

section("S3 did text triples become edges?")
for e in g["edges"]:
    if e.get("label") in ("affects", "owned_by"):
        print("  ", e)

section("S4/S5 search variants")
for kw in ({}, {"verbose": True}, {"onlyContext": True, "contextFormat": "context"}, {"includeReferences": True}):
    r, dt = search(sessionId=f"spike-{uuid.uuid4().hex}", **kw)
    print(f"-- {kw} {dt:.1f}s")
    print(json.dumps(r)[:2000])

section("S5 session leak check (default session, twice)")
search()
r, _ = search(onlyContext=True, contextFormat="prompt")
print("default session prompt has history:", "Previous conversation" in json.dumps(r))

section("S2 nodeName filter")
r = ok(c.post("/search", json={"query": "Who attended?", "searchType": "CHUNKS", "datasets": [DS], "nodeName": ["meeting"]}))
print(json.dumps(r)[:600])

section("S6 focused graph read (seed + depth)")
seed = next((n["id"] for n in g["nodes"] if "adr-007" in json.dumps(n).lower()), None)
if seed:
    g2, _ = graph(seed_node_ids=seed, neighborhood_depth=2)
    print("seed", seed, "-> nodes:", len(g2["nodes"]), "edges:", len(g2["edges"]))

section("S8 dedupe")
n0, e0 = len(g["nodes"]), len(g["edges"])
add(TEXTS["adr"], ["adr"])
ok(c.post("/cognify", json={"datasets": [DS], "runInBackground": False}))
g3, _ = graph()
print(f"before {n0}/{e0} after {len(g3['nodes'])}/{len(g3['edges'])}; data items:", len(ok(c.get(f"/datasets/{dataset_id()}/data"))))
