"""Offline checks for ingestion logic (no Cognee calls). Run: uv run python -m tests.test_ingest"""

import asyncio
from pathlib import Path

from app import cognee_client
from app.config import DATA_DIR
from app.ingest import align, loaders, structural
from app.ingest.__main__ import SHOWCASE

RECORDS = loaders.load(DATA_DIR / "seed")
ALIASES = align.seed_aliases(RECORDS)


def node(id_, label, type_="Entity"):
    return {"id": id_, "label": label, "type": type_, "properties": {}}


# Shaped like the real cloud graph: lowercased / renamed labels, UUID ids, plus a hub node.
FAKE = {
    "nodes": [
        node("u1", "adr-007"), node("u2", "payments"), node("u3", "architecture sync"),
        node("u4", "priya sharma"), node("u5", "platform team"), node("u6", "postgres"),
        node("hub", "structural", "NodeSet"),
    ],
    "edges": [
        {"source": "u1", "target": "u2", "label": "affects"},
        {"source": "u1", "target": "u3", "label": "decided_in"},
        {"source": "u3", "target": "u4", "label": "attended_by"},
        {"source": "u4", "target": "u5", "label": "member_of"},
        {"source": "u1", "target": "u6", "label": "uses"},
        {"source": "u1", "target": "hub", "label": "belongs_to_set"},
        {"source": "u5", "target": "hub", "label": "belongs_to_set"},
    ],
}


def test_every_triple_endpoint_is_canonical():
    for s, _, o in (t for r in RECORDS for t in structural.triples(r)):
        assert align.canonical_id(s, ALIASES) and align.canonical_id(o, ALIASES), (s, o)


def test_showcase_is_in_seed_triples():
    triples = {t for r in RECORDS for t in structural.triples(r)}
    assert set(SHOWCASE) <= triples


def test_aliases_resolve_llm_names():
    assert ALIASES["architecture sync"] == "Meeting:MTG-0312"
    assert ALIASES["payments"] == "Service:svc-payments"
    assert ALIASES["priya sharma"] == ALIASES["p. sharma"] == "Person:priya"
    assert ALIASES["platform team"] == "Team:platform"


def test_missing_edges():
    assert align.missing_edges(SHOWCASE[:4], FAKE, ALIASES) == []
    assert align.missing_edges(SHOWCASE, FAKE, ALIASES) == [("ADR-007", "supersedes", "ADR-003"), ("TCK-142", "references", "ADR-007")]


def test_focus_walk_skips_hubs():
    async def fake_dump(dataset=None, **_):
        return FAKE

    cognee_client.graph_dump = fake_dump
    v = asyncio.run(align.graph("ADR-007", 1, ALIASES))
    ids = {n["id"] for n in v["nodes"]}
    assert ids == {"ADR-007", "svc-payments", "MTG-0312", "u6"}, ids  # not via the hub to platform
    assert "hub" not in ids


def test_source_paths_are_stable():
    assert [(r["ref"], r["path"]) for r in loaders.load(Path(DATA_DIR / "live" / "MTG-0402.md"))] == [("MTG-0402", "live/MTG-0402.md")]
    # single-file and batch runs must key the same sources row
    assert loaders.load(DATA_DIR / "seed" / "adrs" / "ADR-007.md")[0]["path"] == "adrs/ADR-007.md"
    assert "adrs/ADR-007.md" in {r["path"] for r in RECORDS}


def test_semantic_only_formats():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        files = {"Standup notes 04-02.txt": b"Priya: cutover Sunday.", "notes.md": b"# Just notes\nno frontmatter",
                 "export.json": b'[{"a": 1}]', "call.mp3": b"ID3fake", "whiteboard.PNG": b"\x89PNG", "README.md": b"bible",
                 "tool.exe": b"MZ"}
        for n, b in files.items():
            (d / n).write_bytes(b)
        recs = {r["ref"]: r for r in loaders.load(d)}
    assert {k: v["type"] for k, v in recs.items()} == {
        "Standup-notes-04-02": "doc", "notes": "doc", "export": "doc", "call": "audio", "whiteboard": "image"}
    assert recs["call"]["suffix"] == ".mp3" and recs["whiteboard"]["suffix"] == ".png" and "file" in recs["call"]
    assert recs["Standup-notes-04-02"]["body"] == "Priya: cutover Sunday."
    assert all(structural.triples(r) == [] for r in recs.values())  # semantic-only: no metadata edges


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
