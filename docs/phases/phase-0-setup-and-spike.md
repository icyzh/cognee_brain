# Phase 0: Setup + Cognee spike

> **Goal:** remove the biggest unknown first. Confirm how the pinned Cognee version actually behaves before building on it.
> **Tracks:** Cognee, Backend · **Est:** 1–1.5 h · **Depends on:** nothing · **Unblocks:** P1, P3 (mock)
> ← [plan.md](../plan.md) · next → [Phase 1](phase-1-data-and-ingestion.md)

---

## Cognee track

### Tasks
- [x] `cd backend && uv add cognee` and record the exact version in the table below
- [x] `backend/.env` (gitignored) + `backend/.env.example`:
  ```env
  # Cognee Cloud (used by the app)
  COGNEE_SERVICE_URL=https://<tenant>.aws.cognee.ai   # dashboard → API Keys → API Base URL
  COGNEE_API_KEY=...
  COGNEE_DATASET=snow
  # Our own model: P4 contradiction judge + local-mode spike (Cognee Cloud ignores these)
  LLM_PROVIDER=openai
  LLM_MODEL=gpt-5.6-luna
  LLM_API_KEY=...
  EMBEDDING_PROVIDER=openai
  EMBEDDING_MODEL=text-embedding-3-small
  ENABLE_BACKEND_ACCESS_CONTROL=false
  ```
- [x] `backend/spike/spike_cognee.py` (local SDK) + `backend/spike/spike_cloud.py` (Cognee Cloud REST): throwaway scripts that answer every question below on 3 tiny texts

### Spike questions (fill in the answers; they drive the design)

| # | Question | Answer | Fallback if "no" |
|---|---|---|---|
| S1 | Is `remember()` available, or only `add()` + `cognify()`? | Yes, `POST /api/v1/remember` and `/add` + `/cognify` both exist. `remember` also runs `improve` (extra LLM calls) | **Chosen:** `/add` + `/cognify`: explicit, per-step timing |
| S2 | Does `add()`/`remember()` accept `node_set=[...]`? | Yes. `/add` multipart field `node_set`, filtered with `/search` `nodeName: [...]`, verified. **The SDK's cloud client drops `node_set`**, so call REST directly | Not needed |
| S3 | Can custom `DataPoint` subclasses with relationship fields be stored via `add_data_points` (import path?) | **No in cloud.** `add_data_points` is in-process only, with no REST route. Rendering triples as text (`Decision:ADR-007 affects Service:payments.`) into `/add` produced matching `affects` / `owned_by` edges, but they go through the LLM, so they are not guaranteed | **Chosen:** text triples into `/add` (node_set `structural`), plus a P1 check that each expected edge exists in `/graph`. Optional: `/cognify` `graphModel` JSON schema to type the nodes |
| S4 | `recall()` vs `search()`: which exists, and what are the signatures? | Both: `POST /api/v1/search` `{query, searchType, datasets, nodeName, topK, onlyContext, contextFormat, sessionId, verbose, includeReferences}` and `/recall` | **Chosen:** `/search` with `searchType: GRAPH_COMPLETION` |
| S5 | Can we get the **context triplets / source objects** behind a `GRAPH_COMPLETION` answer (`verbose`, `only_context`, `include_references`)? | Yes. `verbose: true` → `[{text_result, context_result, objects_result, evidence}]`. `objects_result` = JSON triplets `{node1: {node_id, node_attributes{type, name, text}}, node2, ...}`. `includeReferences` appends chunk/data IDs to the answer. **Always send a fresh `sessionId`**: the default session injects earlier Q&A into the prompt (verified) | Not needed |
| S6 | How do we read the full graph (nodes + edges) for `/graph` and path extraction? | `GET /api/v1/datasets/{id}/graph` → `{nodes[{id, label, type, properties}], edges[{source, target, label}]}`. Params `seed_node_ids`, `neighborhood_depth`, `max_nodes` give a focused read (seed + depth 2 → 7 nodes / 13 edges) | Not needed |
| S7 | Time and tokens for `cognify` on 1 small doc? For one `GRAPH_COMPLETION` query? | Cloud model: `/add` of 4 tiny texts 14.2 s, `/cognify` 22 s with `runInBackground: false` (~5 s per doc). GRAPH_COMPLETION 7.5–9.5 s, `onlyContext` 5.3 s. Tokens not measured | Build the graph before the demo. Measure tokens in P5 |
| S8 | Does re-adding the same content dedupe? | Yes. Re-adding identical content keeps 4 data items and 40 nodes / 97 edges unchanged | Keep the `sources` hash table anyway, to skip uploads and cognify calls |
| S9 | Default node types created by `cognify` (DocumentChunk, Entity, EntityType, TextSummary?) | `TextDocument`, `DocumentChunk`, `TextSummary`, `Entity`, `EntityType`, `NodeSet`. Custom types only via `graphModel` | Update the diagram's 3b section |

