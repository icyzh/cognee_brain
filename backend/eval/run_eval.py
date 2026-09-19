"""Eval: uv run python -m eval.run_eval [--baseline [raw|prompted]]

Default scores our /ask pipeline ("decision_brain"). --baseline scores raw Cognee on the same questions:
GRAPH_COMPLETION with Cognee's default prompt, and no guard, evidence, path or supersede layers.
Both are scored the same way on what the response *cites*: the IDs written in the answer text.
--baseline prompted is the ablation row: Cognee + our system prompt, still none of our layers.
"grounded" is our pipeline's own flag vs a refusal-wording regex for raw Cognee (it has no flag).
"""

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app import cognee_client, store
from app.query import ask, paths

QUESTIONS = json.loads((Path(__file__).parent / "questions.json").read_text())
REFUSED = re.compile(r"\bnot[\s_-]?found\b|\bno (?:relevant )?information\b|\bdoes(?:n't| not) (?:contain|mention|include)|\b(?:i )?(?:don't|do not|cannot|can't) (?:know|find|answer)", re.I)
STALE_WORDS = re.compile(r"supersed|replaced|no longer|outdated|deprecated", re.I)


async def run_ours(q: dict) -> dict:
    r = await ask.ask(q["q"])
    return {
        "grounded": r["grounded"],
        "refs": list(dict.fromkeys(ask._ID.findall(r["answer"]))) if r["grounded"] else [],  # same basis as raw
        "cited": ask._ID.findall(r["answer"]) if r["grounded"] else [],
        "path_end": r["path"][-1]["to"]["id"] if r["path"] else None,
        "stale": [w["node"] for w in r["warnings"] if w["kind"] == "stale"],
        "answer": r["answer"],
    }


async def run_raw(q: dict, system_prompt: str | None = None) -> dict:
    r = await cognee_client.ask(q["q"], system_prompt=system_prompt)
    answer = r["answer"]
    cited = ask._ID.findall(answer)
    stale = q.get("expect_stale")
    return {
        "grounded": bool(answer.strip()) and not REFUSED.search(answer),
        "refs": list(dict.fromkeys(cited)),
        "cited": cited,
        "path_end": None,  # raw Cognee returns no path
        "stale": [stale] if stale and stale in cited and STALE_WORDS.search(answer) else [],
        "answer": answer,
    }


async def run_prompted(q: dict) -> dict:
    """Ablation: Cognee + our system prompt, none of our layers. Separates what the prompt buys from what the code buys."""
    return await run_raw(q, cognee_client.SYSTEM_PROMPT)


VARIANTS = {"ours": (run_ours, "decision_brain"), "raw": (run_raw, "raw_cognee"), "prompted": (run_prompted, "cognee_prompted")}


def score(q: dict, out: dict) -> dict:
    exp = q["expect_refs"]
    return {
        "q": q["q"],
        "kind": q["kind"],
        "grounded_ok": out["grounded"] == q["expect_grounded"],
        "ref_recall": round(len(set(exp) & set(out["refs"])) / len(exp), 2) if exp else 1.0,
        "hallucinated": sorted({i for i in out["refs"] + out["cited"] if not store.get_source_by_ref(i)}),
        "path_ok": out["path_end"] == q["expect_path_end"] if q.get("expect_path_end") else None,
        "stale_ok": q["expect_stale"] in out["stale"] if q.get("expect_stale") else None,
        "answer": out["answer"][:300],
    }


def summarize(rows: list[dict]) -> dict:
    graded = [r for r in rows if r["path_ok"] is not None]
    stale = [r for r in rows if r["stale_ok"] is not None]
    return {
        "grounded_ok": sum(r["grounded_ok"] for r in rows),
        "total": len(rows),
        "hallucinated_sources": sum(len(r["hallucinated"]) for r in rows),
        "ref_recall": round(sum(r["ref_recall"] for r in rows) / len(rows), 2),
        "stale_flagged": sum(bool(r["stale_ok"]) for r in stale),
        "stale_total": len(stale),
        "path_ok": sum(bool(r["path_ok"]) for r in graded),
        "path_total": len(graded),
    }


async def main(variant: str = "ours") -> dict:
    store.init_db()
    await paths.refresh()  # no FastAPI lifespan here: without it `path` is [] and no stale warnings fire
    run, variant = VARIANTS[variant]
    sem = asyncio.Semaphore(1)  # one at a time, like a user: Cloud slows sharply under concurrent searches (2 in flight → a 23 s timeout)

    async def one(q):
        async with sem:
            try:
                return score(q, await run(q))
            except Exception as e:  # a timeout is a failed question, not a crashed run
                out = {"grounded": None, "refs": [], "cited": [], "path_end": None, "stale": [], "answer": f"ERROR: {e!r}"}
                return score(q, out)

    rows = await asyncio.gather(*(one(q) for q in QUESTIONS))
    summary = summarize(rows)
    store.add_eval_run(variant, summary, rows)
    return {"variant": variant, **summary, "rows": rows}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="python -m eval.run_eval")
    ap.add_argument("--baseline", nargs="?", const="raw", choices=["raw", "prompted"],
                    help="score a baseline instead of our pipeline: raw Cognee (default) or Cognee + our system prompt")
    res = asyncio.run(main(ap.parse_args().baseline or "ours"))
    for r in res["rows"]:
        flags = ["grounded " + ("ok" if r["grounded_ok"] else "WRONG"), f"refs {r['ref_recall']}"]
        flags += [f"path {'ok' if r['path_ok'] else 'WRONG'}"] if r["path_ok"] is not None else []
        flags += [f"stale {'ok' if r['stale_ok'] else 'MISSED'}"] if r["stale_ok"] is not None else []
        flags += [f"hallucinated {r['hallucinated']}"] if r["hallucinated"] else []
        print(f"- {r['q']}\n    {' · '.join(flags)}")
    print(f"\n{res['variant']} @ {datetime.now(UTC):%Y-%m-%d %H:%M}Z: "
          + " · ".join(f"{k} {v}" for k, v in res.items() if k not in ("variant", "rows")))
