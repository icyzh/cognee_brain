"""Parse company files into records with a content hash.

Structured (ADR / meeting .md with frontmatter `id`, ticket .json, team.json): canonical IDs, metadata
edges, stale and contradiction checks. Anything else Cognee can read is "semantic-only": text formats
are sent as text ("doc"), other files as the raw file for Cognee's loaders (pdf and office docs, images
via a vision model, audio and video via transcription). Semantic-only files are searchable and cited
as evidence, but have no metadata edges, so no verified path or stale check.
"""

import hashlib
import json
import re
from pathlib import Path

import yaml

from app.config import DATA_DIR

TYPE_BY_DIR = {"adrs": "adr", "tickets": "ticket", "meetings": "meeting"}
TEXT_EXT = {".txt", ".md", ".markdown", ".csv", ".log", ".html", ".htm", ".xml", ".yaml", ".yml", ".json"}
FILE_KIND = {  # raw files Cognee's loaders handle (extensions as in cognee.infrastructure.loaders)
    "doc": {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".odt", ".rtf", ".epub"},
    "image": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".bmp", ".heic"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".aiff"},
    "video": {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi"},
}
KIND_BY_EXT = {ext: kind for kind, exts in FILE_KIND.items() for ext in exts}
SUPPORTED_EXT = TEXT_EXT | set(KIND_BY_EXT)


def ref_for(name: str) -> str:
    """A file's ref for semantic-only docs: its name without extension, e.g. "standup-2026-04-02"."""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", Path(name).stem).strip("-")[:64] or "doc"


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


def load_file(path: Path, name: str | None = None) -> dict | None:
    """`name` = the real file name when `path` is a temp copy (upload validation)."""
    name = name or path.name
    suffix = Path(name).suffix.lower()
    if name.startswith(".") or name == "README.md" or suffix not in SUPPORTED_EXT:
        return None  # README.md = the story bible, not company data
    data = path.read_bytes()  # ponytail: media is hashed on every load(DATA_DIR); cache by mtime if files get big
    base = {"path": source_path(path), "hash": hashlib.sha256(data).hexdigest()}
    if suffix in KIND_BY_EXT:
        return base | {"type": KIND_BY_EXT[suffix], "ref": ref_for(name), "meta": {}, "body": "", "file": str(path), "suffix": suffix}
    text = data.decode("utf-8", errors="replace")
    doc = base | {"type": "doc", "ref": ref_for(name), "meta": {}, "body": text}
    if name == "team.json":
        return base | {"type": "org", "ref": "team", "meta": json.loads(text), "body": ""}
    if suffix == ".json":
        meta = json.loads(text)
        if isinstance(meta, dict) and isinstance(meta.get("id"), str):
            return base | {"type": "ticket", "ref": meta["id"], "meta": meta, "body": meta.get("body", "")}
        return doc
    if suffix in (".md", ".markdown"):
        meta, body = parse_md(text)
        if not isinstance(meta, dict) or "id" not in meta:
            return doc  # plain Markdown notes: semantic-only
        type_ = TYPE_BY_DIR.get(path.parent.name) or ("adr" if meta["id"].startswith("ADR-") else "meeting")
        return base | {"type": type_, "ref": meta["id"], "meta": meta, "body": body}
    return doc


def load(root: Path) -> list[dict]:
    """Every record under root (a directory or a single file), org chart first."""
    root = Path(root)
    if root.is_file():
        return [r for r in [load_file(root)] if r]
    records = [r for p in sorted(root.rglob("*")) if p.is_file() and (r := load_file(p))]
    return sorted(records, key=lambda r: r["type"] != "org")
