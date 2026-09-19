# Decision Brain: Technical Architecture

A mini Company Brain on **Cognee**. It ingests docs, tickets and meeting notes into a hybrid graph+vector knowledge layer and answers natural-language questions with **evidence** and a **visible multi-hop path**.

> **Full diagram:** [`architecture.excalidraw`](architecture.excalidraw) (open at excalidraw.com), with a PNG preview at [`architecture.png`](architecture.png).
>
> **Excalidraw:** every diagram below is a Mermaid `flowchart` or `sequenceDiagram`, the two types Excalidraw's converter supports. In Excalidraw, open **More tools → Mermaid to Excalidraw** and paste a block.
> Items marked ⚠️ are Cognee APIs to confirm against the pinned version before building on them.

---

## 1. System overview

```mermaid
flowchart LR
    subgraph SRC["Company data (data/seed)"]
        D1["ADRs and docs (.md)"]
        D2["Tickets (.json)"]
        D3["Meeting notes (.md)"]
        D4["Org chart (team.json)"]
    end

    subgraph FE["frontend/ : Next.js App Router"]
        F1["Ask page"]
        F2["Evidence cards"]
        F3["Hop-path view"]
        F4["Graph explorer"]
        F5["Sources page"]
    end

    subgraph BE["backend/ : FastAPI (uv)"]
        B1["POST /ingest"]
        B2["POST /ask"]
        B3["GET /graph"]
        B4["GET /sources"]
        B5["POST /feedback"]
        subgraph ING["Ingestion service"]
            I1["Loaders and normalizer"]
            I2["Structural edge builder"]
            I3["Semantic ingest"]
        end
        subgraph QRY["Query service"]
            Q1["Retriever"]
            Q2["Grounding guard"]
            Q3["Supersede checker"]
            Q4["Path extractor"]
        end
    end

    subgraph COG["Cognee knowledge layer"]
        C1["remember / add"]
        C2["cognify: LLM extraction"]
        C3["add_data_points ⚠️"]
        C4["recall / search GRAPH_COMPLETION"]
        subgraph STORES["File-based stores (.cognee_system)"]
            S1[("Graph DB: Kuzu")]
            S2[("Vector DB: LanceDB")]
            S3[("Relational: SQLite")]
        end
    end

    subgraph APP["App state"]
        A1[("app.db: SQLite stdlib sqlite3")]
    end

    LLM["LLM + embeddings via LiteLLM env config"]

    SRC --> B1
    B1 --> I1
    I1 --> I2
    I1 --> I3
    I2 --> C3
    I3 --> C1
    C1 --> C2
    C2 --> S1
    C2 --> S2
    C3 --> S1
    C3 --> S2
    C1 --> S3

    F1 --> B2
    F4 --> B3
    F5 --> B4
    F2 --> B5
    B2 --> Q1
    Q1 --> C4
    C4 --> S1
    C4 --> S2
    Q1 --> Q2
    Q2 --> Q3
    Q3 --> Q4
    Q4 --> F2
    Q4 --> F3
    B5 --> A1
    B2 --> A1

    C2 -.-> LLM
    C4 -.-> LLM
```

### Components

| Layer | Component | Responsibility |
|---|---|---|
| Data | `data/seed/` | One consistent fictional company with 30–50 items and **canonical IDs** shared across sources |
| Frontend | Next.js App Router | Ask UI, evidence cards, hop-path rendering, graph explorer |
| Backend | FastAPI | HTTP API, ingestion orchestration, query pipeline, grounding rules |
| Knowledge | Cognee | Graph + vector memory, LLM extraction, graph-completion retrieval |
| Stores | Kùzu / LanceDB / SQLite | Cognee's file-based defaults, with zero infrastructure |
| App state | `app.db` (stdlib `sqlite3`) | Q&A history, feedback, eval runs |
| Model | LiteLLM (env vars) | LLM and embedding provider, swappable by config |

---

## 2. Ingestion pipeline (hybrid graph construction)

The core design decision is that **structure comes from metadata and meaning comes from the LLM**. Edges that the multi-hop demo depends on are deterministic, so they cannot be hallucinated.

```mermaid
flowchart TB
    subgraph IN["Raw sources"]
        R1["ADR-007.md"]
        R2["TCK-142.json"]
        R3["2026-03-12-arch-sync.md"]
        R4["team.json"]
    end

    L["Loader: parse frontmatter and fields"]
    N["Normalizer: canonical IDs, dates, source tag"]
    H{"Content hash seen?"}
    SKIP["Skip: already ingested"]

    subgraph STRUCT["Structural path: deterministic"]
        M1["Map metadata to typed DataPoints"]
        M2["Person, Team, Service, Decision, Ticket, Meeting, Document"]
        M3["Edges: attended_by, assigned_to, member_of, owns, decided_in, affects, supersedes, references"]
    end

    subgraph SEM["Semantic path: LLM"]
        T1["Transcript-shaped text with speaker and timestamp"]
        T2["remember with node_set = source type"]
        T3["cognify: entities, topics, rationale edges"]
    end

    ER["Entity alignment: LLM entities linked to canonical nodes by ID or alias"]
    OUT[("Unified knowledge graph + vector index")]

    R1 --> L
    R2 --> L
    R3 --> L
    R4 --> L
    L --> N
    N --> H
    H -- yes --> SKIP
    H -- no --> M1
    H -- no --> T1
    M1 --> M2
    M2 --> M3
    M3 --> OUT
    T1 --> T2
    T2 --> T3
    T3 --> ER
    ER --> OUT
```

