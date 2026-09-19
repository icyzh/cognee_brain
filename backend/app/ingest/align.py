"""Map LLM-named graph entities to canonical IDs, and check expected structural edges.

cognify lowercases and renames entities (spike: "Meeting:MTG-0312" → "architecture sync",
"Service:payments" → "payments"), so every graph lookup goes through the alias index.
ponytail: exact alias matching only; add fuzzy matching if unmatched entities hurt recall.
ponytail: bare IDs like "data" / "platform" are aliases too (triples use raw IDs), so an LLM
concept literally named "data" merges into Team:data in /graph; namespace IDs if that bites.
"""

from app import cognee_client
from app.config import COGNEE_DATASET

TYPE_BY_RECORD = {"adr": "Decision", "ticket": "Ticket", "meeting": "Meeting"}


def norm(name: str) -> str:
    return " ".join(str(name).lower().split())


def seed_aliases(records: list[dict]) -> dict[str, str]:
    """name → canonical 'Type:id' from seed metadata (IDs, display names, declared aliases, titles)."""
    out: dict[str, str] = {}

    def add(cid: str, *names):
        for n in names:
            if n:
                out.setdefault(norm(n), cid)

    for rec in records:
        m = rec["meta"]
        if rec["type"] == "org":
            for p in m.get("people", []):
                add(f"Person:{p['id']}", p["id"], p.get("name"), p["name"].split()[0] if p.get("name") else None, *p.get("aliases", []))
            for t in m.get("teams", []):
                add(f"Team:{t['id']}", t["id"], t.get("name"), f"{t.get('name', t['id'])} team", f"{t['id']} team")
                for s in t.get("owns", []):
                    short = s.removeprefix("svc-")
                    add(f"Service:{s}", s, short, f"{short} service")
        else:
            cid = f"{TYPE_BY_RECORD[rec['type']]}:{rec['ref']}"
            title = rec["meta"].get("title")
            add(cid, rec["ref"], title, title.split(":")[0] if title and rec["type"] == "meeting" else None)
    return out


def canonical_id(ref: str, aliases: dict[str, str]) -> str | None:
    return aliases.get(norm(ref))


def canonical_edges(graph: cognee_client.GraphDump, aliases: dict[str, str]) -> set[tuple[str, str, str]]:
    names = {n["id"]: aliases.get(norm(n["label"])) for n in graph["nodes"]}
    return {
        (names[e["source"]], e["label"], names[e["target"]])
        for e in graph["edges"]
        if names.get(e["source"]) and names.get(e["target"])
    }


def missing_edges(
    expected: list[tuple[str, str, str]], graph: cognee_client.GraphDump, aliases: dict[str, str]
) -> list[tuple[str, str, str]]:
    """Expected triples (raw IDs) not found in the graph, matched on canonical node + edge label."""
    have = canonical_edges(graph, aliases)
    return [t for t in expected if (canonical_id(t[0], aliases), t[1], canonical_id(t[2], aliases)) not in have]


def matched_entities(graph: cognee_client.GraphDump, aliases: dict[str, str]) -> dict[str, str]:
    """LLM Entity label → canonical ID, for the ones the alias index resolves."""
    return {n["label"]: cid for n in graph["nodes"] if n.get("type") == "Entity" and (cid := aliases.get(norm(n["label"])))}


def view(graph: cognee_client.GraphDump, aliases: dict[str, str]) -> dict:
    """Cloud graph → `{nodes:[{id,type,label}], edges:[{from,to,rel}]}` with canonical IDs where known."""
    ids = {}
    nodes = {}
    for n in graph["nodes"]:
        cid = aliases.get(norm(n["label"]))
        ids[n["id"]] = cid.split(":", 1)[1] if cid else n["id"]
        nodes[ids[n["id"]]] = {"id": ids[n["id"]], "type": cid.split(":")[0] if cid else n["type"], "label": n["label"]}
    edges = [{"from": ids[e["source"]], "to": ids[e["target"]], "rel": e["label"]} for e in graph["edges"] if e["source"] in ids and e["target"] in ids]
    return {"nodes": list(nodes.values()), "edges": edges}


async def graph(focus: str | None, depth: int, aliases: dict[str, str], dataset: str = COGNEE_DATASET) -> dict:
    """Entity-level graph view; with focus (a canonical ID like ADR-007), its depth-hop neighborhood.

    Walks Entity→Entity edges only: the server's neighborhood walk goes through hub nodes
    (NodeSet, EntityType, chunks), so depth 2 returned ~80% of the graph.
    """
    full = await cognee_client.graph_dump(dataset)
    ents = {n["id"] for n in full["nodes"] if n["type"] == "Entity"}
    edges = [e for e in full["edges"] if e["source"] in ents and e["target"] in ents]
    keep = ents
    if focus:
        target = canonical_id(focus, aliases)
        keep = frontier = {n["id"] for n in full["nodes"] if n["id"] in ents and target and aliases.get(norm(n["label"])) == target}
        for _ in range(depth):
            frontier = {x for e in edges for a, x in ((e["source"], e["target"]), (e["target"], e["source"])) if a in frontier} - keep
            keep = keep | frontier
    return view(
        {"nodes": [n for n in full["nodes"] if n["id"] in keep], "edges": [e for e in edges if e["source"] in keep and e["target"] in keep]},
        aliases,
    )
