"""Offline checks for the decision timeline (no LLM, no Cognee). Run: uv run python -m tests.test_timeline"""

from app.analysis import timeline
from app.config import DATA_DIR
from app.ingest import loaders

RECORDS = loaders.load(DATA_DIR / "seed")
ALERT = {"kind": "contradiction", "service": "svc-payments", "new_ref": "MTG-0402", "existing_ref": "ADR-007",
         "reason": "DynamoDB reverses the Postgres decision", "created_at": "2026-04-02 10:00:00"}


def in_force(as_of):
    return [e["ref"] for e in timeline.for_service("svc-ledger", RECORDS, [], as_of) if e["in_force"]]


def test_superseded_decision_is_closed_not_deleted():
    adr3 = next(e for e in timeline.for_service("svc-payments", RECORDS, []) if e["ref"] == "ADR-003")
    assert (adr3["status"], adr3["valid_from"], adr3["valid_to"]) == ("superseded", "2025-10-02", "2026-03-12")


def test_as_of_picks_the_truth_of_that_day():
    assert in_force("2026-01-01") == ["ADR-003"]  # MongoDB era
    assert in_force("2026-03-12") == ["ADR-004", "ADR-007"]  # the day Postgres took over: ADR-003 is out
    assert in_force("2025-01-01") == []


def test_contradiction_alert_shows_as_a_proposal_never_in_force():
    last = timeline.for_service("svc-payments", RECORDS, [ALERT, ALERT | {"service": "svc-auth"}])[-1]
    assert (last["ref"], last["status"], last["contradicts"], last["in_force"]) == ("MTG-0402", "proposed", "ADR-007", False)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
