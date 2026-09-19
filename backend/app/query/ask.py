"""POST /ask: retrieve → grounding guard → canonical IDs → path → stale warnings → evidence → log."""

import json
import re
import time

from app import cognee_client, store
from app.ingest import structural
from app.logs import jlog
from app.query import paths

REFUSAL = "I couldn't find this in company knowledge."
SOURCE_TYPES = {"adr", "ticket", "meeting", "org"}
_WORD = re.compile(r"[a-z0-9-]{4,}")
_ID = re.compile(r"\b[A-Z]{2,4}-\d{3,4}\b")
_NOT_FOUND = re.compile(r"\bnot[\s_-]?found\b|\bno (?:relevant )?information\b", re.I)
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
_HEADER_REF = re.compile(r"\[(?:DECISION|MEETING|TICKET) ([A-Z]+-\d+)[^\]]*\]")  # our text-doc headers, echoed by the LLM


def grounding_guard(raw: cognee_client.RawResult) -> bool:
    """True if the answer may be shown: context exists, the LLM didn't refuse in any wording, and if it
    cites IDs, at least one is a real ingested source (a made-up "ADR-099" alone is not grounding)."""
    answer = raw["answer"].strip()
    if not answer or (not raw["chunks"] and not raw["triplets"]) or _NOT_FOUND.search(answer):
        return False
    cited = set(_ID.findall(answer))
    return not cited or any(store.get_source_by_ref(i) for i in cited)


def unsupported_citations(raw: cognee_client.RawResult) -> list[str]:
    """IDs the answer cites that appear nowhere in the retrieved context (chunk files, chunk text, triplets).
    Deterministic citation-precision check: existing in the corpus is not enough, it must have been retrieved."""
    context = " ".join([f"{c['source_ref']} {c['text']}" for c in raw["chunks"]] + [f"{s} {o}" for s, _, o in raw["triplets"]]).upper()  # cognify lowercases entity names
    return [i for i in dict.fromkeys(_ID.findall(raw["answer"])) if i not in context]


def snippet(text: str, terms: set[str], limit: int = 160) -> str:
    """The chunk sentence sharing the most words with the question + answer, header lines skipped."""
    sents = [s.strip() for s in _SENT.split(text) if s.strip() and not s.startswith(("[", "attendees:", "assignee:", "#"))]
    if not sents:
        return text[:limit]
    best = max(sents, key=lambda s: len(terms & set(_WORD.findall(s.lower()))))
    return best if len(best) <= limit else best[: limit - 1].rstrip() + "…"


def evidence(raw: cognee_client.RawResult, terms: set[str], k: int = 3) -> list[dict]:
    """Up to k chunks from distinct source files that exist in `sources`, in Cognee's relevance order.

    If the answer cites IDs, only those files count (otherwise top-k filled up with whatever was
    retrieved, e.g. an office-wifi ticket). A file's triples doc ("TCK-118.triples") is evidence for
    that file too; its prose chunk is preferred when both were retrieved.
    """
    cited = set(_ID.findall(raw["answer"]))
    by_ref: dict[str, dict] = {}
    for ch in raw["chunks"]:
        if not ch["source_ref"]:
            continue
        ref = ch["source_ref"].removesuffix(".triples")
        if (cited and ref not in cited) or (ref in by_ref and not by_ref[ref]["triples"]):
            continue
        by_ref[ref] = {"text": ch["text"], "triples": ch["source_ref"].endswith(".triples"), "order": by_ref.get(ref, {}).get("order", len(by_ref))}
    out = []
    for ref, ch in sorted(by_ref.items(), key=lambda kv: kv[1]["order"]):
        src = store.get_source_by_ref(ref)
        if src and src["type"] in SOURCE_TYPES:
            out.append({"source": src["type"], "ref": ref, "path": src["path"], "snippet": snippet(ch["text"], terms)})
        if len(out) == k:
            break
    return out


def supersede_check(decisions: list[str], adrs: dict[str, dict]) -> list[dict]:
    """Stale warnings from ADR frontmatter (code, not prompt): a cited decision that was superseded,
    or the older decision a cited one replaced."""
    warnings: dict[str, dict] = {}

    def warn(old: str, new: str):
        o, n = adrs.get(old, {}), adrs.get(new, {})
        warnings.setdefault(old, {
            "kind": "stale", "node": old,
            "message": f"{old} ({o.get('title', '')}) superseded by {new} on {n.get('date', '?')}",
        })

    for d in decisions:
        meta = adrs.get(d, {})
        for new in structural._list(meta.get("superseded_by")):
            warn(d, new)
        for old in structural._list(meta.get("supersedes")):
            warn(old, d)
    return list(warnings.values())


