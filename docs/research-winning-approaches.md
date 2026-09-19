# Research: Winning Approaches for "Build a mini Company Brain using Cognee" (PS-2)

> Scope: global web research on hackathon winners and strong projects for the problem in [`PS.md`](../PS.md). It covers how they approached ingestion, graph construction, retrieval, multi-hop reasoning, grounding and demo, and what judges rewarded.
> Method: 5 search angles, 18 sources fetched and 76 claims extracted. 25 of those claims went through 3-vote adversarial verification: 18 confirmed and 7 refuted. The WeMakeDevs winners page was then fetched by hand.
> Date: 2026-09-19

---

## TL;DR

1. **Cognee has run hackathons on this exact theme.** These are the WeMakeDevs × Cognee event "Where's My Context?" (Jun 29 – Jul 5 2026, 500–1,200+ submissions) and three official **Company Brain** events in June 2026 (Slack+Granola on 06-16, Berlin on 06-19, GTM Brain Warsaw on 06-26). Their judging rubrics are public, and they are the best guide to what will score.
2. **Confirmed Cognee winners:** **Lethe** (incident-triage brain over runbooks and post-mortems, with "verifiable forgetting"), **Classroom Memory** (Cognee Cloud, prerequisite-graph reasoning) and **RealtyRecall** (Best Blog, multi-tenant NodeSets).
3. **Closest non-Cognee winner:** **LORE**, Grand Prize at the GitLab AI Hackathon 2026. It turns issues, MR threads, diffs and commits into searchable institutional memory backed by a knowledge graph.
4. **The pattern that wins:** a sharp, painful use case (not a generic chatbot), ≥2 heterogeneous sources, a typed graph, answers that show **evidence and the graph path**, a **memory lifecycle** (update, forget, self-improve) beyond plain RAG, a **live deployed demo** and a good README.
5. **For us:** follow Cognee's official Company Brain reference pipeline. Show `source --[rel]--> target` paths as the multi-hop proof, and add a lifecycle feature (contradiction or staleness detection, forgetting, session→graph distillation), since judges explicitly reward it.

---

## 0. OUR event's actual criteria (from the organizers, see [`PS.md`](../PS.md#evaluation))

| Round | Format | Criteria (5 pts each, /25) |
|---|---|---|
| **Mentoring** 3:30–4:30 PM | 5 min pitch + 2 min Q/A | Problem Clarity · Design Decisions · Scalability · Technical Implementation · Scope & Prioritisation |
| **Judging** 5:00–6:00 PM | **1 min pitch + 2 min demo** + 2 min Q/A | Production Standards · Technical Understanding · System Architecture · Completeness · Reliability |

**How this differs from the Cognee rubrics in section 1:** there is **no "creativity" or "best use of Cognee" score**. 6 of the 10 criteria are engineering-rigor criteria (design decisions, scalability, production standards, architecture, completeness, reliability). This event rewards a **solid, well-reasoned, reliable system** over a flashy idea.

### 0.1 Re-scored against our rubric (/5 each, our assessment)

| Project | Prob. Clarity | Design Dec. | Scal. | Tech Impl. | Scope | **Mentor /25** | Prod. Std. | Tech Und. | Arch. | Complete | Reliab. | **Judge /25** | **Total /50** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lethe | 5 | 5 | 3 | 4 | 5 | **22** | 4 | 4 | 4 | 4 | 4 | **20** | **42** |
| LORE | 5 | 4 | 4 | 4 | 4 | **21** | 4 | 4 | 4 | 4 | 3 | **19** | **40** |
| Classroom Memory | 4 | 4 | 4 | 4 | 4 | **20** | 4 | 3 | 4 | 4 | 3 | **18** | **38** |
| RealtyRecall | 4 | 4 | 4 | 4 | 3 | **19** | 4 | 3 | 4 | 4 | 3 | **18** | **37** |
| Cognee reference pipeline | 5 | 4 | 3 | 4 | 4 | **20** | 2 | 4 | 4 | 3 | 3 | **16** | **36** |
| ChronoScholar | 4 | 4 | 2 | 4 | 4 | **18** | 2 | 5 | 3 | 3 | 4 | **17** | **35** |
| DevAtlas | 4 | 3 | 3 | 3 | 3 | **16** | 3 | 3 | 3 | 3 | 2 | **14** | **30** |
| AI KG for Organizations | 3 | 4 | 4 | 3 | 2 | **16** | 3 | 3 | 4 | 2 | 2 | **14** | **30** |

