"""The only module that talks to Cognee: Cognee Cloud REST (/api/v1, X-Api-Key).

Not cognee.serve(): the 1.6.0 SDK cloud client drops node_set on add and sessionId
on search (spike S2/S5). Bodies land in P1/P2.
"""

from typing import TypedDict


class RawResult(TypedDict):
    answer: str
    triplets: list[tuple[str, str, str]]  # (src, rel, dst)
    chunks: list[dict]  # {text, source_ref}


class GraphDump(TypedDict):
    nodes: list[dict]
    edges: list[dict]


async def add_structural(triples: list[tuple[str, str, str]], dataset: str) -> str:
    """Canonical triples, e.g. ("Decision:ADR-007", "affects", "Service:svc-payments"),
    rendered as text into /add with node_set=["structural"]. Returns the data_id."""
    raise NotImplementedError


async def add_text(text: str, node_set: list[str], dataset: str) -> str:
    """/add one document. Returns its data_id (stored in app.db sources)."""
    raise NotImplementedError


async def build(dataset: str) -> None:
    """/cognify with runInBackground=false."""
    raise NotImplementedError


async def ask(question: str) -> RawResult:
    """/search GRAPH_COMPLETION, verbose, fresh sessionId (spike S5)."""
    raise NotImplementedError


async def graph(focus: str | None, depth: int) -> GraphDump:
    """/datasets/{id}/graph; focus is a canonical name, resolved to a seed node UUID."""
    raise NotImplementedError


async def missing_edges(expected: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """Expected structural triples not found in /graph (matched on node name + edge label)."""
    raise NotImplementedError
