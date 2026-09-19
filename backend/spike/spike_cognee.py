"""Throwaway Phase 0 spike: answers S1-S9 against the installed cognee.

Run: cd backend && uv run python spike/spike_cognee.py
"""

import asyncio
import time
from collections import Counter

from dotenv import load_dotenv

load_dotenv()

import cognee  # noqa: E402
from cognee import SearchType  # noqa: E402
from cognee.infrastructure.databases.graph import get_graph_engine  # noqa: E402
from cognee.infrastructure.engine import DataPoint  # noqa: E402
from cognee.tasks.storage import add_data_points  # noqa: E402

TEXTS = {
    "adr": "ADR-007: Payments service moves from MongoDB to Postgres for ACID ledger guarantees. "
    "Decided in the 2026-03-12 architecture sync. Owner: Priya (Platform Team).",
    "ticket": "TCK-142: Migrate ledger tables to Postgres. Assignee: Priya. Service: payments. Refs: ADR-007.",
    "meeting": "2026-03-12 architecture sync. Attendees: Priya, Marco. Priya argued Postgres gives us "
    "transactions; Marco worried about migration downtime. Decision: ADR-007 accepted.",
}
Q = "Why is payments on Postgres and who owns it?"


class Person(DataPoint):
    name: str
    metadata: dict = {"index_fields": ["name"]}


class Service(DataPoint):
    name: str
    metadata: dict = {"index_fields": ["name"]}


class Decision(DataPoint):
    name: str
    affects: Service | None = None
    owner: Person | None = None
    metadata: dict = {"index_fields": ["name"]}


def section(title):
    print(f"\n===== {title} =====")


def shape(results, n=600):
    for r in results:
        print(type(r).__name__, "->", repr(r)[:n])


async def graph_counts():
    nodes, edges = await (await get_graph_engine()).get_graph_data()
    return Counter(p.get("type") for _, p in nodes), len(nodes), len(edges), nodes, edges


async def main():
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    section("S1/S2/S7 add(node_set) + cognify")
    t = time.perf_counter()
    for src, text in TEXTS.items():
        await cognee.add(text, dataset_name="spike", node_set=[src])
    t_add = time.perf_counter() - t
    t = time.perf_counter()
    await cognee.cognify(datasets=["spike"])
    print(f"add: {t_add:.1f}s  cognify(3 docs): {time.perf_counter() - t:.1f}s")

    section("S3 add_data_points with relationship fields")
    priya = Person(name="Person:priya")
    payments = Service(name="Service:payments")
    adr = Decision(name="Decision:ADR-007", affects=payments, owner=priya)
    await add_data_points([adr])
    types, n_nodes, n_edges, nodes, edges = await graph_counts()
    print("types:", dict(types), "nodes:", n_nodes, "edges:", n_edges)
    print("structural edges:", [e[2] for e in edges if e[2] in ("affects", "owner")])

    section("S4/S5/S7 search GRAPH_COMPLETION variants")
    for kw in ({}, {"verbose": True}, {"only_context": True}, {"include_references": True}):
        t = time.perf_counter()
        res = await cognee.search(Q, query_type=SearchType.GRAPH_COMPLETION, datasets=["spike"], **kw)
        print(f"-- search {kw} {time.perf_counter() - t:.1f}s")
        shape(res, 1500)

    section("S4 recall")
    t = time.perf_counter()
    res = await cognee.recall(Q, query_type=SearchType.GRAPH_COMPLETION, datasets=["spike"])
    print(f"recall {time.perf_counter() - t:.1f}s")
    shape(res, 1500)

    section("S2 node_name filter (node_set scoping)")
    res = await cognee.search(
        "Who was at the meeting?", query_type=SearchType.CHUNKS, datasets=["spike"], node_name=["meeting"]
    )
    shape(res, 300)

    section("S8 dedupe: re-add same content")
    await cognee.add(TEXTS["adr"], dataset_name="spike", node_set=["adr"])
    await cognee.cognify(datasets=["spike"])
    types2, n2, e2, *_ = await graph_counts()
    print(f"before: {n_nodes} nodes/{n_edges} edges  after: {n2}/{e2}")
    data = await cognee.datasets.list_data((await cognee.datasets.list_datasets())[0].id)
    print("data items in dataset:", len(data))

    section("S9 node types")
    print(dict(types2))


if __name__ == "__main__":
    asyncio.run(main())
