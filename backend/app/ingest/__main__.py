"""uv run python -m app.ingest [--reset] [path]  |  uv run python -m app.ingest --forget PATH"""

import argparse
import asyncio
import logging
import time
from collections import Counter
from collections.abc import Coroutine
from pathlib import Path

from app import cognee_client, store
from app.analysis import contradictions
from app.config import COGNEE_DATASET, DATA_DIR
from app.ingest import align, loaders, semantic, structural
from app.query import paths

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
        async def none():
            return None

        t, text = structural.triples(rec), semantic.render(rec)
        triples_id, data_id = await asyncio.gather(
            cognee_client.add_structural(t, dataset, f"{rec['ref']}.triples.txt", structural.facts(rec)) if t else none(),
            cognee_client.add_text(text, [rec["type"]], dataset, f"{rec['ref']}.txt") if text else none(),
        )
        return rec["path"], rec["ref"], rec["type"], rec["hash"], data_id, triples_id


async def _prepare(root: Path, reset: bool, dataset: str) -> tuple[list, dict, list, list]:
    """Load records, sync aliases, and /add every new or changed file. Returns (records, aliases, todo, rows)."""
    store.init_db()
    if reset:
        await cognee_client.delete_dataset(dataset)
        store.reset_ingest_state()
    records = loaders.load(root)
    store.set_aliases(align.seed_aliases(records))
    aliases = store.get_aliases()  # includes names from earlier ingests (single-file mode)
    todo = [r for r in records if (old := store.get_source(r["path"])) is None or old["content_hash"] != r["hash"]]
    rows = []
    if todo:
        await cognee_client.ensure_dataset(dataset)
        sem = asyncio.Semaphore(PARALLEL)
        async with asyncio.TaskGroup() as tg:  # first failure cancels the rest
            tasks = [tg.create_task(_ingest_record(r, dataset, sem)) for r in todo]
        rows = [t.result() for t in tasks]
    return records, aliases, todo, rows


async def _finish(root: Path, dataset: str, records: list, aliases: dict, todo: list, rows: list) -> dict:
    """cognify → record sources → showcase edge check → stale alerts → path cache."""
    t0 = time.perf_counter()
    if todo:
        await cognee_client.build(dataset)
        # Recorded only now: a failed add/cognify leaves these files "unseen", so the next run retries.
        # Re-adding is safe: Cognee derives data_id from content, so it returns the same id.
        for row in rows:
            store.upsert_source(*row)

    graph = await cognee_client.graph_dump(dataset)
    missing = align.missing_edges(SHOWCASE, graph, aliases)
    # ponytail: the retry doc isn't tracked in sources, so it outlives an edited ADR until --reset.
    if missing and todo:  # one retry: re-add just the dropped triples
        await cognee_client.add_structural(missing, dataset, "showcase-retry.triples.txt")
        await cognee_client.build(dataset)
        graph = await cognee_client.graph_dump(dataset)
        missing = align.missing_edges(SHOWCASE, graph, aliases)

    if Path(root).is_dir():
        contradictions.refresh_stale_alerts(records)
    try:
        await paths.refresh(graph)
    except Exception:  # the graph is built; a stale path cache must not fail the ingest
        logging.exception("path cache refresh failed")

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


async def ingest(root: Path = DATA_DIR / "seed", reset: bool = False, dataset: str = COGNEE_DATASET) -> dict:
    t0 = time.perf_counter()
    stats = await _finish(root, dataset, *await _prepare(root, reset, dataset))
    return stats | {"took_s": round(time.perf_counter() - t0, 1)}


async def ingest_file(path: Path, dataset: str = COGNEE_DATASET) -> tuple[dict, Coroutine]:
    """Live ingest of one uploaded doc (P4). Returns (IngestResult, finish): the caller runs `finish`
    (cognify + path refresh, ~30 s on Cognee's side) in the background.

    The alert doesn't need the graph: claims and candidates come from frontmatter. So the response returns
    after /add + the judge (~8 s) instead of ~38 s, and a re-ask sees the contradiction warning at once
    (it comes from `alerts`). Same dataset as the seed, not a separate `live` one: cognify is
    incremental, so it only processes the new file, and /ask, /graph and paths read one dataset.
    """
    t0 = time.perf_counter()
    recs = loaders.load(path)
    if not recs:
        raise ValueError(f"{path.name}: no frontmatter id / not a recognised ADR, meeting or ticket")
    store.init_db()
    async with asyncio.TaskGroup() as tg:  # either failing cancels the other (gather wouldn't)
        prep = tg.create_task(_prepare(path, False, dataset))
        chk = tg.create_task(contradictions.check(recs[0], loaders.load(DATA_DIR)))
    prepared, alerts = prep.result(), chk.result()
    result = {
        "source_ref": recs[0]["ref"],
        "nodes_added": 0,  # unknown until cognify finishes; see graph_status
        "graph_status": "building" if prepared[2] else "unchanged",
        "alerts": alerts,
        "took_ms": round((time.perf_counter() - t0) * 1000),
    }
    return result, _finish(path, dataset, *prepared)


async def forget(path: Path, dataset: str = COGNEE_DATASET) -> None:
    """Undo an ingest (demo reset, P5): drop the file's Cognee data, sources row and alerts; keep the file.
    A running server keeps its cached path edges until the next ingest or restart."""
    store.init_db()
    recs = loaders.load(path) if Path(path).exists() else []
    if not recs:
        raise SystemExit(f"{path}: not found or not a recognised document")
    rec = recs[0]
    if row := store.get_source(rec["path"]):
        for data_id in (row["data_id"], row["triples_data_id"]):
            if data_id:
                await cognee_client.delete_data(data_id, dataset)
        store.delete_source(rec["path"])
    store.clear_contradictions(rec["ref"])


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.ingest")
    ap.add_argument("--reset", action="store_true", help="delete the Cognee dataset and clear sources/aliases first")
    ap.add_argument("--forget", action="store_true", help="un-ingest PATH (e.g. data/live/MTG-0402.md) instead")
    ap.add_argument("path", nargs="?", type=Path, default=DATA_DIR / "seed")
    args = ap.parse_args()
    if args.forget:
        asyncio.run(forget(args.path))
        print(f"forgot {args.path}")
        return
    stats = asyncio.run(ingest(args.path, args.reset))
    for k, v in stats.items():
        print(f"{k:24} {v}")
    if stats["showcase_missing"]:
        raise SystemExit(f"FAIL: showcase edges missing from the graph: {stats['showcase_missing']}")


if __name__ == "__main__":
    main()
