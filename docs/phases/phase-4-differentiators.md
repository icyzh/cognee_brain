# Phase 4: Differentiators (contradiction detection, live ingest, eval)

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
      semantic:   LLM pass "list decisions/proposals in this text as {service, claim}"
  → candidates = ACTIVE decisions (status=accepted, not superseded) affecting the SAME service   ← deterministic, bounded
  → for each (claim, candidate): LLM judge → {contradicts: bool, confidence, reason}
  → contradicts && confidence ≥ 0.7 → alert
```

### Backend / Cognee tasks: `backend/app/analysis/contradictions.py`
- [ ] `extract_claims(doc) -> list[Claim{service_id, text, source_ref}]` (frontmatter first; LLM fallback with a strict JSON schema)
- [ ] `candidates(service_id) -> list[Decision]` from the structural graph (active only)
- [ ] `judge(claim, decision) -> Verdict`: one direct OpenAI call (`httpx` → `/v1/chat/completions`, `LLM_MODEL` + `LLM_API_KEY` from `.env`; Cognee Cloud's model is hidden behind its proxy, so the judge uses a model we can name and pin), temperature 0, JSON output; prompt includes both texts and asks for a one-sentence reason
- [ ] Persist to `alerts` (`kind='contradiction', new_ref, existing_ref, service, reason, confidence, created_at`) (app.db only; P0 S3: no custom graph edges in Cognee Cloud)
- [ ] Also persist `kind='stale'` alerts for every superseded decision at batch ingest (cheap, deterministic)
- [ ] `GET /alerts` → newest first
- [ ] `/ask` integration: if the path/evidence touches a decision with an open contradiction alert → add a `warnings[]` item `kind: contradiction`
- [ ] Test: `test_contradictions.py`, where `candidates()` returns only same-service active decisions (no LLM)

### Guardrails
- Never compare against superseded decisions (they are already stale)
- Cap judge calls per ingest (e.g. ≤ 10) → bounded cost; log the count

---

## 4B: Live ingest

### Backend
- [ ] `POST /ingest` multipart single file → the same pipeline as batch, **but add the new doc to a separate `live` dataset and cognify only that** (`/cognify` is scoped by dataset, not node_set) → then contradictions → response `{source_ref, nodes_added, alerts: [...] , took_ms}`
- [ ] Rebuild the in-memory adjacency for `paths.py` after ingest
- [ ] Measure: a single meeting file end-to-end should take ≤ 30 s. If slower, pre-warm by running the extraction LLM call on upload and show progress.

### Frontend: `app/alerts/page.tsx`
- [ ] Dropzone / file input → `ingestFile()` → progress steps: *parsing → structural → cognify → checking contradictions*
- [ ] Alert feed: red cards `MTG-0402 contradicts ADR-007`, with reason, service, people involved (owner and raiser, from the graph), and a "view evidence" link to both sources
- [ ] Stale alerts in amber below
- [ ] Nav badge with the count of open alerts

---

## 4C: Eval, shown in the UI

### Quality track: `backend/eval/`
- [ ] `questions.json`, 10 items:
  ```json
  {"q": "Why is payments on Postgres, and who owns it now?",
   "expect_refs": ["ADR-007", "MTG-0312"], "expect_path_end": "platform", "expect_grounded": true}
  ```
  Mix: 5 multi-hop, 2 single-hop facts, 2 refusals (not in the corpus), 1 stale-decision question
- [ ] `run_eval.py`: calls the `/ask` pipeline in-process; scores
  - **grounded correct** (matches `expect_grounded`)
  - **ref recall** (expected refs ⊆ evidence refs)
  - **hallucinated sources** (evidence refs not in `sources`), which must be 0
  - **path end correct**
  → writes a summary + per-question rows to `eval_runs`
- [ ] `GET /eval/latest` → `{run_at, grounded_ok: 9, total: 10, hallucinated_sources: 0, ref_recall: 0.93}`

### Frontend
- [ ] `EvalBadge` on the Ask page: `Eval 9/10 grounded · 0 hallucinated sources`; click → per-question table

---

## Acceptance criteria
- Drop `data/live/MTG-0402.md` in the UI → a red contradiction alert (vs ADR-007) appears in ≤ 30 s, with a correct one-line reason
- Re-ask the showcase question → it now includes the `contradiction` warning
- Ingesting a non-conflicting doc raises **no** alert (false-positive check)
- `uv run python -m eval.run_eval` → ≥ 9/10, 0 hallucinated sources; the badge shows it

## Exit gate
Demo steps 3–5 of the [plan's demo script](../plan.md#7-demo-script-2-minutes-judging-round) work end to end.

## If behind (in order)
1. Skip the LLM claim extraction and use frontmatter `decisions/affects` only (the demo file has frontmatter)
2. Eval: run the CLI only and put the number on a slide instead of the UI badge
3. Live ingest: pre-ingest MTG-0402 and show the alert feed only (lose the "live" moment, keep contradiction)
