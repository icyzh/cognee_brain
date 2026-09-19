"""Metadata → canonical triples (S3: Cognee Cloud has no custom DataPoints, so edges go in as text)."""


def _list(v) -> list:
    return [] if v is None else v if isinstance(v, list) else [v]


def facts(rec: dict) -> list[str]:
    """Key metadata as plain sentences, sent in the triples doc. Retrieval favors that small doc for
    ID-centric questions ("status of TCK-142?"), and without these it held no status/date/title (eval).
    Not edges: kept out of triples(), so they're never verified or used in paths."""
    m, ref = rec["meta"], rec["ref"]
    keys = {"adr": ("title", "status", "date"), "ticket": ("title", "status", "created"), "meeting": ("title", "date")}
    return [f"{ref} {k} is {m[k]}." for k in keys.get(rec["type"], ()) if m.get(k)]


def triples(rec: dict) -> list[tuple[str, str, str]]:
    m, ref = rec["meta"], rec["ref"]
    out: list[tuple[str, str, str]] = []
    if rec["type"] == "org":
        out += [(p["id"], "member_of", p["team"]) for p in m.get("people", [])]
        for t in m.get("teams", []):
            out += [(t["id"], "owns", s) for s in t.get("owns", [])]
            if t.get("lead"):  # "X leads Y" was dropped by cognify every time; led_by survives like owned_by
                out.append((t["id"], "led_by", t["lead"]))
    elif rec["type"] == "adr":
        out += [(ref, "affects", s) for s in _list(m.get("affects"))]
        out += [(ref, "decided_in", x) for x in _list(m.get("decided_in"))]
        out += [(ref, "owned_by", x) for x in _list(m.get("owner"))]
        out += [(ref, "supersedes", x) for x in _list(m.get("supersedes"))]
    elif rec["type"] == "ticket":
        out += [(ref, "assigned_to", x) for x in _list(m.get("assignee"))]
        out += [(ref, "about", x) for x in _list(m.get("service"))]
        out += [(ref, "references", x) for x in _list(m.get("refs"))]
    elif rec["type"] == "meeting":
        out += [(ref, "attended_by", p) for p in _list(m.get("attendees"))]
        out += [(ref, "produced", d) for d in _list(m.get("decisions"))]
        out += [(ref, "proposes_change_to", s) for p in _list(m.get("proposals")) for s in _list(p.get("affects"))]
    return out