### Source → graph mapping

| Source | Format | Structural edges (metadata) | Semantic content (LLM) |
|---|---|---|---|
| ADR / docs | Markdown + YAML frontmatter (`id`, `status`, `decided_in`, `affects`, `supersedes`, `owner`) | `Decision -affects-> Service`, `Decision -supersedes-> Decision`, `Decision -decided_in-> Meeting` | Rationale, alternatives, trade-offs |
| Tickets | JSON (`id`, `title`, `assignee`, `service`, `refs`, `status`) | `Ticket -assigned_to-> Person`, `Ticket -about-> Service`, `Ticket -references-> Decision` | Problem description, discussion |
| Meeting notes | Markdown (`date`, `attendees`, `decisions`) | `Meeting -attended_by-> Person`, `Meeting -produced-> Decision` | Who argued what, open questions |
| Org chart | JSON | `Person -member_of-> Team`, `Team -owns-> Service` | none |

---

## 3. Graph schema

```mermaid
flowchart LR
    P(["Person"])
    T(["Team"])
    S(["Service"])
    D(["Decision"])
    K(["Ticket"])
    M(["Meeting"])
    DOC(["Document"])
    TOP(["Topic: LLM-extracted"])

    P -- member_of --> T
    T -- owns --> S
    D -- affects --> S
    D -- decided_in --> M
    M -- attended_by --> P
    M -- produced --> D
    D -- supersedes --> D
    K -- assigned_to --> P
    K -- about --> S
    K -- references --> D
    DOC -- describes --> D
    DOC -- authored_by --> P
    D -- about_topic --> TOP
    K -- about_topic --> TOP
```

`DataPoint` models are pydantic classes subclassing Cognee's `DataPoint` ⚠️, with relationship fields as typed references. Every node carries `id` (canonical), `source`, `source_ref` (file and line/field) and `created_at`, which drive citations.

---

## 4. Query pipeline (`POST /ask`)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Next.js Ask page
    participant API as FastAPI /ask
    participant R as Retriever
    participant C as Cognee recall GRAPH_COMPLETION
    participant G as Graph + vector stores
    participant L as LLM
    participant GG as Grounding guard
    participant SC as Supersede checker
    participant DB as app.db

    U->>FE: Why is payments on Postgres and who owns it now?
    FE->>API: POST /ask {question}
    API->>R: retrieve(question)
    R->>C: recall(query, type=GRAPH_COMPLETION, verbose ⚠️)
    C->>G: embed query, vector top-k to seed nodes
    G-->>C: seed nodes
    C->>G: project subgraph around seeds, rank triplets
    G-->>C: triplets and chunks
    C->>L: answer from context only
    L-->>C: answer text
    C-->>R: answer + context triplets + source objects
    R->>GG: check context
    alt no relevant context
        GG-->>API: refuse: not in company knowledge
    else grounded
        GG->>SC: decisions in path
        SC->>G: any incoming supersedes edge?
        G-->>SC: D-07 superseded by D-14
        SC-->>API: answer + evidence + path + stale warnings
    end
    API->>DB: log question, answer, latency, sources
    API-->>FE: {answer, evidence[], path[], warnings[]}
    FE-->>U: answer, evidence cards, hop path, stale badge
```

### `/ask` response contract

```json
{
  "answer": "Payments moved to Postgres per ADR-007 (decided 2026-03-12). Platform Team owns it; talk to Priya.",
  "evidence": [
    {"source": "adr", "ref": "ADR-007.md", "snippet": "We choose Postgres for ACID..."},
    {"source": "meeting", "ref": "2026-03-12-arch-sync.md", "snippet": "Priya: ..."},
    {"source": "ticket", "ref": "TCK-142", "snippet": "Migrate ledger tables..."}
  ],
  "path": [
    {"from": "Service:payments", "rel": "affected_by", "to": "Decision:ADR-007"},
    {"from": "Decision:ADR-007", "rel": "decided_in", "to": "Meeting:2026-03-12"},
    {"from": "Meeting:2026-03-12", "rel": "attended_by", "to": "Person:priya"},
    {"from": "Person:priya", "rel": "member_of", "to": "Team:platform"}
  ],
  "warnings": [],
  "grounded": true,
  "latency_ms": 2140
}
```

### Retrieval strategy

| Question shape | Cognee mode | Why |
|---|---|---|
| Relational / "who / why / what affects" (default) | `GRAPH_COMPLETION` | Vector-seeded subgraph gives multi-hop context |
| Plain fact lookup | `CHUNKS` / `RAG_COMPLETION` | Cheaper, and graph adds noise |
| Deep chains (3+ hops) | Context-extension / CoT retriever ⚠️ | Iterative expansion, roughly one hop per round |

MVP ships **`GRAPH_COMPLETION` only**. The router is listed under *Next*.

---

## 5. Deployment and runtime

```mermaid
flowchart LR
    subgraph HOST["Single host: no Docker"]
        subgraph FEP["frontend/ npm run dev or start :3000"]
            NX["Next.js"]
        end
        subgraph BEP["backend/ uv run uvicorn :8000"]
            FA["FastAPI"]
            CG["cognee library in-process"]
        end
        subgraph DISK["Local disk"]
            K1[(".cognee_system: Kuzu, LanceDB, SQLite")]
            K2[("app.db")]
            K3["data/seed"]
        end
    end
    EXT["LLM + embedding API"]

    NX -- "REST JSON" --> FA
    FA --> CG
    CG --> K1
    FA --> K2
    FA --> K3
    CG -- HTTPS --> EXT
