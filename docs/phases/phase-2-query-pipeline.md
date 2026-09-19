# Phase 2: Query pipeline (`POST /ask`)

> **Goal:** a grounded answer with evidence, the exact multi-hop path and stale warnings, or an explicit refusal.
> **Tracks:** Cognee, Backend · **Est:** 2 h · **Depends on:** P1 · **Unblocks:** P3 (live), P4
> ← [Phase 1](phase-1-data-and-ingestion.md) · next → [Phase 3](phase-3-frontend.md)

---

## Contract (frozen at the start of this phase; frontend builds against it)

```jsonc
// POST /ask  {"question": "..."}
{
  "answer": "Payments moved to Postgres per ADR-007 ...",
  "grounded": true,
  "evidence": [
    {"source": "adr", "ref": "ADR-007", "path": "adrs/ADR-007.md", "snippet": "The ledger needs multi-row ACID ..."}
  ],
  "path": [
    {"from": {"id": "svc-payments", "type": "Service"}, "rel": "affected_by", "to": {"id": "ADR-007", "type": "Decision"}}
  ],
  "warnings": [
    {"kind": "stale", "node": "ADR-003", "message": "ADR-003 (Use MongoDB for the payments ledger) superseded by ADR-007 on 2026-03-12"}
  ],
  "latency_ms": 7900,
  "qa_id": 42
}
```
Refusal: `{"answer": "I couldn't find this in company knowledge.", "grounded": false, "evidence": [], "path": [], ...}`

---

## Cognee track: `cognee_client.ask()`
- [x] `POST /search` with `searchType: GRAPH_COMPLETION`, `verbose: true` and a fresh `sessionId` (S4/S5): answer = `text_result`, triplets = `objects_result` (`node1` / `node2` / relationship), chunks = the `DocumentChunk` nodes among them
- [x] Normalize into `RawResult{answer, triplets[(src, rel, dst)], chunks[{text, source_ref}]}`; `source_ref` = the ref of the chunk's `TextDocument` (named after our upload file) → `sources` row by ref

## Backend track: `backend/app/query/`

### `ask.py`: pipeline
```
question
  → cognee_client.ask()                         # retrieve + LLM answer
  → grounding_guard(raw)                         # refuse on NOT_FOUND, empty context, or no evidence in sources
  → map entities → canonical IDs (alias table)
  → path = paths.best_path(canonical_ids)        # deterministic, over structural edges
  → warnings = supersede_check(path + cited decisions)
  → evidence = top-3 chunks, deduped by source_ref, snippet ≤ 160 chars
  → qa_log insert → response
```

### Tasks
- [x] `grounding_guard`: refuse when there are no chunks and no triplets, **or** none of the cited refs exist in `sources`. Never let the LLM answer on empty context.
- [x] `paths.py`: `best_path(ids)`, a weighted shortest path (Dijkstra, tie-break weights) over verified structural edges (metadata triples ∩ `align.canonical_edges(graph_dump(), aliases)` gives canonical `(Type:id, rel, Type:id)` edges; cache at startup) between the question's anchor entity and the answer's person or team; max 4 hops; returns ordered edges. Match on canonical `Type:id` node names (graph ids are UUIDs, and edge labels are LLM-chosen)
  - Anchor = the first canonical Service/Decision/Ticket in the question; for a Service, route through the decision the answer cites; target = the Person (else Team) in the answer, plus their team
  - Cache the adjacency in memory; rebuild after `/ingest`
- [x] `supersede_check`: for every Decision in the path or evidence, look up `supersedes` in the loader metadata (ADR frontmatter), not the LLM-built graph, and emit a `stale` warning. This is **code, not prompt**, so it is always correct.
- [x] Answer post-processing: if the LLM answer cites a superseded decision as current, append the warning text
- [x] `POST /ask` route + `POST /feedback {qa_id, helpful: bool}`
- [x] Timeouts: 20 s cognee call; one retry with backoff on rate-limit errors
- [x] Log: question, latency, token estimate, grounded flag → `qa_log`

