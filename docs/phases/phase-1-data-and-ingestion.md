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
  "teams":  [{"id": "platform", "name": "Platform", "lead": "priya", "owns": ["svc-payments", "svc-ledger", "svc-auth"]}]
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
**Meeting (markdown)**: frontmatter `{id, date, title, attendees, decisions: [ADR-…]}` (+ optional `proposals: [{affects, summary}]`, used by `live/MTG-0402.md`) + transcript lines `Name: text`. `title` matters: cognify names meetings by title ("architecture sync"), and the alias index maps it back

### Tasks
- [x] Write the "story bible" first: 5 services, 9 ADRs (ADR-003→007 and ADR-005→009 superseded), and who decided what
- [x] Author the files. **Every person and service reference uses canonical IDs or declared aliases.**
- [x] Embed the showcase chain: `svc-payments ← ADR-007 → MTG-0312 → priya → platform` plus TCK-142
- [x] Embed ≥3 more multi-hop answers for the eval set (e.g. "who owns the service affected by TCK-118?")
- [x] Add 2–3 "noise" docs, so retrieval has to discriminate
- [x] `data/live/MTG-0402.md`: Arjun proposes moving payments to DynamoDB "for scale", with no mention of ACID. It must contradict ADR-007.
- [x] `data/seed/README.md`: the story bible (people, services, decision timeline). Also feeds the eval answers.

---

## Cognee track: `backend/app/ingest/`

### Structural edges as canonical triples (S3: no custom DataPoints in Cognee Cloud)
Metadata becomes one text line per edge, with **raw IDs**, sent via `/add` with `node_set=["structural"]` (one triples doc per source file). Canonical `Type:id` only exists after alias resolution in `align.py`:
```text
ADR-007 affects svc-payments.
ADR-007 decided_in MTG-0312.
MTG-0312 attended_by priya.
priya member_of platform.
ADR-007 supersedes ADR-003.
platform led_by priya.
```
Labels: `member_of`, `owns`, `led_by` (org) · `affects`, `decided_in`, `owned_by`, `supersedes` (ADR) · `assigned_to`, `about`, `references` (ticket) · `attended_by`, `produced` (meeting).
`cognify` turns these into graph edges (the spike reproduced `affects` / `owned_by`), but the LLM picks node names and edge labels, so **every expected triple is checked against `/graph` after cognify** (`missing_edges`). Node properties can't be set through `/add`: evidence maps each retrieved chunk's `data_id` → `sources` row (path, ref). Optional: pass a `graphModel` JSON schema to `/cognify` if node typing is needed.

### Tasks
- [x] `loaders.py`: parse md frontmatter (`python-frontmatter` or a tiny YAML split), JSON; normalize IDs through the alias table; compute `sha256` of the content
- [x] `structural.py`: records → canonical triples (above) → `cognee_client.add_structural(triples, dataset)`; keep the list of expected triples for the check
- [x] `semantic.py`: render each doc as transcript-shaped text with a header (`[MEETING MTG-0312 2026-03-12] attendees: …`), then `cognee_client.add_text(text, node_set=[source_type], dataset=COGNEE_DATASET)` → store the returned `data_id` in `sources`
- [x] `cognee_client.build(dataset)` → `/cognify` (`runInBackground: false`) once after the batch
- [x] `align.missing_edges(expected, graph, aliases)` → match on node name (case-insensitive) + edge label; any missing → re-add that triple once, then fail loudly
- [x] `align.py`: after cognify, map LLM Entity names → canonical IDs via aliases (case-insensitive exact + alias). Store the mapping in the `app.db` `aliases` table (S3: no custom graph edges).
- [x] `app/ingest/__main__.py`: `uv run python -m app.ingest [--reset] [path]` (`--reset` = `DELETE /api/v1/datasets/{id}` + clear `sources` / `aliases`):
  1. hash check against `sources` (skip unchanged)
  2. structural → semantic → cognify → `missing_edges` check → align
  3. print stats: nodes and edges per type, time taken, tokens if available

---

## Backend track
- [x] `POST /ingest` → runs the same pipeline for `data/seed` (batch; a lock returns 409 on overlap). Single-file upload is P4
- [x] `GET /sources` → rows from the `sources` table
- [x] `GET /graph?focus=&depth=` → `align.graph()` → `{nodes:[{id,type,label}], edges:[{from,to,rel}]}`: canonical IDs via the alias index, walking **Entity→Entity edges only** (the server's `seed_node_ids` walk goes through NodeSet/EntityType/chunk hubs: depth 2 returned ~80% of the graph)
- [x] `store.py`: `upsert_source(path, ref, type, content_hash, data_id, triples_data_id)` (written only after cognify succeeds), `get_source(path)`, `list_sources()`, `set_aliases` / `get_aliases`, `reset_ingest_state()`

---

## Acceptance criteria
- `uv run python -m app.ingest --reset` completes from scratch, printing counts. Re-running without `--reset` skips everything (idempotent).
- `missing_edges()` returns `[]` for these (via `GET /api/v1/datasets/{id}/graph`): `ADR-007 -affects-> svc-payments`, `ADR-007 -decided_in-> MTG-0312`, `MTG-0312 -attended_by-> priya`, `priya -member_of-> platform`, `ADR-007 -supersedes-> ADR-003`
- ≥1 LLM-extracted entity (e.g. "Priya") is aligned to canonical `Person:priya`
- `GET /graph?focus=ADR-007&depth=2` returns the neighborhood

## Exit gate
`missing_edges()` returns `[]` for the showcase path and `ADR-007 supersedes ADR-003`. If cognify keeps dropping an edge, switch that edge's check to app.db metadata instead of the graph.

## Results (2026-09-19, Cognee Cloud dataset `snow`)
| Metric | Value |
|---|---|
| Files | 33 seed (1 org chart, 9 ADRs, 15 tickets, 8 meetings) + `live/MTG-0402.md` |
| Fresh ingest (`--reset`) | ~4.5–5 min (66 `/add` calls, 5 parallel, one synchronous cognify) |
| Re-run | 33 skipped in ~5 s (idempotent by content hash) |
| Graph | 430 nodes / 1,676 edges; 173 Entity nodes |
| Structural edges found | **124/125**; showcase + supersedes **5/5** |
| Aligned LLM entities | 61 (e.g. `priya`, `priya sharma` → `Person:priya`) |
| Checks | `uv run python -m tests.test_ingest` (offline: triples, aliases, missing_edges, focus walk) |

### Findings
- **cognify renames entities**: lowercases, and turns `MTG-0312` into "architecture sync" and `svc-payments` into "payments". Every graph lookup goes through the `aliases` table (IDs, display names, declared aliases, titles).
- **Edge labels mostly survive** when written as triples, but **`leads` was dropped 3/3**. Rewritten as `Team led_by Person` + an org-chart text doc; now found.
- **The LLM still loses and invents edges**: `MTG-0129 attended_by arjun` is missing, and the first run produced `nora works_for data` (wrong). This is why the demo path is checked, not assumed.
- **Content-hash idempotency doesn't notice pipeline-code changes**: after changing `structural.py` / `semantic.py`, run `--reset`.
- Parallel `/add` to a **new** dataset races (409 permission error); `ensure_dataset()` creates it first.

## If behind
Cut alignment to exact-name matching only. Reduce the seed to 5 ADRs, 8 tickets and 5 meetings, but keep the showcase chain and one superseded ADR.
