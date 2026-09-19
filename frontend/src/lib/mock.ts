import type { AskResponse } from "./types";

export const SHOWCASE_QUESTION = "Why is payments on Postgres, and who should I talk to about it now?";

export const mockAsk: AskResponse = {
  answer:
    "Payments moved to Postgres per ADR-007 (decided 2026-03-12). Platform Team owns it; talk to Priya.",
  grounded: true,
  evidence: [
    { source: "adr", ref: "ADR-007", path: "adrs/ADR-007.md", snippet: "The ledger needs multi-row ACID ..." },
    { source: "meeting", ref: "MTG-0312", path: "meetings/MTG-0312.md", snippet: "Priya: Postgres gives us transactions ..." },
    { source: "ticket", ref: "TCK-142", path: "tickets/TCK-142.json", snippet: "Migrate ledger tables to Postgres" },
  ],
  path: [
    { from: { id: "svc-payments", type: "Service" }, rel: "affected_by", to: { id: "ADR-007", type: "Decision" } },
    { from: { id: "ADR-007", type: "Decision" }, rel: "decided_in", to: { id: "MTG-0312", type: "Meeting" } },
    { from: { id: "MTG-0312", type: "Meeting" }, rel: "attended_by", to: { id: "priya", type: "Person" } },
    { from: { id: "priya", type: "Person" }, rel: "member_of", to: { id: "platform", type: "Team" } },
  ],
  warnings: [
    { kind: "stale", node: "ADR-003", message: "ADR-003 (MongoDB) superseded by ADR-007 on 2026-03-12" },
  ],
  latency_ms: 7900,
  qa_id: 42,
};
