# Permafrost

**Ask why. Get the answer, the evidence, and the path.**

Permafrost is a mini Company Brain built on Cognee. It connects a company's docs, tickets, meeting notes and org chart into one knowledge graph, then answers natural-language questions with cited evidence and a visible multi-hop path.

## The idea

A new engineer asks, *"Why is payments on Postgres, and who should I talk to about it now?"* The answer exists, but it is scattered: an ADR records the decision, a meeting note records who made it, a ticket records the migration, and the org chart records who owns the service today. No single document holds the whole answer.

Keyword search finds the pieces but not the links between them. Chatbots that answer from vector search alone can produce a confident answer with no trail behind it. Permafrost keeps the links between documents as first-class graph edges, so every answer shows the chain of documents and people it came from.

## What Permafrost does

- **Ingest** four source types from `data/seed/`: ADRs and docs (Markdown), tickets (JSON), meeting notes (Markdown) and the org chart (`team.json`).
- **Build** a hybrid graph. Metadata becomes canonical structural edges (verified in the graph after ingestion), and Cognee's LLM extraction adds entities, topics and reasoning from prose.
- **Answer** questions through `POST /ask` using Cognee `GRAPH_COMPLETION` retrieval, and refuse when retrieval finds nothing relevant.
- **Show** evidence cards, the hop path (`Service → Decision → Meeting → Person → Team`) and warnings when a cited decision has been superseded.
- **Explore** the graph and the ingested sources directly.

## Structure from metadata. Meaning from the LLM.

Permafrost does not rely on the LLM to invent the relationships its answers depend on.

- The edges used in the multi-hop demo (`attended_by`, `assigned_to`, `member_of`, `owns`, `led_by`, `decided_in`, `affects`, `owned_by`, `supersedes`, `references`, `produced`) come from source metadata and canonical IDs, and ingestion fails if any expected edge is missing from the graph.
- The LLM handles only prose: entities, topics and the reasoning behind decisions. Those entities are then linked back to the canonical nodes.
- A grounding guard answers only from retrieved context. Each answer carries `evidence[]`, `path[]` and `warnings[]`, and a supersede check flags stale decisions.

## Architecture

![Permafrost architecture](docs/architecture.png)

The Next.js frontend talks to a FastAPI backend over REST. The backend calls Cognee Cloud over REST; the graph, vector and metadata stores and the LLM are managed by the Cognee Cloud tenant, so no database server runs locally. App state such as question history and feedback lives in a separate SQLite file (`app.db`) accessed with Python's built-in `sqlite3`. Cognee Cloud is configured with `COGNEE_SERVICE_URL` and `COGNEE_API_KEY` in `backend/.env`.

The full design is in [`docs/architecture.md`](docs/architecture.md): ingestion pipeline, graph schema, query sequence, reliability plan and scale-out path. The diagram source is [`docs/architecture.excalidraw`](docs/architecture.excalidraw).

## Built with

- Next.js, React, TypeScript and Tailwind CSS
- Python, FastAPI and uv
- Cognee Cloud (REST API; managed graph, vector store and LLM)

## Status

Phases 0–1 are done: Cognee Cloud spike, seed data (Snow Pay, `data/seed/`), and ingestion (`POST /ingest`, `GET /sources`, `GET /graph`). `/ask` and the UI wiring follow [`docs/plan.md`](docs/plan.md).

## Run locally

Prerequisites: Node.js 20+, npm, [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
bash scripts/init.sh   # then fill COGNEE_SERVICE_URL / COGNEE_API_KEY in backend/.env
cd backend && uv run python -m app.ingest --reset   # build the graph once (~5 min)
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

Open http://localhost:3000. The API runs on http://localhost:8000, with interactive docs at http://localhost:8000/docs.

```bash
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```
