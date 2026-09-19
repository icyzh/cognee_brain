"""Offline checks for the /ask pipeline (no Cognee calls). Run: uv run python -m tests.test_ask"""

from app.config import DATA_DIR
from app.ingest import align, loaders, structural
from app.query import ask, paths

RECORDS = loaders.load(DATA_DIR / "seed")
ALIASES = align.seed_aliases(RECORDS)
ADRS = {r["ref"]: r["meta"] for r in RECORDS if r["type"] == "adr"}


def use_metadata_graph():
    """Fixture adjacency: every metadata triple, as if cognify kept all of them."""
    edges = {(align.canonical_id(s, ALIASES), r, align.canonical_id(o, ALIASES)) for rec in RECORDS for s, r, o in structural.triples(rec)}
    paths.build(edges, ALIASES, ADRS)


def test_showcase_path_is_the_4_hop_story():
    use_metadata_graph()
    q = paths.mentions("Why is payments on Postgres, and who should I talk to about it now?")
    a = paths.mentions("Moved per ADR‑007 (MTG‑0312). Priya Sharma owns TCK-142; talk to Priya (Platform team).")
    assert q == ["Service:svc-payments"]
    assert paths.best_path(q, a) == [
        ("Service:svc-payments", "affected_by", "Decision:ADR-007"),  # stored as ADR-007 affects svc-payments
        ("Decision:ADR-007", "decided_in", "Meeting:MTG-0312"),
        ("Meeting:MTG-0312", "attended_by", "Person:priya"),
        ("Person:priya", "member_of", "Team:platform"),
    ]


def test_no_anchor_or_target_means_no_path():
    use_metadata_graph()
    assert paths.best_path([], ["Person:priya"]) == []
    # no anchor in the question: the decision the answer cites anchors the path, and the verified
    # member_of edge wins over the LLM's claim ("marco ... part of the svc-payments team")
    assert [h[2] for h in paths.best_path([], ["Person:marco", "Service:svc-payments", "Decision:ADR-008"])] == [
        "Meeting:MTG-0305", "Person:marco", "Team:platform"]
    assert paths.best_path(["Service:svc-payments"], ["Decision:ADR-007"]) == []


def test_supersede_check_flags_adr_003():
    assert ask.supersede_check(["ADR-007"], ADRS) == [
        {"kind": "stale", "node": "ADR-003", "message": "ADR-003 (Use MongoDB for the payments ledger) superseded by ADR-007 on 2026-03-12"}
    ]
    assert [w["node"] for w in ask.supersede_check(["ADR-005"], ADRS)] == ["ADR-005"]  # cited stale decision
    assert ask.supersede_check(["ADR-001"], ADRS) == []


def test_grounding_guard_refuses():
    ask.store.get_source_by_ref = lambda ref: {"ref": ref} if ref in {r["ref"] for r in RECORDS} else None
    ctx = {"triplets": [("a", "r", "b")], "chunks": [{"text": "x", "source_ref": "ADR-001"}]}
    assert not ask.grounding_guard({"answer": "anything", "triplets": [], "chunks": []})
    for refusal in ("NOT_FOUND", "Not found in the provided context.", "not_found", "There is no information about that."):
        assert not ask.grounding_guard({"answer": refusal, **ctx}), refusal
    assert not ask.grounding_guard({"answer": "Decided in ADR-099.", **ctx})  # cites only a made-up ID
    assert ask.grounding_guard({"answer": "Per ADR\u2011001 …".replace("\u2011", "-"), **ctx})
    assert ask.grounding_guard({"answer": "The Data team owns reports.", **ctx})  # no IDs cited: allowed


def test_path_skips_superseded_decision():
    use_metadata_graph()
    q = paths.mentions("Why is payments on Postgres, and who should I talk to about it now?")
    a = paths.mentions("Payments left MongoDB (ADR-003) for Postgres per ADR-007, decided in MTG-0312. Talk to Priya.", bare_teams=False)
    assert [h[2] for h in paths.best_path(q, a)] == ["Decision:ADR-007", "Meeting:MTG-0312", "Person:priya", "Team:platform"]


def test_hop_limit_does_not_hide_a_shorter_route():
    # s -owned_by(2.5)-> t (1 hop) vs s -> x -> t (cost 2, 2 hops); then t -> 3 hops -> goal. Only the
    # 1-hop route fits in 4 hops, but the cheaper 2-hop route reaches t first.
    edges = {("S:s", "owned_by", "T:t"), ("S:s", "affects", "X:x"), ("X:x", "affects", "T:t"),
             ("T:t", "affects", "A:a"), ("A:a", "affects", "B:b"), ("B:b", "affects", "G:g")}
    paths.build(edges, {}, {})
    assert [h[2] for h in paths.shortest("S:s", "G:g", 4)] == ["T:t", "A:a", "B:b", "G:g"]


def test_bare_team_ids_in_prose_are_not_targets():
    use_metadata_graph()
    assert "Team:data" not in paths.mentions("The service stores payment data.", bare_teams=False)
    assert "Team:data" in paths.mentions("Ask the Data team.", bare_teams=False)


def test_evidence_only_cited_files_triples_count():
    ask.store.get_source_by_ref = lambda ref: {"ref": ref, "type": "ticket", "path": f"tickets/{ref}.json"}
    raw = {"answer": "svc-reports is affected by TCK-118.", "triplets": [], "chunks": [
        {"text": "TCK-112 about svc-notify.", "source_ref": "TCK-112.triples"},
        {"text": "TCK-118 assigned_to diego. TCK-118 about svc-reports.", "source_ref": "TCK-118.triples"},
        {"text": "[TICKET TCK-128] Office wifi keeps dropping.", "source_ref": "TCK-128"},
    ]}
    assert [e["ref"] for e in ask.evidence(raw, {"reports"})] == ["TCK-118"]
    raw["answer"] = "Nothing cited here."  # no IDs cited: top-k in relevance order
    assert [e["ref"] for e in ask.evidence(raw, set())] == ["TCK-112", "TCK-118", "TCK-128"]


def test_snippet_picks_the_relevant_sentence():
    text = "[DECISION ADR-007 2026-03-12] Use Postgres\n\n## Context\nWe like coffee. MongoDB could not give multi-document ACID guarantees."
    assert ask.snippet(text, {"mongodb", "acid", "guarantees"}) == "MongoDB could not give multi-document ACID guarantees."


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
