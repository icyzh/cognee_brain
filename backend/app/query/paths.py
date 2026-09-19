"""Hop path over the verified structural edges of the Cognee graph (canonical `Type:id` nodes)."""

import heapq
import re

from app import cognee_client, store
from app.config import DATA_DIR
from app.ingest import align, loaders, structural

INVERSE = {
    "affects": "affected_by", "owns": "owned_by", "member_of": "has_member", "led_by": "leads",
    "decided_in": "decided", "owned_by": "owns", "supersedes": "superseded_by", "assigned_to": "assigned",
    "about": "has_ticket", "references": "referenced_by", "attended_by": "attended", "produced": "produced_by", "proposes_change_to": "change_proposed_in",
}
# Tie-breaks between equally short routes: decision → meeting → person tells the "why + who" story;
# a ticket or bare ownership hop is the fallback.
WEIGHT = {"owned_by": 2.5, "assigned_to": 1.5, "about": 1.5, "references": 1.5}

_cache: dict = {}


async def refresh(graph: cognee_client.GraphDump | None = None) -> None:
    """Rebuild the adjacency; call at startup and after /ingest.

    Path edges = metadata triples ∩ graph edges. The LLM also writes edges between canonical nodes,
    some with our labels and some false (seen: "ADR-007 affects svc-reports", "priya owns ADR-007"),
    so the graph alone can't be trusted, and metadata alone isn't proof the edge is in Cognee.
    """
    aliases = store.get_aliases()
    records = loaders.load(DATA_DIR)  # seed + live; edges not yet ingested drop out of the intersection
    truth = {
        (align.canonical_id(s, aliases), r, align.canonical_id(o, aliases))
        for rec in records for s, r, o in structural.triples(rec)
    }
    graph = graph or await cognee_client.graph_dump()  # ingest passes the dump it already has (~6 s each)
    build(align.canonical_edges(graph, aliases) & truth, aliases, {r["ref"]: r["meta"] for r in records if r["type"] == "adr"})
    _cache["nodes"] = len(graph["nodes"])


def build(edges: set[tuple[str, str, str]], aliases: dict[str, str], adrs: dict[str, dict]) -> None:
    adj: dict[str, list] = {}
    for s, rel, o in sorted(edges):
        adj.setdefault(s, []).append((o, rel, rel))  # (next, label as walked, stored label for weights)
        adj.setdefault(o, []).append((s, INVERSE[rel], rel))
    names = sorted(aliases, key=len, reverse=True)
    _cache.clear()
    _cache.update(
        adj=adj,
        adrs=adrs,
        aliases=aliases,
        mention_re=re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, names)) + r")(?![\w-])") if names else None,
    )


def mentions(text: str, bare_teams: bool = True) -> list[str]:
    """Canonical IDs mentioned in text, in order of first appearance (longest alias wins).

    bare_teams=False ignores teams matched only by their bare ID ("data", "platform"): ordinary words
    in LLM prose ("stores payment data"), while "Platform team" / "Data" by display name still count.
    """
    if not _cache.get("mention_re"):
        return []
    seen: dict[str, None] = {}
    for m in _cache["mention_re"].finditer(align.norm(cognee_client.clean(text))):
        cid = _cache["aliases"][m.group(1)]
        if not bare_teams and cid.startswith("Team:") and m.group(1) == cid.split(":", 1)[1]:
            continue
        seen.setdefault(cid)
    return list(seen)


def shortest(a: str, b: str, max_hops: int = 4) -> list[tuple[str, str, str]] | None:
    """Weighted shortest path a → b as ordered (from, rel, to) hops; deterministic tie-breaks."""
    adj = _cache.get("adj", {})
    heap = [(0.0, (), a)]
    done: set[tuple[str, int]] = set()  # keyed on hop count too: a cheaper-but-longer route must not block a shorter one
    while heap:
        cost, hops, node = heapq.heappop(heap)
        if node == b:
            return list(hops)
        if (node, len(hops)) in done or len(hops) >= max_hops:
            continue
        done.add((node, len(hops)))
        for nxt, rel, base in sorted(adj.get(node, [])):
            heapq.heappush(heap, (cost + WEIGHT.get(base, 1.0), hops + ((node, rel, nxt),), nxt))
    return None


def rank_people(seeds: list[str], k: int = 3, alpha: float = 0.3, iters: int = 30) -> list[dict]:
    """Who to ask: Personalized PageRank over the verified edges, restarting at the entities the question and
    answer mention (HippoRAG, arXiv 2405.14831). Ranks by graph evidence (decisions owned, meetings attended,
    tickets assigned), not by who the LLM happened to name first. Hub-ish edges keep their path WEIGHT penalty."""
    adj = _cache.get("adj", {})
    seeds = [s for s in dict.fromkeys(seeds) if s in adj]
    if not seeds:
        return []
    score = restart = {s: 1 / len(seeds) for s in seeds}
    for _ in range(iters):
        nxt = {s: alpha * r for s, r in restart.items()}
        for node, mass in score.items():
            out = [(n, 1 / WEIGHT.get(base, 1.0)) for n, _, base in adj[node]]
            total = sum(w for _, w in out)
            for n, w in out:
                nxt[n] = nxt.get(n, 0.0) + (1 - alpha) * mass * w / total
        score = nxt
    people = sorted(((v, n) for n, v in score.items() if n.startswith("Person:")), key=lambda x: (-x[0], x[1]))[:k]
    team = lambda p: next((n.split(":", 1)[1] for n, rel, _ in adj[p] if rel == "member_of"), None)  # noqa: E731
    return [{"id": p.split(":", 1)[1], "team": team(p), "score": round(v, 3)} for v, p in people]


def best_path(question_ids: list[str], answer_ids: list[str]) -> list[tuple[str, str, str]]:
    """Anchor (first Service/Decision/Ticket in the question) → cited *active* decision → person → team.

    No anchor in the question ("who decided how we send customer notifications?") → the first decision
    the answer cites is the anchor: its path still shows who decided it, where, and their real team.
    """
    anchor = next((i for i in question_ids if i.split(":")[0] in ("Service", "Decision", "Ticket")), None)
    anchor = anchor or next((i for i in answer_ids if i.startswith("Decision:")), None)
    person = next((i for i in answer_ids if i.startswith("Person:")), None)
    team = next((i for i in answer_ids if i.startswith("Team:")), None)
    target = person or team
    if not anchor or not target:
        return []
    waypoint = None
    if anchor.startswith("Service:"):  # "why is <service> …": route through the decision the answer cites
        adrs = _cache.get("adrs", {})
        waypoint = next((
            i for i in answer_ids
            if i.startswith("Decision:") and not adrs.get(i.split(":", 1)[1], {}).get("superseded_by") and shortest(anchor, i, 1)
        ), None)
    legs = [(anchor, waypoint), (waypoint, target)] if waypoint else [(anchor, target)]
    path: list[tuple[str, str, str]] = []
    for a, b in legs:
        leg = shortest(a, b)
        if leg is None:
            return []
        path += leg
    if person and not any(h[2].startswith("Team:") or h[0].startswith("Team:") for h in path):
        path += next(([(person, rel, n)] for n, rel, _ in _cache["adj"].get(person, []) if rel == "member_of"), [])
    return path