Rationale in brief:
- **Lethe** leads because it has one crisp problem ("stale runbook at 3am"), an explicit design decision (forgetting as a feature) and tight scope. Its human-gated audit trail counts as a production standard and a reliability measure. Scalability is its weak spot (single-node file stores).
- **ChronoScholar** scores highest on Technical Understanding (it documents API pitfalls and token budgets) and gets reliability credit for an actual eval. Scalability and production polish are low.
- **The reference pipeline** is the right starting point, but it is only a starter. It gets no production-standards credit until we add them.

### 0.2 What each criterion means for our build

| Criterion | What judges will look for | Concrete move |
|---|---|---|
| **Problem Clarity** | One user, one painful moment | "New engineer asks why we chose X and who owns it now." Say it in the first 15 s. |
| **Design Decisions** | *Why* each choice, with trade-offs | A 1-slide decision log: Cognee (graph+vector hybrid) vs plain RAG; SQLite/file stores vs Neo4j (zero infra); GRAPH_COMPLETION vs CHUNKS; node_set per source |
| **Scalability** | A credible path from demo to org-scale | Incremental ingestion (hash dedupe), `node_set` tenancy, stores swappable by config (LanceDB→pgvector, Kùzu→Neo4j), async ingestion queue. Say what breaks first (LLM extraction cost). |
| **Technical Implementation** | It actually works end to end | A live ingestion → graph → Q&A path, not mocks |
| **Scope & Prioritisation** | What you cut and why | Show an explicit "MVP / cut / next" list: 3 sources, 1 multi-hop story; no auth, no connectors beyond files |
| **Production Standards** | Code quality, config, errors, logging | Env-based config, typed API, error states in the UI, structured logs, README with a one-command setup, a few tests |
| **Technical Understanding** | Can you explain the internals in Q/A? | Know how GRAPH_COMPLETION works (vector seeds → subgraph → triplets → LLM), why entity resolution matters, token cost per query |
| **System Architecture** | A clear diagram, clean separation | An ingestion layer / knowledge layer (Cognee) / API / UI diagram, shown in the pitch |
| **Completeness** | Every PS requirement is visibly met | A checklist slide: ✅ Cognee layer ✅ ≥2 data types ✅ NL Q&A ✅ grounded (evidence shown) ✅ multi-hop (path shown) |
| **Reliability** | No hallucinations, no demo failure | Answers are always grounded (show the evidence, refuse when there is no context), a small eval (≈10 Qs with expected sources), a **pre-built graph** so the demo never waits on ingestion, retries and a rate-limit-safe LLM tier, a cached fallback for the demo query |

### 0.3 Timing implications
- **Judging demo is only 2 minutes.** Script **one** question that shows the answer, the evidence and the multi-hop path, plus one "refuses when it doesn't know" question. Pre-ingest everything.
- **Judging pitch is 1 minute**: problem, architecture diagram, done.
- **The mentoring pitch (5 min)** is where design decisions, scalability and scope are scored, so prepare the decision log and the cut list for it.

---

## 1. What judges rewarded at other Cognee events (verified rubrics)

### WeMakeDevs × Cognee "The Hangover Part AI: Where's My Context?" (Jun 29 – Jul 5 2026)
Source: https://archive.wemakedevs.org/hackathons/cognee (verified 3-0)

| # | Criterion | Notes |
|---|---|---|
| 1 | Potential Impact | a real, painful problem |
| 2 | Creativity & Innovation | |
| 3 | Technical Excellence | |
| 4 | **Best Use of Cognee** | depth of **memory lifecycle APIs** and **hybrid graph-vector memory** |
| 5 | User Experience | |
| 6 | Presentation Quality | demo, README, submission |

Prizes: $10k pool plus job interviews at Cognee. Tracks were Best Use of Open Source (MacBook per member), Best Use of Cognee Cloud (iPhone 17 per member), and an OSS PR track ($100/PR, top 20).

### Cognee official "Company Brain" events (June 2026)
Source: https://github.com/topoteretes/cognee-hackathons (verified 3-0, READMEs read directly)

