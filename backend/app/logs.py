"""JSON-lines logs with a per-request id (set by the middleware in main.py)."""

import json
import logging
import sys
import time
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="-")

_log = logging.getLogger("permafrost")
_log.setLevel(logging.INFO)
_log.propagate = False
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
_log.addHandler(_handler)


def jlog(event: str, **fields) -> None:
    _log.info(json.dumps({"ts": round(time.time(), 3), "rid": request_id.get(), "event": event, **fields}, default=str))