def _hop(h: tuple[str, str, str]) -> dict:
    (ft, fid), (tt, tid) = h[0].split(":", 1), h[2].split(":", 1)
    return {"from": {"id": fid, "type": ft}, "rel": h[1], "to": {"id": tid, "type": tt}}


async def ask_raw(question: str) -> dict:
    """Plain Cognee for the side-by-side demo: default prompt, no guard / supersede / path, not logged."""
    t0 = time.perf_counter()
    raw = await cognee_client.ask(question, system_prompt=None)
    refs = dict.fromkeys(c["source_ref"].removesuffix(".triples") for c in raw["chunks"] if c["source_ref"])
    return {"answer": raw["answer"], "retrieved_refs": list(refs), "latency_ms": round((time.perf_counter() - t0) * 1000)}


async def ask(question: str) -> dict:
    t0 = time.perf_counter()
    raw = await cognee_client.ask(question)
    resp = {"answer": REFUSAL, "grounded": False, "evidence": [], "path": [], "warnings": []}

    terms = set(_WORD.findall(f"{question} {raw['answer']}".lower()))
    ev = evidence(raw, terms) if grounding_guard(raw) else []
    if ev and (a_ids := paths.mentions(raw["answer"], bare_teams=False)):  # must name something real
        q_ids = paths.mentions(question)
        path = paths.best_path(q_ids, a_ids)
        decisions = list(dict.fromkeys(
            [i.split(":", 1)[1] for i in a_ids if i.startswith("Decision:")]
            + [x.split(":", 1)[1] for h in path for x in (h[0], h[2]) if x.startswith("Decision:")]
            + [e["ref"] for e in ev if e["source"] == "adr"]
        ))
        adrs = paths._cache.get("adrs", {})
        warnings = supersede_check(decisions, adrs) + [
            {"kind": "contradiction", "node": c["existing_ref"], "message": f"{c['new_ref']} contradicts {c['existing_ref']}: {c['reason']}"}
            # services too: the answer's wording varies run to run and may not cite the decision (rehearsal run 3)
            for c in store.contradictions_for(decisions, [i.split(":", 1)[1] for i in q_ids + a_ids if i.startswith("Service:")])
        ]
        answer = _HEADER_REF.sub(r"\1", raw["answer"])
        cited = {i.split(":", 1)[1] for i in a_ids if i.startswith("Decision:")}
        for w in warnings:  # the answer cites a stale decision as if current, without its successor
            if w["node"] in cited and not cited & set(structural._list(adrs.get(w["node"], {}).get("superseded_by"))):
                answer += f" Note: {w['message']}."
        resp.update(answer=answer, grounded=True, evidence=ev, path=[_hop(h) for h in path], warnings=warnings,
                    unsupported_citations=unsupported_citations(raw), experts=paths.rank_people(q_ids + a_ids))

    resp["latency_ms"] = round((time.perf_counter() - t0) * 1000)
    tokens_est = (len(question) + len(raw["answer"]) + sum(len(c["text"]) for c in raw["chunks"])) // 4
    resp["qa_id"] = store.log_qa(question, resp["answer"], json.dumps(resp), resp["grounded"], tokens_est, resp["latency_ms"])
    jlog("ask", grounded=resp["grounded"], latency_ms=resp["latency_ms"], tokens_est=tokens_est, qa_id=resp["qa_id"], hops=len(resp["path"]))
    return resp


def cached(question: str) -> dict | None:
    """The last answer to this exact question, with contradiction warnings recomputed (an alert raised
    after it was cached, e.g. the live MTG-0402 upload, still shows). Flagged `cached: true`."""
    resp = store.last_answer(question)
    if not resp:
        return None
    decisions = list(dict.fromkeys(
        [x["id"] for h in resp["path"] for x in (h["from"], h["to"]) if x["type"] == "Decision"]
        + [e["ref"] for e in resp["evidence"] if e["source"] == "adr"]
    ))
    services = [x["id"] for h in resp["path"] for x in (h["from"], h["to"]) if x["type"] == "Service"]
    services += [i.split(":", 1)[1] for i in paths.mentions(question) if i.startswith("Service:")]
    resp["warnings"] = [w for w in resp["warnings"] if w["kind"] != "contradiction"] + [
        {"kind": "contradiction", "node": c["existing_ref"], "message": f"{c['new_ref']} contradicts {c['existing_ref']}: {c['reason']}"}
        for c in store.contradictions_for(decisions, services)
    ]
    return resp | {"cached": True}
