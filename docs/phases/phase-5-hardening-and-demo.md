# Phase 5: Hardening, docs and demo

> **Goal:** nothing fails in front of judges, and every rubric line has a prepared answer.
> **Tracks:** Quality, All · **Est:** 1.5 h (+ the 4:30–5:00 window after mentoring) · **Depends on:** P4
> ← [Phase 4](phase-4-differentiators.md) · back to [plan.md](../plan.md)

---

## Reliability (Backend + Cognee)
- [ ] **Demo reset:** after the final seed ingest, freeze the `acme` dataset (no more re-ingest) and back up `app.db` → `snapshots/demo/`; `scripts/restore_demo.sh` deletes the `live` dataset over REST (`DELETE /api/v1/datasets/{id}`) and restores `app.db`
- [ ] **Cached fallback:** answers for the 3 scripted questions stored in `app.db`. If the live call fails or takes > 20 s, serve the cache (flagged `cached: true` in the logs, not hidden from Q&A if asked)
- [ ] Retries with backoff on Cognee Cloud 429/5xx; clear error JSON (`{error, retryable}`), no stack traces to the client
- [ ] Structured logs (JSON lines): request id, endpoint, latency, tokens, grounded
- [ ] `GET /health` reports graph node and edge counts and the last eval score (a quick pre-demo check)
- [ ] Pin: `uv.lock` committed, `package-lock.json` committed, `COGNEE_*` vars in `.env.example` (models are tenant-managed)

## Production standards (All)
- [ ] `backend`: type hints, `ruff check` clean, the 3 test files pass (`uv run pytest`)
- [ ] `frontend`: `npm run lint` + `npm run build` pass; no console errors
- [ ] No secrets in the repo; `.env.example` for both apps
- [ ] `scripts/init.sh` → one command to set up; `scripts/dev.sh` runs both servers

## Docs (Quality)
- [ ] `README.md`: problem (2 lines), architecture image (`docs/architecture.png`), quickstart (3 commands), demo script, eval result, decision log (link to `plan.md §4`), cut list
- [ ] Update `docs/architecture.md` and the diagram: add contradiction detection (P4) and remove the resolved ⚠️ markers

## Pitch material
### Slides (max 6)
1. **Problem:** "Company knowledge doesn't just go missing, it goes stale. A wrong answer delivered confidently is worse than none."
2. **Demo** (live)
3. **Architecture:** `architecture.png` (hybrid ingest → Cognee → grounded `/ask`)
4. **Design decisions:** D1–D8 table (mentoring round focus)
5. **Reliability + scale:** eval score, grounded-or-refuse, frozen dataset/fallback; scale path (dedicated tenant or self-hosted Cognee, `node_set` tenancy, incremental ingest, first bottleneck = LLM extraction cost)
6. **Scope:** MVP / cut / next

### Mentoring round (5 min pitch + 2 min Q&A): emphasise
Problem Clarity → slide 1 · Design Decisions → slide 4 · Scalability → slide 5 · Technical Implementation → quick demo · Scope → slide 6

### Judging round (1 + 2 + 2 min): emphasise
Production standards, architecture, completeness (PS checklist), reliability (eval + refusal + fallback)

### Prepared Q&A answers
| Likely question | Answer, in short |
|---|---|
| Why not plain RAG? | Vector search can't traverse Decision → Meeting → Person → Team; graph context gives the *why* and the *who* together |
| What if cognify extracts wrong entities? | The demo path uses structural edges generated from metadata and verified in the graph at ingest; LLM entities are aligned to canonical IDs; the eval catches regressions |
| How does it scale? | Dedicated Cognee Cloud tenant, or self-hosted Cognee with Neo4j/pgvector; ingest is incremental by hash; `node_set` per team for access; the bottleneck is LLM extraction cost, kept low because structural edges are short canonical triples |
| How do you prevent hallucinations? | Grounded-or-refuse guard in code, evidence only from ingested sources, 0 hallucinated sources in eval |
| Contradiction false positives? | Candidates are bounded to active decisions on the same service; the LLM judge has a confidence threshold; tested with a non-conflicting doc |
| Cost per query? | ~8 s per graph query (P0); tokens are billed on the tenant, measure via `/api/v1/sessions/cost-by-model`; cached embeddings |

## Rehearsal
- [ ] Run the [demo script](../plan.md#7-demo-script-2-minutes-judging-round) **3 times clean** from `restore_demo.sh`
- [ ] Time it: ≤ 2:00
- [ ] Record a backup screen video of one clean run
- [ ] Pre-demo checklist: backend up, `/health` green, snapshot restored, browser zoom 125%, notifications off, MTG-0402 file on the desktop

## 4:30–5:00 (after mentoring)
- [ ] Apply only **small**, low-risk mentor feedback (copy, UI emphasis, slide order)
- [ ] Re-run eval + one rehearsal → freeze

## Acceptance criteria
- Clean rehearsal ×3; backup video exists; README quickstart works on a fresh clone
- Every item in [plan.md §8](../plan.md#8-definition-of-done-ps-2-completeness) is ticked
