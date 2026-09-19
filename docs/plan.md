# Permafrost: Build Plan

> A mini Company Brain on Cognee. It answers **why** a decision was made, **who** owns it now and **what** it affects. It shows evidence and the exact multi-hop path, and **flags stale or contradictory company knowledge**.
>
> Related: [`PS.md`](../PS.md) · [`architecture.md`](architecture.md) · [`architecture.excalidraw`](architecture.excalidraw) · [`research-winning-approaches.md`](research-winning-approaches.md)
>
> Phase files: [`phases/`](phases/)

---

## 1. Goals and success criteria

| # | Goal | Measured by |
|---|---|---|
| G1 | Meet every PS-2 requirement visibly | Completeness checklist (§8) all ✅ in the demo |
| G2 | Answers are grounded and traceable | Every answer shows evidence cards and a hop path; the system refuses when there is no context |
| G3 | Multi-hop is reliable, not luck | The showcase query returns the same 4-hop path 10/10 runs |
| G4 | Differentiator lands in ≤10 s | Live ingest of one meeting triggers a **contradiction alert** on screen |
| G5 | Reliability is measurable | Eval set ≥ 9/10 grounded, 0 hallucinated sources, shown in the UI |
| G6 | Demo never blocks on the LLM | Graph built before the demo, with a cached fallback for the scripted queries |

