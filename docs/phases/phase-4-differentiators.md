# Phase 4: Differentiators (contradiction detection, live ingest, eval + baseline, agent access)

> **Goal:** the moments judges remember: the brain **notices when company knowledge contradicts itself**, updates live, and **proves its reliability with a number**.
> **Tracks:** Cognee, Backend, Frontend, Quality · **Est:** 2 h · **Depends on:** P2, P3 · **Unblocks:** P5
> ← [Phase 3](phase-3-frontend.md) · next → [Phase 5](phase-5-hardening-and-demo.md)

---

## 4A: Contradiction detection

### Design (decision D6)
```
new doc ingested
  → extract its decision claims
      structural: frontmatter `decisions`, `affects`
      (semantic LLM extraction deferred: see the ponytail note in contradictions.py)
  → candidates = ACTIVE decisions (status=accepted, not superseded) affecting the SAME service   ← deterministic, bounded
  → for each (claim, candidate): LLM judge → {contradicts: bool, confidence, reason}
  → contradicts && confidence ≥ 0.7 → alert
```

### Backend / Cognee tasks: `backend/app/analysis/contradictions.py`
- [x] `extract_claims(doc) -> list[Claim{service_id, text, source_ref}]` (frontmatter `proposals` / `decisions` only; LLM fallback deferred)
- [x] `candidates(service_id) -> list[Decision]` from the structural graph (active only)
- [x] `judge(claim, decision) -> Verdict`: one direct OpenAI call (`httpx` → `/v1/chat/completions`, `LLM_MODEL` + `LLM_API_KEY` from `.env`; Cognee Cloud's model is hidden behind its proxy, so the judge uses a model we can name and pin), default temperature (gpt-5.6-luna rejects 0), JSON output, uploaded text fenced in `<document>` against prompt injection; prompt includes both texts and asks for a one-sentence reason
- [x] Persist to `alerts` (`kind='contradiction', new_ref, existing_ref, service, reason, confidence, created_at`) (app.db only; P0 S3: no custom graph edges in Cognee Cloud)
- [x] Also persist `kind='stale'` alerts for every superseded decision at batch ingest (cheap, deterministic)
- [x] `GET /alerts` → newest first
- [x] `/ask` integration: if the path/evidence touches a decision with an open contradiction alert → add a `warnings[]` item `kind: contradiction`
- [x] Test: `test_contradictions.py`, where `candidates()` returns only same-service active decisions (no LLM)

### Guardrails
- Never compare against superseded decisions (they are already stale)
- Cap judge calls per ingest (e.g. ≤ 10) → bounded cost; log the count

---

## 4B: Live ingest

### Backend
- [x] `POST /ingest` multipart single file → same pipeline, **same dataset** (cognify is incremental, so it only processes the new file; /ask, /graph and paths keep reading one dataset). Contradiction check runs alongside `/add`; the response returns after add + judge (~8 s) with `graph_status: "building"`, and cognify + path refresh finish in the background under the ingest lock (`GET /ingest/status`)
- [x] Rebuild the in-memory adjacency for `paths.py` after ingest
- [x] Measure: ~38 s end to end (cognify ~22 s) → the response returns after add + judge: **alert in ~8 s**, graph in the background

### Frontend: `app/alerts/page.tsx`
- [x] Dropzone / file input → `ingestFile()` → progress steps: *parsing → adding to Cognee → checking contradictions* (then "graph updating in the background")
- [x] Alert feed: red cards `MTG-0402 contradicts ADR-007`, with reason, service, people involved (owner and raiser, from document frontmatter), and a "view evidence" link to both sources
- [x] Stale alerts in amber below
- [x] Nav badge with the count of open alerts

---

## 4C: Eval, shown in the UI

### Quality track: `backend/eval/`
- [x] `questions.json`, 10 items:
  ```json
  {"q": "Why is payments on Postgres, and who should I talk to about it now?",
   "expect_refs": ["ADR-007", "MTG-0312"], "expect_path_end": "platform", "expect_grounded": true}
  ```
  Mix: 5 multi-hop, 2 single-hop facts, 2 refusals (not in the corpus), 1 stale-decision question
- [x] `run_eval.py`: calls `app.query.ask.ask()` in-process, **after `store.init_db()` and `await paths.refresh()`** (the FastAPI lifespan doesn't run, so without it `path` is always `[]` and no stale warnings fire); eval rows go to `qa_log` too (fine: tagged by question); scores
  - **grounded correct** (matches `expect_grounded`)
  - **ref recall** (expected refs ⊆ evidence refs)
  - **hallucinated sources** (evidence refs not in `sources`), which must be 0
  - **path end correct**
  → writes a summary + per-question rows to `eval_runs`
- [x] **Baseline comparison** (`run_eval.py --baseline`): the same 10 questions through **raw Cognee** (`cognee_client.ask(q, system_prompt=None)`: Cognee's default prompt, no NOT_FOUND rule, no guard / supersede / path layers), scored the same way; plus **stale flagged** (does the answer mark ADR-003 as superseded?) and **refused** (does it decline out-of-corpus questions?). Both variants are scored on the IDs cited in the answer text; `grounded` is our flag vs a refusal-wording regex for raw. Stored as `eval_runs.variant = 'raw_cognee'` vs `'decision_brain'`
  → answers "isn't this just a Cognee wrapper?" with numbers, not claims
- [x] `GET /eval/latest` → `{decision_brain: {run_at, grounded_ok: 10, total: 10, hallucinated_sources: 0, ref_recall: 1.0, stale_flagged: 2, stale_total: 2, path_ok: 5, path_total: 5, results: [...]}, raw_cognee: {…same fields…}}`

### Frontend
- [x] `EvalBadge` on the Ask page: `Eval 10/10 grounded · 0 hallucinated sources`; click → per-question table with a **raw Cognee vs Permafrost** column pair, plus verified-path and stale columns

---

## 4D: Agent access (PS-2: "humans, agents, and applications")
`/ask` is already the application API; this makes the same brain usable by an agent, with no new logic.

- [x] `backend/mcp_server.py`: `uv add mcp`, one `MCPServer` (mcp 2.x, `mcp.server.mcpserver`; FastMCP was renamed) stdio server with one tool, `ask_company_brain(question) -> dict`, that POSTs to `http://localhost:8000/ask` (httpx timeout 45 s: `/ask` takes 10–16 s, ≤ 23 s budget incl. retry) and returns the response unchanged (answer, evidence, path, warnings)
- [x] `.mcp.json` at the repo root registering it (`uv run --directory backend python mcp_server.py`), so Claude Code / any MCP client picks it up
- [x] README: a 3-line "Use from an agent" section

---

### Carried over from the P1 audit
- [x] Claims for the live file come from `proposals[].affects` (MTG-0402 has `decisions: []`); `structural.triples` now emits `MTG-0402 proposes_change_to svc-payments`
- [x] Not needed: the live file goes into the same `snow` dataset (see 4B)
- [x] `POST /ingest` currently returns ingest stats; the P4 upload variant should add `alerts: [...]`. The frontend `ingestFile()` posts a file with a 60 s timeout, so don't wire it until the upload route exists

## Results (2026-09-19)
| Check | Result |
|---|---|
| Drop MTG-0402 | alert `MTG-0402 contradicts ADR-007` (confidence 0.99, correct reason) in **7.4–8.4 s**; people = priya (owner), arjun (raiser); graph finishes ~15–30 s later |
| Non-conflicting doc (notify retry tuning) | no alert (the 3 other svc-payments candidates were also judged non-conflicting for MTG-0402) |
| Re-ask showcase | warnings `stale ADR-003` + `contradiction ADR-007` (immediately, from `alerts`) |
| Eval, ours | **10/10 grounded · ref recall 1.0 · stale 2/2 · path 5/5 · 0 hallucinated sources** |
| Eval, raw Cognee | 9/10 grounded (answered the off-corpus question) · ref recall 0.55 · stale 1/2 · path 0/5 · 0 hallucinated |
| MCP | `ask_company_brain` returns the same answer, path, warnings and evidence as the UI |
| Offline checks | `tests.test_contradictions` (4), `tests.test_ask` (9), `tests.test_ingest` (6) |
| Demo reset | `uv run python -m app.ingest --forget ../data/live/MTG-0402.md` |

### Findings
- **gpt-5.6-luna rejects `temperature: 0`** (only the default is allowed). The judge relies on a strict JSON shape, deterministic candidates and a 0.7 threshold instead.
- **Live ingest time is mostly Cognee**: cognify ~22 s, two `/add` ~6 s, each graph dump ~6 s. The alert doesn't need the graph, so the response no longer waits for it (38 s → ~8 s).
- **The eval found two real gaps, both fixed**: (1) ID-centric questions retrieve a file's small triples doc, which held no status/date/title ("status of TCK-142?" was refused by both variants) → key metadata is now written as fact sentences in the triples doc; (2) questions naming no service/decision had no path anchor → the decision the answer cites anchors it. The idempotency path now shows `marco member_of platform` even though the LLM's prose said "svc-payments team".
- **Cognee Cloud slows sharply under concurrent searches** (2 in flight → a 23 s timeout; 6 → most time out). The eval runs one question at a time; the demo should too.
- **Transient `/add` failures** (409 "connection was closed in the middle of operation") killed a fresh ingest once; `add_text` now retries 409/429/5xx/transport errors 3× with backoff.

## Acceptance criteria
- Drop `data/live/MTG-0402.md` in the UI → a red contradiction alert (vs ADR-007) appears in ≈ 8 s (measured 7.4–8.7 s), with a correct one-line reason
- Re-ask the showcase question → it now includes the `contradiction` warning
- Ingesting a non-conflicting doc raises **no** alert (false-positive check)
- `uv run python -m eval.run_eval` → ≥ 9/10, 0 hallucinated sources; the badge shows it
- `uv run python -m eval.run_eval --baseline` → raw Cognee scores recorded; Permafrost beats it on stale flagged and refusals (if it doesn't, that's a finding to fix, not hide)
- An MCP client (e.g. Claude Code) calls `ask_company_brain` with the showcase question and gets the same answer, evidence and path as the UI

## Exit gate
Demo steps 3–5 of the [plan's demo script](../plan.md#7-demo-script-2-minutes-judging-round) work end to end.

## If behind (in order)
0. Cut 4D (agent access) first; mention it on the scalability slide instead
1. Skip the LLM claim extraction and use frontmatter `decisions/affects` only (the demo file has frontmatter)
2. Eval: run the CLI only (both variants) and put the comparison table on a slide instead of the UI badge
3. Live ingest: pre-ingest MTG-0402 and show the alert feed only (lose the "live" moment, keep contradiction)
