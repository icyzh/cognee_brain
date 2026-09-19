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
    {"kind": "stale", "node": "ADR-003", "message": "ADR-003 (MongoDB) superseded by ADR-007 on 2026-03-12"}
  ],
  "latency_ms": 7900,
  "qa_id": 42
}
```
Refusal: `{"answer": "I couldn't find this in company knowledge.", "grounded": false, "evidence": [], "path": [], ...}`

---

## Cognee track: `cognee_client.ask()`
- [ ] `POST /search` with `searchType: GRAPH_COMPLETION`, `verbose: true` and a fresh `sessionId` (S4/S5): answer = `text_result`, triplets = `objects_result` (`node1` / `node2` / relationship), chunks = the `DocumentChunk` nodes among them
- [ ] Normalize into `RawResult{answer, triplets[(src, rel, dst)], chunks[{text, source_ref}]}`; `source_ref` = the chunk's `data_id` → `sources` row

## Backend track: `backend/app/query/`

### `ask.py`: pipeline
```
question
  → cognee_client.ask()                         # retrieve + LLM answer
  → grounding_guard(raw)                         # refuse if no chunks/triplets
  → map entities → canonical IDs (alias table)
  → path = paths.best_path(canonical_ids)        # deterministic, over structural edges
  → warnings = supersede_check(path + cited decisions)
  → evidence = top-3 chunks, deduped by source_ref, snippet ≤ 160 chars
  → qa_log insert → response
```

### Tasks
- [ ] `grounding_guard`: refuse when there are no chunks and no triplets, **or** none of the cited refs exist in `sources`. Never let the LLM answer on empty context.
- [ ] `paths.py`: `best_path(ids)`, a BFS over structural edges (from `graph()` or a cached adjacency built at startup) between the question's anchor entity and the answer's person or team; max 4 hops; returns ordered edges. Match on canonical `Type:id` node names (graph ids are UUIDs, and edge labels are LLM-chosen)
  - Anchor = the first canonical Service/Decision mentioned; target = the Person/Team in the answer
  - Cache the adjacency in memory; rebuild after `/ingest`
- [ ] `supersede_check`: for every Decision in the path or evidence, look up `supersedes` in the loader metadata (ADR frontmatter), not the LLM-built graph, and emit a `stale` warning. This is **code, not prompt**, so it is always correct.
- [ ] Answer post-processing: if the LLM answer cites a superseded decision as current, append the warning text
- [ ] `POST /ask` route + `POST /feedback {qa_id, helpful: bool}`
- [ ] Timeouts: 20 s cognee call; one retry with backoff on rate-limit errors
- [ ] Log: question, latency, token estimate, grounded flag → `qa_log`

### Tests (one small file: `backend/tests/test_ask.py`)
- [ ] `best_path` returns the 4-hop showcase path from a fixture adjacency
- [ ] `supersede_check` flags ADR-003
- [ ] `grounding_guard` refuses on an empty context

---

## Acceptance criteria
```bash
curl -s localhost:8000/ask -d '{"question":"Why is payments on Postgres, and who should I talk to now?"}' -H 'content-type: application/json' | jq
```
- `grounded: true`, ≥2 evidence items from different source types, `path` = 4 hops ending at `platform`, `warnings` includes ADR-003
- `"What's our Kafka strategy?"` → `grounded: false`, refusal text
- Same showcase query 5× → identical `path` (it is deterministic)

## Exit gate
The showcase and refusal queries both behave correctly via curl.

## If behind
Hard-code the path anchor detection to regex on canonical IDs in the question and answer text. Keep BFS.
