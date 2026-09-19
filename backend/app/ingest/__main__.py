"""uv run python -m app.ingest [--reset] [path]"""

import argparse
import asyncio
import time
from collections import Counter
from pathlib import Path

from app import cognee_client, store
from app.config import COGNEE_DATASET, DATA_DIR
from app.ingest import align, loaders, semantic, structural

# Showcase path + stale link: ingestion fails if cognify drops any of these (P1 exit gate).
SHOWCASE = [
    ("ADR-007", "affects", "svc-payments"),
    ("ADR-007", "decided_in", "MTG-0312"),
    ("MTG-0312", "attended_by", "priya"),
    ("priya", "member_of", "platform"),
    ("ADR-007", "supersedes", "ADR-003"),
    ("TCK-142", "references", "ADR-007"),
]
PARALLEL = 5


async def _ingest_record(rec: dict, dataset: str, sem: asyncio.Semaphore) -> tuple:
    """Adds one file to Cognee; returns its sources row, written only after cognify succeeds."""
    async with sem:
        old = store.get_source(rec["path"])
        for stale in (old["data_id"], old["triples_data_id"]) if old else ():
            if stale:  # file changed: drop its previous version from Cognee
                await cognee_client.delete_data(stale, dataset)
        triples_id = None
        if t := structural.triples(rec):
            triples_id = await cognee_client.add_structural(t, dataset, f"{rec['ref']}.triples.txt")
        data_id = None
        if text := semantic.render(rec):
            data_id = await cognee_client.add_text(text, [rec["type"]], dataset, f"{rec['ref']}.txt")
        return rec["path"], rec["ref"], rec["type"], rec["hash"], data_id, triples_id


async def ingest(root: Path = DATA_DIR / "seed", reset: bool = False, dataset: str = COGNEE_DATASET) -> dict:
    t0 = time.perf_counter()
    store.init_db()
    if reset:
        await cognee_client.delete_dataset(dataset)
        store.reset_ingest_state()

    records = loaders.load(root)
    aliases = align.seed_aliases(records)
    store.set_aliases(aliases)
    aliases = store.get_aliases()  # includes names from earlier ingests (single-file mode)

    todo = [r for r in records if (old := store.get_source(r["path"])) is None or old["content_hash"] != r["hash"]]
    if todo:
        await cognee_client.ensure_dataset(dataset)
        sem = asyncio.Semaphore(PARALLEL)
        async with asyncio.TaskGroup() as tg:  # first failure cancels the rest
            tasks = [tg.create_task(_ingest_record(r, dataset, sem)) for r in todo]
        await cognee_client.build(dataset)
        # Recorded only now: a failed add/cognify leaves these files "unseen", so the next run retries.
        # Re-adding is safe: Cognee derives data_id from content, so it returns the same id.
        for t in tasks:
            store.upsert_source(*t.result())

    graph = await cognee_client.graph_dump(dataset)
    missing = align.missing_edges(SHOWCASE, graph, aliases)
    # ponytail: the retry doc isn't tracked in sources, so it outlives an edited ADR until --reset.
    if missing and todo:  # one retry: re-add just the dropped triples
        await cognee_client.add_structural(missing, dataset, "showcase-retry.triples.txt")
        await cognee_client.build(dataset)
        graph = await cognee_client.graph_dump(dataset)
        missing = align.missing_edges(SHOWCASE, graph, aliases)

    all_expected = [t for r in records for t in structural.triples(r)]
    return {
        "files": len(records),
        "ingested": len(todo),
        "skipped": len(records) - len(todo),
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "node_types": dict(Counter(n["type"] for n in graph["nodes"])),
        "structural_edges_found": f"{len(all_expected) - len(align.missing_edges(all_expected, graph, aliases))}/{len(all_expected)}",
        "aligned_entities": len(align.matched_entities(graph, aliases)),
        "showcase_missing": missing,
        "took_s": round(time.perf_counter() - t0, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.ingest")
    ap.add_argument("--reset", action="store_true", help="delete the Cognee dataset and clear sources/aliases first")
    ap.add_argument("path", nargs="?", type=Path, default=DATA_DIR / "seed")
    args = ap.parse_args()
    stats = asyncio.run(ingest(args.path, args.reset))
    for k, v in stats.items():
        print(f"{k:24} {v}")
    if stats["showcase_missing"]:
        raise SystemExit(f"FAIL: showcase edges missing from the graph: {stats['showcase_missing']}")


if __name__ == "__main__":
    main()
