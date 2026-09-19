# Decision Brain

**Ask why. Get the answer, the evidence, and the path.**

Decision Brain is a mini Company Brain built on Cognee. It connects a company's docs, tickets, meeting notes and org chart into one knowledge graph, then answers natural-language questions with cited evidence and a visible multi-hop path.

## The idea

A new engineer asks, *"Why is payments on Postgres, and who owns it now?"* The answer exists, but it is scattered: an ADR records the decision, a meeting note records who made it, a ticket records the migration, and the org chart records who owns the service today. No single document holds the whole answer.

Keyword search finds the pieces but not the links between them. Chatbots that answer from vector search alone can produce a confident answer with no trail behind it. Decision Brain keeps the links between documents as first-class graph edges, so every answer shows the chain of documents and people it came from.

## What Decision Brain does

- **Ingest** four source types from `data/seed/`: ADRs and docs (Markdown), tickets (JSON), meeting notes (Markdown) and the org chart (`team.json`).
- **Build** a hybrid graph. Metadata becomes deterministic typed edges, and Cognee's LLM extraction adds entities, topics and reasoning from prose.
- **Answer** questions through `POST /ask` using Cognee `GRAPH_COMPLETION` retrieval, and refuse when retrieval finds nothing relevant.
- **Show** evidence cards, the hop path (`Service → Decision → Meeting → Person → Team`) and warnings when a cited decision has been superseded.
- **Explore** the graph and the ingested sources directly.

## Structure from metadata. Meaning from the LLM.

Decision Brain does not rely on the LLM to invent the relationships its answers depend on.

- The edges used in the multi-hop demo (`attended_by`, `assigned_to`, `member_of`, `owns`, `decided_in`, `affects`, `supersedes`, `references`) come from source metadata and canonical IDs, so they cannot be hallucinated.
- The LLM handles only prose: entities, topics and the reasoning behind decisions. Those entities are then linked back to the canonical nodes.
- A grounding guard answers only from retrieved context. Each answer carries `evidence[]`, `path[]` and `warnings[]`, and a supersede check flags stale decisions.

## Architecture

![Decision Brain architecture](docs/architecture.png)

The Next.js frontend talks to a FastAPI backend over REST. The backend runs Cognee in-process, and Cognee stores its graph (Kùzu), vectors (LanceDB) and metadata (SQLite) in local files, so no database server is needed. App state such as question history and feedback lives in a separate SQLite file (`app.db`) accessed with Python's built-in `sqlite3`. LLM and embedding providers are set through environment variables (LiteLLM), so switching providers is a config change.

The full design is in [`docs/architecture.md`](docs/architecture.md): ingestion pipeline, graph schema, query sequence, reliability plan and scale-out path. The diagram source is [`docs/architecture.excalidraw`](docs/architecture.excalidraw).

## Built with

- Next.js, React, TypeScript and Tailwind CSS
- Python, FastAPI and uv
- Cognee, with Kùzu, LanceDB and SQLite as file-based stores
- LiteLLM-compatible LLM and embedding providers

## Status

The frontend and backend scaffolds are in place, and the backend currently serves only `GET /health`. Ingestion, `/ask`, the graph explorer and the seed data are still to be built, following [`docs/architecture.md`](docs/architecture.md).

## Run locally

Prerequisites: Node.js 20+, npm, [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
bash scripts/init.sh
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

Open http://localhost:3000. The API runs on http://localhost:8000, with interactive docs at http://localhost:8000/docs.

```bash
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```