```

**Config (`backend/.env`):** `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, and `ENABLE_BACKEND_ACCESS_CONTROL=false` for a single-user demo. Cognee is configured through env vars, since `set_llm_config()` was removed in 1.2.x.

---

## 6. Reliability design

```mermaid
flowchart TB
    A["Pre-demo: uv run python -m app.ingest"] --> B[("Graph built ahead of time on disk")]
    B --> C["Eval: 10 questions with expected sources and path"]
    C --> D{"Pass rate OK?"}
    D -- no --> E["Fix seed data or schema"]
    E --> A
    D -- yes --> F["Freeze .cognee_system snapshot"]
    F --> G["Demo"]
    G --> H{"LLM error or timeout?"}
    H -- retry with backoff --> G
    H -- still failing --> I["Serve cached answer for scripted query"]
```

| Risk | Mitigation |
|---|---|
| Hallucinated answer | Answer only from retrieved context, refuse when there is none, always return evidence |
| Broken multi-hop path | Demo path runs over **deterministic metadata edges**, and canonical IDs avoid entity-resolution errors |
| Ingestion slow or failing live | Graph built before the demo and snapshotted; content-hash dedupe makes re-ingest idempotent |
| LLM rate limits (~7k tokens per graph query) | Paid tier or high-TPM model, retries with backoff, cached fallback for the scripted query |
| Cognee API drift | Pinned version in `uv.lock`, with a thin `app/cognee_client.py` wrapper as the single integration point |
| Stale knowledge | `supersedes` edges produce warnings in the answer |

---

## 7. Scalability path (mentoring round)

| Concern | MVP | Scale-out |
|---|---|---|
| Graph store | Kùzu (embedded) | Neo4j / FalkorDB via Cognee config |
| Vector store | LanceDB (embedded) | pgvector / Qdrant via Cognee config |
| Ingestion | Batch CLI over files | Connectors (Slack, Jira, Git) → queue → incremental ingest by content hash |
| Tenancy / access | Single user | `node_set` / dataset per team, with permission filter at retrieval |
| Cost | LLM extraction per document | Structural edges without LLM calls, LLM only for prose; cache embeddings |
| First bottleneck | LLM extraction throughput and cost | Batch plus a cheaper extraction model, and extract only changed documents |

---

## 8. Repository layout

```
backend/
  pyproject.toml            # uv; cognee pinned
  app/
    main.py                 # FastAPI app and routes
    config.py               # env loading
    cognee_client.py        # the ONLY module importing cognee
    ingest/
      loaders.py            # md/json parsing, normalization, hashing
      models.py             # DataPoint schema (Person, Decision, ...)
      structural.py         # metadata -> DataPoints + edges
      semantic.py           # remember + cognify with node_set
    query/
      ask.py                # retrieve -> guard -> supersede -> path
      paths.py              # triplets -> path[]
    store.py                # sqlite3 app.db (history, feedback)
  eval/
    questions.json          # 10 Qs + expected sources/path
    run_eval.py
frontend/
  src/app/
    page.tsx                # Ask page
    graph/page.tsx          # explorer
    sources/page.tsx
  src/components/
    EvidenceCard.tsx
    HopPath.tsx
data/seed/
  adrs/  tickets/  meetings/  team.json
```

---

## 9. PS requirement traceability

| PS-2 requirement | Where it is satisfied |
|---|---|
| Cognee-powered knowledge layer | §1 Cognee layer, `cognee_client.py` |
| ≥2 types of company information | §2: ADRs, tickets, meeting notes, org chart (4 types) |
| Natural-language Q&A interface | §4 `/ask` and the Ask page |
| Answers grounded in retrieved knowledge | §4 grounding guard and `evidence[]` |
| At least one multi-hop relationship | §3 schema and §4 `path[]` (Service → Decision → Meeting → Person → Team) |
