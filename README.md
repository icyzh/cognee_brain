# Cognee Brain

- `frontend/` — Next.js + React + TypeScript (http://localhost:3000)
- `backend/` — Python FastAPI (http://localhost:8000, docs at `/docs`)

## Development

```bash
bash scripts/init.sh
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```