- **Company Brain hackathon (2026-06-16):** Slack + Granola meeting notes merged into one graph.
- **Cognee Cloud Hackathon: Build Your Company Brain (Berlin, 2026-06-19):**
  - Required base operations: **Ingest**, **Query + Self-improve**, **Lint**.
  - *"This distillation pattern [session → permanent graph] is the core piece of the hackathon. Judges will want to see how you use it."*
  - A dedicated **Best use of Cognee Cloud** bonus; *"Cloud projects start ahead on the rubric."*
  - Prize pool of €1,200 (600/400/200). **3-minute pitch**: explain how the agent self-improves, then give a live demo.
  - Suggested agents: support assistants that spot repeat questions, **expert finders**, **contradiction detectors**.
- **GTM Brain (Warsaw, 2026-06-26):** "Merge Accounts, Deals & Conversations into One Graph".

### General AI-hackathon judging (lablab.ai guide, dev.to judge write-up)
Sources: https://lablab.ai/guide/how-to-win-an-ai-hackathon, https://dev.to/amising6/what-i-learned-after-reviewing-many-ai-and-developer-projects-as-a-hackathon-judge-2g06

- lablab scores **Presentation, Business Value, Application of Technology, Originality**.
- *"Judges reward clarity over production value."* Show the solution working early.
- A **deployed demo URL** is a strong signal, and a local-only demo is a common failure.
- Name a **specific target user** and say why the product needs AI.
- Commit history gets checked, and pivoting after hour 12 is a known failure mode.

---

## 2. Scoring rubric used below

Each project is scored **1–10** on six axes taken from the PS and the rubrics above:

| Axis | What it measures |
|---|---|
| **Rel** | Relevance to PS-2 (company data, ≥2 types, Q&A) |
| **Tech** | Technical depth (graph design, lifecycle, retrieval sophistication) |
| **Hop** | Multi-hop relationship demonstrated |
| **Grd** | Grounding and citations (answers traceable to sources) |
| **UX** | Demo, UX and presentation (live demo, video, clarity) |
| **Repro** | Reproducibility (open repo, setup, self-hostable) |

> ⚠️ **These scores are our own assessment** based on the public evidence. They are not the judges' scores. Where evidence was thin (for example, a claim was refuted), the score is conservative.

---

## 3. Scoreboard

| # | Project | Event / Result | Cognee? | Rel | Tech | Hop | Grd | UX | Repro | **Total /60** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Lethe** | WeMakeDevs × Cognee, **Winner: Best Use of Cognee OSS** | ✅ | 8 | 8 | 5 | 8 | 9 | 9 | **47** |
| 2 | **Cognee Company Brain reference pipeline** | Official starter (Cognee, Jun 2026) | ✅ | 10 | 7 | 7 | 7 | 5 | 9 | **45** |
| 3 | **LORE** | GitLab AI Hackathon 2026, **Grand Prize** | ❌ | 9 | 8 | 6 | 5 | 7 | 6 | **41** |
| 4 | **Classroom Memory** | WeMakeDevs × Cognee, **Winner: Best Use of Cognee Cloud** | ✅ | 4 | 7 | 8 | 5 | 8 | 7 | **39** |
| 5 | **ChronoScholar** | WeMakeDevs × Cognee submission (placement unknown) | ✅ | 4 | 8 | 7 | 7 | 5 | 8 | **39** |
| 6 | **RealtyRecall** | WeMakeDevs × Cognee, **Best Blog Award** | ✅ | 5 | 7 | 5 | 5 | 8 | 7 | **37** |
| 7 | **DevAtlas** | LA Hacks 2025 (no prize shown) | ❌ | 8 | 6 | 7 | 4 | 6 | 5 | **36** |
| 8 | **AI Knowledge Graph for Organizations** | GitHub repo (not a hackathon entry) | ❌ | 7 | 7 | 5 | 6 | 3 | 5 | **33** |

---

## 4. Project deep-dives

