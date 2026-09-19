"""MCP stdio server: lets an agent (Claude Code, any MCP client) ask the company brain.

One tool, no new logic: it calls POST /ask on the running backend and returns the response unchanged.
Run the backend first (uv run uvicorn app.main:app --port 8000). Registered in the repo's .mcp.json.
"""

import os

import httpx
from mcp.server.mcpserver import MCPServer

API = os.environ.get("PERMAFROST_API", "http://localhost:8000")
server = MCPServer(
    "company-brain",
    instructions="Ask Snow Pay's company brain about decisions, owners, services, meetings and tickets. "
    "Answers are grounded with evidence and a verified relationship path, or refused.",
)


@server.tool()
async def ask_company_brain(question: str) -> dict:
    """Ask a natural-language question about the company (why a decision was made, who owns what,
    who to talk to). Returns {answer, grounded, evidence[], path[], warnings[]}: grounded=false means
    the company knowledge doesn't cover it, so don't guess. warnings flag stale or contradicted decisions."""
    async with httpx.AsyncClient(timeout=45) as c:  # /ask takes 10–16 s; up to ~25 s with its retry
        r = await c.post(f"{API}/ask", json={"question": question})
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    server.run("stdio")
