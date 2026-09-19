# Repository conventions

- `frontend/`: Next.js (App Router) + React + TypeScript, managed with npm.
- `backend/`: Python FastAPI, managed with uv (`uv add <pkg>`).
- Prefer SQLite (Python stdlib `sqlite3`) for prototype persistence. Do not introduce Docker or a remote database unless concrete requirements exceed SQLite’s limits.
- Run `bash scripts/init.sh` when initializing a fresh copy.
- Before implementing a medium or large feature, review `docs/idea.md` when it contains a product brief so decisions reflect the product’s purpose. Skip this step for small, direct user requests.