### 4.1 Lethe: Winner, Best Use of Cognee Open Source (WeMakeDevs × Cognee 2026)
- **Links:** [GitHub](https://github.com/vinayaksonthalia/lethe) · [Live demo](https://vinayaksonthalia-lethe.hf.space/) · [Video](https://youtu.be/3840gxTZWxY) · [Winners page](https://archive.wemakedevs.org/hackathons/cognee/projects)
- **What:** a self-hosted incident-triage assistant that treats **verifiable forgetting** as a first-class feature.
- **Ingestion:** team runbooks and post-mortems in plain English, with no schema required.
- **Graph:** `cognify()` builds a knowledge graph (Kùzu) and a vector index (LanceDB) from the prose.
- **Lifecycle (the differentiator):** two-layer forgetting (hard delete plus reversible *demote*), human-gated curation and **audit timelines**.
- **Hook:** *"The dangerous moment is 3am, mid-outage, when your assistant tells you to fix a server that was decommissioned last month."*
- **Why it won (our read):** a painful, specific user and moment; it goes beyond RAG into the **memory lifecycle** (exactly the "Best Use of Cognee" criterion); it has a live demo and a video.
- **Lesson for us:** a company brain has to handle **stale knowledge**. Freshness and forgetting count as a feature, not a bug fix.
- *Evidence level: the winners page only. The internals were not independently verified.*

### 4.2 Cognee official Company Brain reference pipeline (Jun 2026)
- **Links:** https://github.com/topoteretes/cognee-hackathons (`cognee-companybrain-hackathon-2026-06-16`)
- **Ingestion:** Slack threads and Granola meeting notes are normalized into **transcript-shaped documents** with speaker, timestamp and channel tags.
- **Write path:** `remember()` with **`node_set` facets** (source / channel / project / speaker).
- **Graph:** Cognee's default extraction produces **`Person`, `Topic`, `Decision`, `Question`** nodes with attribution. This design intent was verified; the actual extractor output was not.
- **Multi-hop, built in:** Person → Decision → Topic → other Person ("who else was affected by the decision X made about Y?").
- **Suggested agents:** repeat-question detector, **expert finder**, **contradiction detector**.
- **Lesson:** this is literally our PS. Start here instead of designing from scratch.

### 4.3 LORE (Living Organizational Record Engine): Grand Prize, GitLab AI Hackathon 2026
- **Links:** [Devpost](https://devpost.com/software/lore-living-organizational-record-engine) · [GitLab winners blog](https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/)
- **What:** a multi-agent system that captures **engineering decisions** from GitLab issues, MR comment threads, code diffs and commits, and turns them into **searchable, enforceable institutional memory**.
- **Graph:** a knowledge graph with **cycle prevention**.
- **Data types:** tickets, code and decisions (meets the "≥2 types" requirement).
- **Caveat:** the claim that LORE does "@mention Ask" Q&A with "Memory #" citations was **refuted 0-3**, so its grounding UX is unverified. It does not use Cognee.
- **Lesson:** "decisions" are the most valuable entity in a company brain. Capturing *why* something was decided is what makes it feel like a brain rather than search.

### 4.4 Classroom Memory: Winner, Best Use of Cognee Cloud (WeMakeDevs × Cognee 2026)
- **Links:** [GitHub](https://github.com/RajdeepKushwaha5/ClassroomMemory) · [Live demo](https://classroom-memory.vercel.app/) · [Video](https://www.youtube.com/watch?v=2AUA_g0S3Ks)
- **Ingestion:** quiz responses, curriculum JSON and student progress records.
- **Cognee:** per-student private memory on Cognee Cloud, with graph reasoning over **prerequisites and downstream concept dependencies**.
- **Relevance:** off-domain (education), but the **dependency chain traversal is a clean multi-hop demo**.
- **Lesson:** using Cognee Cloud earns a separate prize track, and per-user or per-tenant memory isolation impresses judges.

### 4.5 ChronoScholar: WeMakeDevs × Cognee submission
- **Links:** [GitHub](https://github.com/SourabhaKK/ChronoScholar) · [Build log](https://dev.to/sourabha_kallapur_ef0353d/i-built-a-research-memory-agent-with-cognee-five-api-breaks-one-knowledge-graph-seven-days-e3b)
- **What:** a research-memory agent that ingests arXiv papers and **detects contradictions** between stored beliefs and new literature.
- **Graph:** from 10 papers it built **494 entities and 1,025 edges**, with **6 typed edge types** (`contradicts`, `supports`, `extends`, `invalidates`, `replicates`, `authored_by`).
- **Retrieval:** combines `CHUNKS` with `GRAPH_COMPLETION` for grounded cross-paper answers.
- **Eval:** F1 = 1.0 on a small 10-pair contradiction benchmark. It is tiny, but having any number at all helps the pitch.
- **Hard-won pitfalls (Cognee 1.2.2):**
  - `set_llm_config()` was removed, so configure through env vars (LiteLLM).
  - The default `ENABLE_BACKEND_ACCESS_CONTROL=true` splits writes and reads across DBs, which is confusing.
  - One `GRAPH_COMPLETION` call used about 6,910 tokens, **over Groq's 6k TPM free tier**.
- **Lesson:** **typed relationship edges** make multi-hop explainable, and a small eval number adds credibility.

### 4.6 RealtyRecall: Best Blog Award (WeMakeDevs × Cognee 2026)
- **Links:** [Blog](https://mahimairaja.medium.com/your-voice-agent-forgets-you-the-moment-you-hang-up-i-gave-it-a-memory-90ef8fdc8327) · [GitHub](https://github.com/mahimairaja/realtyRecall/) · [Live](https://realtyrecall.mahimai.ca/) · [Video](https://youtu.be/5k5fvlj2clY)
- **Ingestion:** crawled agent websites, call recordings and property listings (3 heterogeneous types).
- **Cognee:** the graph recognizes repeat callers and surfaces relevant listings, with **multi-tenancy via NodeSets**.
- **Lesson:** a good write-up is a prize category of its own. NodeSets are the idiomatic way to separate sources and tenants.

### 4.7 DevAtlas: LA Hacks 2025 (no prize shown)
- **Link:** https://devpost.com/software/devatlas-32ewbz
- **Ingestion:** GitHub API, Slack API and email webhooks.
- **Graph and retrieval:** Neo4j with a custom **GraphRAG + embedding hybrid**.
- **Multi-hop use case:** "who owns user auth?" returns developer → team → manager (code area → person → org).
- **Stack:** FastAPI, Gemini, fetch.ai agents, Docker, Next.js/Remix + Tailwind.
- **Lesson:** an **expert finder** is the most intuitive multi-hop demo for a company brain.

### 4.8 AI Knowledge Graph for Organizations (GitHub repo)
- **Link:** https://github.com/Carlos05-code/AI-Knowledge-Graph-for-Organizations
- **Stack:** Neo4j 5, Qdrant, OpenSearch and GPT-4o, with hybrid **BM25 + vector + graph** search.
- **Lesson:** it is a reference architecture only (0 stars, no event). Cognee gives you the same hybrid out of the box with file-based stores.

### Not comparable (excluded from scoring)
- **Neo4j Global GraphHack 2019** (https://neo4j.com/blog/news/announcing-global-graphhack-winners/) predates LLMs. Its winners (Meetup Mixer, Neomap, a JMeter load-testing tool) are graph tooling, not company brains.
- **ArangoDB × NVIDIA GraphRAG hackathon** (https://arangodbhackathon.devpost.com/updates/35431-hackathon-winners-live-results): winners were announced live at GTC 2025 and are not listed on the page.

---

## 5. Cross-cutting patterns: how winners approached each layer

| Layer | Winning / recommended approach | Evidence |
|---|---|---|
| **Ingestion** | Normalize heterogeneous sources into **text documents with metadata** (speaker, timestamp, channel, source). Cognee `add`/`remember` accepts 38+ formats (PDF, CSV, JSON, code, audio, images), dedupes by hash and groups into datasets. | [Cognee blog](https://www.cognee.ai/blog/fundamentals/how-cognee-builds-ai-memory), reference pipeline |
| **Source separation** | **`node_set` tags** per source, channel, project, speaker or tenant | Reference pipeline, RealtyRecall |
| **Graph schema** | Let the default extraction produce Person / Topic / Decision / Question, or define **typed edges** (`contradicts`, `supports`, `owns`, `decided`...) for explainable hops | Reference pipeline, ChronoScholar |
| **Storage** | Default file-based stores (Kùzu/Ladybug graph, LanceDB vectors, SQLite relational) mean **zero infra**, which helps reproducibility | Cognee blog, Lethe |
| **Retrieval** | `GRAPH_COMPLETION` (default): embed the query, pick seed nodes from vector hits, project a subgraph, rank triplets, build context, then the LLM answers. Pair it with `CHUNKS` for raw passages. | [Cognee search docs](https://docs.cognee.ai/core-concepts/main-operations/legacy-operations/search), ChronoScholar |
| **Multi-hop** | `GraphCompletionContextExtensionRetriever` (multi-round expansion through LLM follow-up queries) or `GraphCompletionCotRetriever` (chain-of-thought with iterative refinement). Each round adds about one hop. | Cognee docs and blog (medium confidence) |
| **Grounding** | `include_references=True` appends an **"Evidence:"** block. `verbose=True` returns `text_result`, `context_result`, `objects_result` and the prompts. Context renders as `source --[relationship]--> target` lines, which the UI can show as **citations plus a visible path**. | Cognee search docs (verified 3-0) |
| **Lifecycle** | Forgetting and demotion with an audit trail (Lethe); session → permanent graph distillation, self-improvement and lint (Berlin brief); contradiction detection (ChronoScholar, reference agents) | Winners page, cognee-hackathons |
| **Demo / UX** | Live deployed URL, video, a 3-minute pitch focused on one painful moment, and a README | All winners, lablab guide |

---

## 6. Pitfalls to avoid

1. **Entity resolution compounds across hops.** At 85% per-hop accuracy, 1-hop answers are about 85% correct but 5-hop answers only about 44%. Keep the demo to **2–3 hops** and dedupe people and system names on purpose (canonical IDs in metadata). Source: https://www.sowmith.dev/blog/graphrag-entity-disambiguation
2. **Don't assume graph beats hybrid search.** Claims either way about graph traversal vs strong hybrid (RRF) search failed verification, so there is no solid evidence that graph wins. Use the graph where relationships matter and route simple factual lookups to chunks. Source (SPRIG preprint): https://arxiv.org/pdf/2602.23372
3. **Cognee API churn.** `search()` is now marked *legacy*, and v1.0 recommends `remember()` / `recall()`. Check whether `include_references`, `verbose` and the retriever classes are exposed through `recall()` before building the UI on them.
4. **LLM rate limits.** One `GRAPH_COMPLETION` call can use about 7k tokens, so free tiers (Groq 6k TPM) will fail mid-demo.
5. **Config gotchas.** Configure the LLM through env vars (LiteLLM). Watch `ENABLE_BACKEND_ACCESS_CONTROL`, which splits reads and writes across DBs.
6. **A local-only demo** is a named failure mode, so deploy something judges can open.

---

## 7. Recommended approach for our build (synthesis)

Based on the rubric plus the winners:

1. **Pick one painful moment and one user.** For example: *"A new engineer asks why we chose X and who to talk to. The brain answers with the decision, the meeting it came from, the ticket it closed, and the person who owns it now."*
2. **Ingest ≥3 source types** as normalized, metadata-tagged docs: **docs** (markdown/PDF), **tickets** (CSV/JSON), **meeting notes / Slack** (transcripts). Tag each with a `node_set` for its source.
3. **Graph:** Cognee `cognify` default extraction, plus typed relationships centered on **Decision** (`decided_in`, `affects`, `owned_by`, `supersedes`).
4. **Q&A:** `GRAPH_COMPLETION` with references and verbose output. The UI shows **the answer, then the evidence snippets, then the rendered hop path** (`Person --decided--> Decision --affects--> Service --owned_by--> Team`).
5. **Multi-hop showcase query** (scripted for the demo): expert finder, or "which open tickets are affected by the decision made in the 12 Mar meeting?"
6. **Lifecycle differentiator** (pick one, since judges reward it): **staleness/supersedes detection** (Lethe-style), **contradiction detector** (docs vs meeting notes), or **Q&A session → graph distillation** (Berlin core piece).
7. **Storage:** Cognee's file-based defaults plus SQLite for app state (in line with repo conventions). No Docker.
8. **Ship:** a deployed URL, a 2–3 min video, a README with an architecture diagram and a tiny eval (for example, 10 questions with expected sources).

---

## 8. Refuted or unverified claims (do not rely on these)

| Claim | Vote |
|---|---|
| LORE offers @mention "Ask" Q&A with numbered "Memory #" citations | 0-3 ❌ |
| GRAPH_COMPLETION does 1-hop by default and `neighborhood_depth` is the documented k-hop setting | 1-2 ❌ |
| Cognee's core pipeline is exactly add / cognify / memify / search | 1-2 ❌ (v1.0 uses remember/recall) |
| Multi-hop is done by `GRAPH_COMPLETION_COT`, "one of 14 modes" | 0-3 ❌ |
| Graph-seeded hybrid (GraphHybrid / GraphRRF) beats RRF for multi-hop recall | 1-2 / 0-3 ❌ |
| GraphCompletionRetriever is "the main" grounded Q&A path (as described in that blog) | 0-3 ❌ |

---

## 9. Open questions

- Who won the June 2026 Company Brain events (06-16, Berlin, Warsaw)? No public results were found.
- The WeMakeDevs page mentions "eighteen standout builds" beyond the 3 winners, but none are detailed publicly.
- Does `recall()` in v1.0 expose the Evidence block, verbose context and the multi-hop retrievers?
- Are there verified winners built on Graphiti/Zep, LightRAG, MS GraphRAG or Mem0 for enterprise knowledge? None survived verification.

---

## 10. Sources

| Source | Type | Used for |
|---|---|---|
| https://archive.wemakedevs.org/hackathons/cognee | Primary | Rubric, prizes |
| https://archive.wemakedevs.org/hackathons/cognee/projects | Primary | Winners (Lethe, Classroom Memory, RealtyRecall) |
| https://github.com/topoteretes/cognee-hackathons | Primary | Company Brain briefs, reference pipeline |
| https://github.com/vinayaksonthalia/lethe | Primary | Lethe |
| https://github.com/RajdeepKushwaha5/ClassroomMemory | Primary | Classroom Memory |
| https://github.com/mahimairaja/realtyRecall/ | Primary | RealtyRecall |
| https://mahimairaja.medium.com/your-voice-agent-forgets-you-the-moment-you-hang-up-i-gave-it-a-memory-90ef8fdc8327 | Blog | RealtyRecall write-up |
| https://devpost.com/software/lore-living-organizational-record-engine | Primary | LORE |
| https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/ | Primary | LORE win confirmation |
| https://devpost.com/software/devatlas-32ewbz | Primary | DevAtlas |
| https://github.com/Carlos05-code/AI-Knowledge-Graph-for-Organizations | Repo | Reference architecture |
| https://github.com/SourabhaKK/ChronoScholar | Repo | ChronoScholar |
| https://dev.to/sourabha_kallapur_ef0353d/i-built-a-research-memory-agent-with-cognee-five-api-breaks-one-knowledge-graph-seven-days-e3b | Blog | ChronoScholar, Cognee pitfalls |
| https://www.cognee.ai/blog/fundamentals/how-cognee-builds-ai-memory | Vendor | Ingestion, retrieval, storage |
| https://docs.cognee.ai/core-concepts/main-operations/legacy-operations/search | Vendor docs | Search types, references, verbose |
| https://docs.cognee.ai/core-concepts/main-operations/search | Vendor docs | Current search / recall |
| https://www.cognee.ai/blog/deep-dives/the-art-of-intelligent-retrieval-unlocking-the-power-of-search | Vendor | Multi-hop retrievers |
| https://arxiv.org/abs/2510.02827 | Preprint | StepChain GraphRAG (evidence-chain demo pattern) |
| https://arxiv.org/pdf/2602.23372 | Preprint | Graph vs hybrid retrieval (SPRIG) |
| https://www.sowmith.dev/blog/graphrag-entity-disambiguation | Blog | Entity-resolution pitfalls |
| https://lablab.ai/guide/how-to-win-an-ai-hackathon | Blog | General judging |
| https://dev.to/amising6/what-i-learned-after-reviewing-many-ai-and-developer-projects-as-a-hackathon-judge-2g06 | Blog | General judging |
| https://neo4j.com/blog/news/announcing-global-graphhack-winners/ | Primary | Excluded (2019, not comparable) |
| https://arangodbhackathon.devpost.com/updates/35431-hackathon-winners-live-results | Primary | Excluded (no winners listed) |