**Rubric mapping.** Mentoring scores Problem Clarity, Design Decisions, Scalability, Technical Implementation and Scope. Judging scores Production Standards, Technical Understanding, System Architecture, Completeness and Reliability. See [`PS.md`](../PS.md#evaluation).

---

## 2. Workstreams (tracks)

Each track owns a part of the repo. Phases (§3) cut across tracks.

### 2.1 Data track: `data/seed/`
A fictional company, **Snow Pay**, with **canonical IDs shared across every source**. This track makes or breaks the multi-hop story.

| Item | Count | Notes |
|---|---|---|
| People (`team.json`) | ~8 | id, name, aliases (`Priya`, `P. Sharma`), team |
| Teams | 3 | platform, payments-product, data |
| Services | 5 | svc-payments, svc-ledger, svc-auth, svc-notify, svc-reports |
| ADRs (`adrs/*.md`) | 9 | YAML frontmatter; **2 superseded** (ADR-003 → ADR-007, ADR-005 → ADR-009) |
| Tickets (`tickets/*.json`) | ~15 | assignee, service, refs to ADRs |
| Meetings (`meetings/*.md`) | ~8 | attendees, decisions, transcript-style lines |
| **Live-demo file** (`live/MTG-0402.md`) | 1 | **Not pre-ingested.** It proposes DynamoDB for payments, which contradicts active ADR-007. |

### 2.2 Cognee track: `backend/app/cognee_client.py` + `backend/app/ingest/`
- The **only** module that talks to Cognee: a thin httpx client for Cognee Cloud REST (`/api/v1`), so API drift stays in one file.
- Structural ingest: metadata rendered as text triples with raw IDs (`ADR-007 affects svc-payments.`; canonical `Type:id` exists only after alias resolution) via `/add` with `node_set=structural`, then verified in `/graph` after cognify (Cognee Cloud has no custom DataPoints; spike S3).
- Semantic ingest: `POST /add` with `node_set` per source type, then `POST /cognify`.
- Entity alignment: LLM entities → canonical IDs by alias table.
- Retrieval: `POST /search` with `GRAPH_COMPLETION`, `verbose: true` and a fresh `sessionId`, returning `text_result` + `objects_result` triplets.

### 2.3 Backend track: `backend/app/` (FastAPI, uv, stdlib `sqlite3`)
| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness, Cognee config, `graph {nodes, verified_edges}`, `last_eval`, `ingest_building` (pre-demo check) |
| `POST /ingest` | batch (seed dir) → stats; or multipart upload (live demo) → `{source_ref, alerts[], graph_status, took_ms}` in ~8 s, graph builds in the background |
| `GET /ingest/status` | `{building}` while a live upload's graph is being built |
| `POST /ask` | `{question}` → `{answer, evidence[], path[], warnings[], grounded, latency_ms, qa_id}` + optional `cached`, `experts[]`, `unsupported_citations[]`; `?raw=true` = plain Cognee for the side-by-side |
| `GET /history` | recent grounded answers, one per question (Ask page start state) |
| `GET /timeline?service=&as_of=` | decision history of a service: validity intervals, what was in force on a date, open contradiction proposals |
| `GET /graph` | nodes and edges for the explorer (optional `?focus=<id>&depth=2`) |
| `GET /graph/cognee` | Cognee's own rendered graph page, proxied (keeps the API key server-side) |
| `GET /sources` | every ingested item with hash, type and time |
| `GET /alerts` | contradictions and stale decisions |
| `POST /feedback` | `{qa_id, helpful, comment?}` |
| `GET /eval/latest` | latest eval run per variant: ours, Cognee + our prompt (ablation), raw Cognee |

Modules: `query/ask.py` (retrieve → guard → supersede → path), `query/paths.py`, `analysis/contradictions.py`, `analysis/timeline.py`, `store.py` (app.db), `logs.py` (JSON lines).

`app.db` tables: `sources`, `aliases`, `qa_log`, `feedback`, `alerts`, `eval_runs`.

### 2.4 Frontend track: `frontend/` (Next.js 16 App Router, Tailwind 4, npm)
| Route | Content |
|---|---|
| `/` Ask | question box, answer, stale/contradiction banners, evidence cards, hop path, feedback, eval badge |
| `/alerts` | contradiction and stale feed; live-ingest dropzone (demo trigger) |
| `/graph` | graph explorer (**stretch**) |
| `/sources` | ingested items table |

### 2.5 Quality and demo track: `backend/eval/`, `README.md`, pitch
- `eval/questions.json`: 10 questions with expected source refs and path nodes.
- `eval/run_eval.py`: scores grounding (cited refs ⊆ retrieved, expected refs hit) and path correctness, and writes to `eval_runs`.
- Freeze the demo dataset before the demo, cached answers, the demo script, and slides (decision log, architecture, cut list).

---

## 3. Phases

| Phase | Name | Tracks | Est. | Exit gate |
|---|---|---|---|---|
| [P0](phases/phase-0-setup-and-spike.md) | Setup + Cognee spike | Cognee, Backend | 1–1.5 h | Every ⚠️ API confirmed or a fallback chosen |
| [P1](phases/phase-1-data-and-ingestion.md) | Seed data + ingestion | Data, Cognee, Backend | 2–2.5 h | `uv run python -m app.ingest` builds the graph; the showcase path exists in the graph |
| [P2](phases/phase-2-query-pipeline.md) | Query pipeline `/ask` | Cognee, Backend | 2 h | The showcase question returns a grounded answer, evidence, the 4-hop path and a stale warning via curl |
| [P3](phases/phase-3-frontend.md) | Frontend Ask experience | Frontend | 2 h | End-to-end demo in the browser |
| [P4](phases/phase-4-differentiators.md) | Contradictions + live ingest + eval + MCP agent tool | All | 2–2.5 h | Dropping `MTG-0402.md` raises an alert in ~8 s; eval badge shows 10/10 vs raw Cognee's 9/10 |
| [P5](phases/phase-5-hardening-and-demo.md) | Hardening, docs, pitch | Quality, All | 1.5 h | Demo rehearsed 3× clean; README and slides done |

> Estimates are focused-work hours for a small team. **Backend and frontend can run in parallel from P2 onward** (frontend builds against the `/ask` contract with a mock JSON).

```mermaid
flowchart LR
    P0["P0 Setup + spike"] --> P1["P1 Data + ingestion"]
    P1 --> P2["P2 /ask pipeline"]
    P0 --> P3a["P3 Frontend on mock JSON"]
    P2 --> P3b["P3 Frontend on live API"]
    P3a --> P3b
    P2 --> P4["P4 Contradictions + live ingest + eval + agent"]
    P3b --> P4
    P4 --> P5["P5 Hardening + demo"]
```

### Event checkpoints
| When | Must be true |
|---|---|
| **Before mentoring (3:30 PM)** | P0–P3 done; P4 at least contradiction detection working via curl. Slides: problem, architecture, decision log, cut list. |
| **Mentoring (3:30–4:30)** | 5-min pitch focused on **design decisions, scalability, scope**. Write down every mentor question. |
| **4:30–5:00** | Fold in mentor feedback (small changes only), finish P5 rehearsal, freeze the graph snapshot. |
| **Judging (5:00–6:00)** | 1-min pitch, 2-min demo (script in P5), 2-min Q&A. |

---

## 4. Key design decisions (for the decision-log slide)

| # | Decision | Alternative rejected | Why |
|---|---|---|---|
| D1 | **Hybrid graph**: structural edges generated from metadata (canonical triples, verified in `/graph`) + `cognify` LLM edges | Pure `cognify` | Entity-resolution errors compound per hop (85% per hop → 44% at 5 hops). The demo path must be checked, not hoped for. |
| D2 | Cognee as the knowledge layer | Plain vector RAG | Vector search cannot follow Decision → Meeting → Person → Team |
| D3 | Cognee Cloud (managed stores + model) + SQLite `app.db` | Local Kùzu / LanceDB | No infra to run; the local SDK was spiked as a fallback |
| D4 | `node_set` per source type | One undifferentiated dataset | Provenance, filtering, a future per-team access path |
| D5 | Grounded-or-refuse | Always answer | A wrong answer delivered confidently is the core risk of a company brain |
| D6 | Contradiction = deterministic candidates (same service, active decision) + LLM judge | LLM compares everything | Bounded cost O(new × related), explainable, testable |
| D7 | One wrapper module for cognee | cognee calls everywhere | REST and SDK drift (the 1.6.0 SDK cloud client drops `node_set` / `sessionId`) is isolated to one file |
| D8 | App state in stdlib `sqlite3` | ORM / Postgres | Repo convention; the prototype scale fits |

---

## 5. Scope

| MVP (must) | Stretch (if time) | Cut (say so in the pitch) |
|---|---|---|
| 4 source types, canonical IDs | Graph explorer page | Real Slack/Jira connectors |
| Hybrid ingest, hash dedupe | Retrieval router (CHUNKS vs GRAPH) | Auth / permissions |
| `/ask` with evidence, path, stale warning, refusal | Multi-turn chat memory | Graph editing UI |
| Contradiction detection + live ingest | `memify` / feedback-driven refinement | Cloud deploy with autoscaling |
| Eval set + badge | Deployed URL | Voice or other extra modalities |
| Graph built before the demo + cached fallback | | |

---

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation | Owner phase |
|---|---|---|---|---|
| ~~Cognee API differs from the docs~~ **Resolved in P0**: REST verified; no custom DataPoints in cloud → text triples | High | High | P0 spike | P0 |
| `cognify` slow or rate-limited | Med | High | Tenant-managed model; build the graph before the demo; live ingest is only 1 small file | P1, P5 |
| LLM entities don't align with canonical IDs | Med | Med | Alias table + normalization; the path relies on the verified structural edges | P1 |
| Judge verdict varies (gpt-5.6-luna rejects temperature 0) | Low | Med | Strict JSON verdict, same-service active candidates, threshold 0.7; the demo file is unambiguous (0.99 in every run) | P4 |
| Concurrent Cognee searches time out (2 in flight blew the 23 s budget) | Med | High | Eval runs one question at a time; demo asks one question at a time; 23 s budget + retry | P4, P5 |
| Answer text ignores the stale decision | Med | Med | Supersede check is **post-retrieval code**, not a prompt; warnings are always attached | P2 |
| Contradiction false positives | Med | Med | Only compare against the same service + active decisions; LLM judge returns a reason; demo file is crafted | P4 |
| Demo network or LLM failure | Low | High | Cached answers for the 3 scripted queries; a recorded backup video | P5 |
| Frontend blocked on the backend | Med | Med | Contract-first: mock JSON in `frontend/src/lib/mock.ts` | P3 |

---

## 7. Demo script (2 minutes, judging round)

Measured: `/ask` 10–16 s, alert ~8 s. Ask one question at a time (Cognee Cloud slows under concurrent searches).

1. **(20 s)** Ask *"Why is payments on Postgres, and who should I talk to about it now?"* → answer, 3 evidence cards, 4-hop path, **STALE** badge (ADR-003 was superseded). Talk over the ~12 s wait: "it's walking the graph".
2. **(20 s)** Ask *"What's our mobile release cadence?"* → **refuses**: "not in company knowledge". Point out that it never guesses.
3. **(20 s)** Go to Alerts and drop `MTG-0402.md` (a new meeting proposing DynamoDB for payments). In ~8 s a **contradiction alert** appears: *"MTG-0402 contradicts ADR-007 (Postgres for ACID). People: Priya (owner), Arjun (raised it)."* The graph keeps building in the background.
4. **(20 s)** Re-ask the first question → the answer now carries the contradiction warning (it's there immediately).
5. **(20 s)** Open the eval badge → **Permafrost vs raw Cognee** on the same 10 questions: verified path 5/5 vs 0/5, stale flagged 2/2 vs 1/2, grounded 10/10 vs 9/10 (raw answered the off-corpus question), expected refs cited 100% vs 55%. This is the "not just a wrapper" answer.
6. **(20 s)** Buffer.

---

## 8. Definition of done (PS-2 completeness)

- [x] Cognee-powered knowledge layer (`cognee_client.py`, graph in the Cognee Cloud dataset `snow`: 453 nodes, 125/125 structural edges verified)
- [x] ≥2 types of company information (ADRs, tickets, meetings, org chart = 4)
- [x] Natural-language Q&A interface (`/ask` page, `POST /ask`)
- [x] Answers grounded in retrieved knowledge (evidence cards, refusal path; eval: 0 hallucinated sources)
- [x] ≥1 multi-hop relationship demonstrated (4-hop path `svc-payments → ADR-007 → MTG-0312 → priya → platform`, 8/8 identical runs)
- [x] Differentiator: contradiction + stale detection live (MTG-0402 → alert vs ADR-007 in ~8 s)
- [x] Eval ≥ 9/10 and shown in the UI, next to the raw-Cognee baseline on the same questions (10/10 vs 9/10; path 5/5 vs 0/5)
- [x] Agent access: MCP tool `ask_company_brain` wraps `/ask` (PS-2 Challenge: humans, agents, and applications)
- [x] README: one-command setup (`scripts/init.sh`, `scripts/dev.sh`), architecture diagram, decision log
