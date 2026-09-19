"""Media → text with our own OpenAI key, before anything reaches Cognee.

Cognee Cloud's hosted model isn't multimodal: sent a raw mp3 or png, it stored its own chat reply as
the document ("I'm happy to transcribe… please upload the audio file"), and it rejects .mp4 outright.
So audio and video are transcribed, and images described, here; Cognee gets the text. The text is cached
next to the file as a hidden sidecar (dotfiles are never loaded as data), so each file costs one call.
"""

import base64
import mimetypes
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.config import LLM_API_KEY, LLM_MODEL, TRANSCRIBE_MODEL

API = "https://api.openai.com/v1"
TRANSCRIBE_EXT = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}  # what the transcription API takes
IMAGE_PROMPT = (
    "This image comes from a company's internal documents. Transcribe every piece of visible text exactly, "
    "then describe what the image shows (diagram, whiteboard, screenshot, chart) in 2-4 sentences. Plain text only."
)


def sidecar(path: Path) -> Path:
    return path.with_name(f".{path.name}.txt")


def _headers() -> dict:
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set: needed to transcribe audio/video and read images")
    return {"Authorization": f"Bearer {LLM_API_KEY}"}


async def _transcribe(path: Path) -> str:
    src = path
    if path.suffix.lower() not in TRANSCRIBE_EXT:  # e.g. .mov/.mkv/.avi/.flac: extract the audio track first
        if not shutil.which("ffmpeg"):
            raise RuntimeError(f"{path.suffix} needs ffmpeg to extract its audio (or upload mp3/mp4/m4a/wav/webm)")
        src = Path(tempfile.mkdtemp()) / f"{path.stem}.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-vn", str(src)], check=True, timeout=300)
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.post(f"{API}/audio/transcriptions", headers=_headers(), data={"model": TRANSCRIBE_MODEL},
                         files={"file": (src.name, src.read_bytes(), mimetypes.guess_type(src.name)[0] or "application/octet-stream")})
    r.raise_for_status()
    return r.json()["text"].strip()


async def _describe(path: Path) -> str:
    uri = f"data:{mimetypes.guess_type(path.name)[0] or 'image/png'};base64,{base64.b64encode(path.read_bytes()).decode()}"
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{API}/chat/completions", headers=_headers(), json={"model": LLM_MODEL, "messages": [
            {"role": "user", "content": [{"type": "text", "text": IMAGE_PROMPT}, {"type": "image_url", "image_url": {"url": uri}}]}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


async def text_for(rec: dict) -> str:
    """Transcript (audio, video) or description (image) of a media record; cached in a sidecar."""
    path = Path(rec["file"])
    cache = sidecar(path)
    if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
        return cache.read_text()
    text = await (_describe(path) if rec["type"] == "image" else _transcribe(path))
    if not text:
        raise RuntimeError(f"{path.name}: no speech or text found")
    cache.write_text(text)
    return text