### Tests (one small file: `backend/tests/test_ask.py`)
- [x] `best_path` returns the 4-hop showcase path from a fixture adjacency
- [x] `supersede_check` flags ADR-003
- [x] `grounding_guard` refuses on an empty context

---

### Carried over from the P1 audit
- [x] Evidence lookup: by **ref**, not data_id. Cognee names each chunk's `TextDocument` after our upload filename (`ADR-007`), so `store.get_source_by_ref()`; triples-doc chunks (`ADR-007.triples`) are dropped from evidence
- [x] `best_path` reverses edges where the contract says so: the graph has `ADR-007 affects svc-payments`, the contract shows `svc-payments affected_by ADR-007`. Pin with a test
- [x] `supersede_check` reads `supersedes` from `loaders.load()` frontmatter (cache at startup); app.db doesn't store frontmatter

## Results (2026-09-19, dataset `snow`)
| Check | Result |
|---|---|
| Showcase via curl | `grounded: true`; evidence = meeting MTG-0312 + adr ADR-007 + ticket TCK-142; path `svc-payments > ADR-007 > MTG-0312 > priya > platform`; warning ADR-003 |
| Refusal ("mobile release cadence") | `grounded: false`, refusal text, no evidence/path |
| Showcase 5× (+3× after audit fixes) | identical path, warnings and evidence 8/8 |
| Latency | 9.8–13.0 s per `/ask` (Cognee Cloud `/search` dominates) |
| Offline checks | `uv run python -m tests.test_ask` (9) + `tests.test_ingest` (6) |

### Findings
- **Refusal needs a sentinel.** Top-k retrieval always returns context (15 triplets even for off-corpus questions), so "no context" never fires. The `systemPrompt` makes the LLM answer exactly `NOT_FOUND`; the guard keys on that, plus "at least one evidence source exists in `sources`".
- **The LLM writes false edges with our labels** (`ADR-007 affects svc-reports`, `priya owns ADR-007`). Path edges are therefore **metadata triples ∩ graph edges** (124 verified), never graph-only.
- **Typographic characters**: answers use U+2011 hyphens and U+202F spaces (`ADR‑007`); `cognee_client.clean()` normalizes before any ID matching.
- **Path choice** is weighted shortest path with a waypoint (the decision the answer cites): decision → meeting → person costs less than `owned_by`/ticket hops, so the "why + who" route wins deterministically.
- The LLM echoes our text headers (`[DECISION ADR-007 2026-03-12]`); stripped to the ID.
- **Audit fixes**: refusal matched in any wording (`not found`, `no information`); an answer citing only made-up IDs is refused; the path waypoint must be an *active* decision (an answer mentioning ADR-003 first used to route through it); Dijkstra's visited set is keyed on hop count; evidence = only files the answer cites (triples-doc chunks count for their file), so no filler; overall 23 s budget for `/search` incl. retry; transport/parse errors → 502, unknown `qa_id` → 404.
- **Known retrieval limit (for the P4 eval)**: "Who owns the service affected by TCK-118?" retrieved only ticket triples, not the org chart, so the LLM answered "owned by diego" (the assignee) instead of the Data team. The path (TCK-118 → diego → data) is structurally true, but the answer is wrong. The raw-Cognee baseline should show whether our layers change this.

## Acceptance criteria
```bash
curl -s localhost:8000/ask -d '{"question":"Why is payments on Postgres, and who should I talk to about it now?"}' -H 'content-type: application/json' | jq
```
- `grounded: true`, ≥2 evidence items from different source types, `path` = 4 hops ending at `platform`, `warnings` includes ADR-003
- `"What's our mobile release cadence?"` → `grounded: false`, refusal text
- Same showcase query 5× → identical `path` (it is deterministic)

## Exit gate
The showcase and refusal queries both behave correctly via curl.

## If behind
Hard-code the path anchor detection to regex on canonical IDs in the question and answer text. Keep BFS.
