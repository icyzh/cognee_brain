"""Offline checks for contradiction candidates and claims (no LLM). Run: uv run python -m tests.test_contradictions"""

import asyncio

from app.analysis import contradictions
from app.config import DATA_DIR
from app.ingest import loaders

RECORDS = loaders.load(DATA_DIR)  # seed + live
ADRS = {r["ref"]: r["meta"] for r in RECORDS if r["type"] == "adr"}
LIVE = next(r for r in RECORDS if r["ref"] == "MTG-0402")


def test_candidates_are_active_same_service_decisions():
    # ADR-003 also affects svc-payments but is superseded: never a candidate
    assert contradictions.candidates("svc-payments", ADRS) == ["ADR-002", "ADR-006", "ADR-007", "ADR-008"]
    assert contradictions.candidates("svc-notify", ADRS) == ["ADR-002", "ADR-009"]  # not superseded ADR-005
    assert contradictions.candidates("svc-payments", ADRS, exclude={"ADR-007"}) == ["ADR-002", "ADR-006", "ADR-008"]


def test_claims_come_from_frontmatter():
    assert contradictions.extract_claims(LIVE, ADRS) == [
        {"service": "svc-payments", "text": "Move payments storage to DynamoDB", "source_ref": "MTG-0402", "by": "arjun"}
    ]
    mtg = next(r for r in RECORDS if r["ref"] == "MTG-0312")  # decided ADR-007 → claims on its services
    assert {c["service"] for c in contradictions.extract_claims(mtg, ADRS)} == {"svc-payments", "svc-ledger"}


def test_threshold_and_cap():
    calls = []

    async def fake_judge(claim, d, meta, body):
        calls.append(d)
        return {"contradicts": True, "confidence": 0.99 if d == "ADR-007" else 0.5, "reason": "r"}

    saved = []
    contradictions.judge = fake_judge
    contradictions.store.add_alert = lambda *a: saved.append(a) or {"existing_ref": a[2]}
    alerts = asyncio.run(contradictions.check(LIVE, RECORDS))
    assert sorted(calls) == ["ADR-002", "ADR-006", "ADR-007", "ADR-008"]
    assert [a["existing_ref"] for a in alerts] == ["ADR-007"]  # 0.5 < THRESHOLD: no alert


def test_stale_alert_rows():
    rows = []
    contradictions.store.replace_stale_alerts = rows.extend
    contradictions.refresh_stale_alerts(RECORDS)
    assert sorted((new, old) for new, old, *_ in rows) == [("ADR-007", "ADR-003"), ("ADR-009", "ADR-005")]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
