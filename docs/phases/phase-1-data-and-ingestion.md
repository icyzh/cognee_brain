# Phase 1: Seed data + hybrid ingestion

> **Goal:** a consistent fictional company, ingested into Cognee as a hybrid graph (structural edges generated from metadata + LLM semantic knowledge), with the showcase 4-hop path **verified** to exist in the Cognee Cloud graph.
> **Tracks:** Data, Cognee, Backend · **Est:** 2–2.5 h · **Depends on:** P0 · **Unblocks:** P2, P4
> ← [Phase 0](phase-0-setup-and-spike.md) · next → [Phase 2](phase-2-query-pipeline.md)

---

## Data track: `data/seed/`

### Layout
```
data/
  seed/
    team.json
    adrs/ADR-001.md … ADR-009.md
    tickets/TCK-101.json … TCK-150.json
    meetings/MTG-0115.md … MTG-0320.md
  live/
    MTG-0402.md          # NOT pre-ingested; P4 demo trigger
```

### Formats
**team.json**
```json
{
  "people": [{"id": "priya", "name": "Priya Sharma", "aliases": ["Priya", "P. Sharma"], "team": "platform"}],
  "teams":  [{"id": "platform", "name": "Platform", "owns": ["svc-payments", "svc-ledger"]}]
}
```
**ADR (markdown + frontmatter)**
```markdown
---
id: ADR-007
title: Use Postgres for the payments ledger
status: accepted            # accepted | superseded
decided_in: MTG-0312
affects: [svc-payments, svc-ledger]
supersedes: ADR-003
owner: priya
date: 2026-03-12
---
## Context
The ledger needs multi-row ACID transactions; MongoDB (ADR-003) can't guarantee them…
## Decision
## Alternatives considered
```
**Ticket (JSON)**: `{id, title, body, assignee, service, refs: [ADR-…], status, created}`
**Meeting (markdown)**: frontmatter `{id, date, attendees, decisions: [ADR-…]}` + transcript lines `Name: text`

### Tasks
- [ ] Write the "story bible" first: 5 services, 8 ADRs (ADR-003→007 and ADR-005→009 superseded), and who decided what
- [ ] Author the files. **Every person and service reference uses canonical IDs or declared aliases.**
- [ ] Embed the showcase chain: `svc-payments ← ADR-007 → MTG-0312 → priya → platform` plus TCK-142
- [ ] Embed ≥3 more multi-hop answers for the eval set (e.g. "who owns the service affected by TCK-118?")
- [ ] Add 2–3 "noise" docs, so retrieval has to discriminate
- [ ] `data/live/MTG-0402.md`: Arjun proposes moving payments to DynamoDB "for scale", with no mention of ACID. It must contradict ADR-007.
- [ ] `data/seed/README.md`: the story bible (people, services, decision timeline). Also feeds the eval answers.

---

## Cognee track: `backend/app/ingest/`

### Structural edges as canonical triples (S3: no custom DataPoints in Cognee Cloud)
Metadata becomes one text line per edge, with canonical `Type:id` names, sent via `/add` with `node_set=["structural"]`:
```text
Decision:ADR-007 affects Service:svc-payments.
Decision:ADR-007 decided_in Meeting:MTG-0312.
Meeting:MTG-0312 attended_by Person:priya.
Person:priya member_of Team:platform.
Decision:ADR-007 supersedes Decision:ADR-003.
```
`cognify` turns these into graph edges (the spike reproduced `affects` / `owned_by`), but the LLM picks node names and edge labels, so **every expected triple is checked against `/graph` after cognify** (`missing_edges`). Node properties can't be set through `/add`: evidence maps each retrieved chunk's `data_id` → `sources` row (path, ref). Optional: pass a `graphModel` JSON schema to `/cognify` if node typing is needed.

### Tasks
- [ ] `loaders.py`: parse md frontmatter (`python-frontmatter` or a tiny YAML split), JSON; normalize IDs through the alias table; compute `sha256` of the content
- [ ] `structural.py`: records → canonical triples (above) → `cognee_client.add_structural(triples, dataset)`; keep the list of expected triples for the check
- [ ] `semantic.py`: render each doc as transcript-shaped text with a header (`[MEETING MTG-0312 2026-03-12] attendees: …`), then `cognee_client.add_text(text, node_set=[source_type], dataset=COGNEE_DATASET)` → store the returned `data_id` in `sources`
- [ ] `cognee_client.build(dataset)` → `/cognify` (`runInBackground: false`) once after the batch
- [ ] `cognee_client.missing_edges(expected)` → match on node name (case-insensitive) + edge label; any missing → re-add that triple once, then fail loudly
- [ ] `align.py`: after cognify, map LLM Entity names → canonical IDs via aliases (case-insensitive exact + alias). Store the mapping in the `app.db` `aliases` table (S3: no custom graph edges).
- [ ] `app/ingest/__main__.py`: `uv run python -m app.ingest [--reset] [path]` (`--reset` = `DELETE /api/v1/datasets/{id}` + clear `sources` / `aliases`):
  1. hash check against `sources` (skip unchanged)
  2. structural → semantic → cognify → `missing_edges` check → align
  3. print stats: nodes and edges per type, time taken, tokens if available

---

## Backend track
- [ ] `POST /ingest` → runs the same pipeline for `data/seed` (batch) or an uploaded file (single; used in P4)
- [ ] `GET /sources` → rows from the `sources` table
- [ ] `GET /graph?focus=&depth=` → `cognee_client.graph()` → `{nodes:[{id,type,label}], edges:[{from,to,rel}]}`. Cloud returns `nodes[{id (UUID), label, type, properties}]`, `edges[{source, target, label}]`: map `label`→`rel`, take the canonical type from the `Type:` name prefix (cloud `type` is `Entity`), and resolve `focus=ADR-007` to a node UUID for `seed_node_ids`
- [ ] `store.py`: `upsert_source(path, ref, type, hash, data_id)`, `source_seen(hash)`

---

## Acceptance criteria
- `uv run python -m app.ingest --reset` completes from scratch, printing counts. Re-running without `--reset` skips everything (idempotent).
- `missing_edges()` returns `[]` for these (via `GET /api/v1/datasets/{id}/graph`): `ADR-007 -affects-> svc-payments`, `ADR-007 -decided_in-> MTG-0312`, `MTG-0312 -attended_by-> priya`, `priya -member_of-> platform`, `ADR-007 -supersedes-> ADR-003`
- ≥1 LLM-extracted entity (e.g. "Priya") is aligned to canonical `Person:priya`
- `GET /graph?focus=ADR-007&depth=2` returns the neighborhood

## Exit gate
`missing_edges()` returns `[]` for the showcase path and `ADR-007 supersedes ADR-003`. If cognify keeps dropping an edge, switch that edge's check to app.db metadata instead of the graph.

## If behind
Cut alignment to exact-name matching only. Reduce the seed to 5 ADRs, 8 tickets and 5 meetings, but keep the showcase chain and one superseded ADR.
