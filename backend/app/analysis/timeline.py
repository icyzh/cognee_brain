"""Decision timeline for a service: what was decided, when it was in force, and what now challenges it.

Pure code over ADR frontmatter + the alerts table (no LLM, no Cognee call). Validity intervals follow
Zep/Graphiti (arXiv 2501.13956): a superseded decision is closed (valid_to), never deleted, so
"what was true in February?" stays answerable.
"""

from datetime import date

from app.ingest import structural


def for_service(service: str, records: list[dict], alerts: list[dict], as_of: str | None = None) -> list[dict]:
    """Entries ordered by date. status: superseded | active | proposed (a contradiction alert on this service).
    `in_force` marks the decisions valid on `as_of` (ISO date, default today): valid_from <= as_of < valid_to."""
    as_of = as_of or date.today().isoformat()
    meta = {r["ref"]: r["meta"] for r in records}
    adrs = {r["ref"]: r["meta"] for r in records if r["type"] == "adr"}
    out = []
    for ref, m in adrs.items():
        if service not in structural._list(m.get("affects")):
            continue
        valid_from = str(m.get("date"))
        valid_to = min((str(adrs[n]["date"]) for n in structural._list(m.get("superseded_by")) if n in adrs), default=None)
        out.append({
            "ref": ref, "title": m.get("title", ""), "status": "superseded" if valid_to else "active",
            "valid_from": valid_from, "valid_to": valid_to, "superseded_by": structural._list(m.get("superseded_by")),
            "decided_in": m.get("decided_in"), "owner": m.get("owner"),
            "in_force": valid_from <= as_of and (valid_to is None or as_of < valid_to),
        })
    for a in alerts:
        if a["kind"] == "contradiction" and a["service"] == service:
            out.append({
                "ref": a["new_ref"], "title": a["reason"], "status": "proposed",
                "valid_from": str(meta.get(a["new_ref"], {}).get("date") or a["created_at"][:10]), "valid_to": None,
                "contradicts": a["existing_ref"], "in_force": False,
            })
    return sorted(out, key=lambda e: (e["valid_from"], e["ref"]))