### Pinned facts
| Item | Value |
|---|---|
| cognee version | 1.6.0 SDK (pinned in `uv.lock`), used against **Cognee Cloud** REST (`COGNEE_SERVICE_URL`, `X-Api-Key`) |
| LLM model / TPM | Cognee Cloud: hidden behind `litellm_proxy/litellm` (per `/sessions/cost-by-model`, $0 billed). Ours: gpt-5.6-luna for the P4 judge / TPM unknown |
| embedding model / dims | Cloud tenant's default / not exposed |
| cognify time per doc | ~5 s (tiny docs, synchronous) |
| query latency p50 | ~8 s GRAPH_COMPLETION |

Local mode (SDK in-process, gpt-5.6-luna) was spiked first: same answers, except S3 works natively via `add_data_points` and S6 via `get_graph_engine()`. Queries took ~3.6 s. See `backend/spike/spike_cognee.py`.

---

## Backend track

### Tasks
- [x] `backend/app/config.py`: loads `.env` (pydantic-settings or `os.environ`), exposes paths (`DATA_DIR`, `APP_DB`) and `COGNEE_SERVICE_URL` / `COGNEE_API_KEY` / `COGNEE_DATASET`
- [x] `backend/app/main.py`: FastAPI app, CORS for `http://localhost:3000`, `GET /health` → `{status, cognee_version, cognee_configured, dataset, llm_model}`
- [x] `backend/app/cognee_client.py` stub with the final function signatures (bodies filled in P1/P2):
  ```python
  async def add_structural(triples: list[tuple[str, str, str]], dataset: str, filename: str | None = None) -> str: ...  # text triples → /add; data_id
  async def add_text(text: str, node_set: list[str], dataset: str, filename: str | None = None) -> str: ...  # /add; data_id
  # P1 added: ensure_dataset, dataset_id, delete_dataset, delete_data (REST helpers)
  async def build(dataset: str) -> None: ...                                              # /cognify
  async def ask(question: str) -> RawResult: ...     # /search GRAPH_COMPLETION verbose: answer + triplets + chunks
  async def graph_dump(dataset, **params) -> GraphDump: ...          # /datasets/{id}/graph (raw); canonical view + missing_edges live in ingest/align.py (P1)
  ```
- [x] `backend/app/store.py`: `sqlite3` connection + `init_db()` creating `sources, aliases, qa_log, feedback, alerts, eval_runs`
- [x] Update `scripts/init.sh` if new setup steps are needed

## Frontend track (parallel, small)
- [x] Write `frontend/src/lib/types.ts` with the `/ask` response contract (the frozen [P2 contract](phase-2-query-pipeline.md), mirrored in [architecture.md §4](../architecture.md))
- [x] `frontend/src/lib/mock.ts`: a mock response for the showcase question, so P3 can start without the backend

---

## Acceptance criteria
- `uv run uvicorn app.main:app --port 8000` → `GET /health` returns 200 with the cognee version
- Spike table S1–S9 is fully answered, and fallbacks are chosen where needed
- `architecture.md` ⚠️ markers are updated (remove or replace confirmed ones)

## Exit gate
**Do not start P1 until S3, S4 and S5 are answered.** They decide how ingestion and evidence work.

## If behind
Skip S7–S9 measurements and use defaults. Measure again in P5.
