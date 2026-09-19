"""Parse seed files (md + YAML frontmatter, JSON) into records with a content hash."""

import hashlib
import json
from pathlib import Path

import yaml

from app.config import DATA_DIR

TYPE_BY_DIR = {"adrs": "adr", "tickets": "ticket", "meetings": "meeting"}


def parse_md(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm) or {}, body.strip()


def source_path(path: Path) -> str:
    """Stable sources key for batch and single-file runs: relative to data/seed (matches /ask
    evidence paths like "adrs/ADR-007.md"), else to data/ (e.g. "live/MTG-0402.md")."""
    p = path.resolve()
    for base in (DATA_DIR / "seed", DATA_DIR):
        if p.is_relative_to(base.resolve()):
            return str(p.relative_to(base.resolve()))
    return p.name


def load_file(path: Path) -> dict | None:
    text = path.read_text()
    rel = source_path(path)
    base = {"path": rel, "hash": hashlib.sha256(text.encode()).hexdigest()}
    if path.name == "team.json":
        return base | {"type": "org", "ref": "team", "meta": json.loads(text), "body": ""}
    if path.suffix == ".json":
        meta = json.loads(text)
        return base | {"type": "ticket", "ref": meta["id"], "meta": meta, "body": meta.get("body", "")}
    if path.suffix == ".md" and path.name != "README.md":
        meta, body = parse_md(text)
        if "id" not in meta:
            return None
        type_ = TYPE_BY_DIR.get(path.parent.name) or ("adr" if meta["id"].startswith("ADR-") else "meeting")
        return base | {"type": type_, "ref": meta["id"], "meta": meta, "body": body}
    return None


def load(root: Path) -> list[dict]:
    """Every record under root (a directory or a single file), org chart first."""
    root = Path(root)
    if root.is_file():
        return [r for r in [load_file(root)] if r]
    records = [r for p in sorted(root.rglob("*")) if p.is_file() and (r := load_file(p))]
    return sorted(records, key=lambda r: r["type"] != "org")
