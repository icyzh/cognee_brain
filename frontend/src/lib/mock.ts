import type { Alert, AskResponse, EvalLatest, GraphData, IngestResult, Source } from "./types";

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

export const REFUSAL_QUESTION = "What's our Kafka strategy?";
export const OWNER_QUESTION = "Who decided to move the ledger off MongoDB, and which team owns it?";

// Doubles as the Ask page's demo shortcuts.
export const SUGGESTED = [SHOWCASE_QUESTION, REFUSAL_QUESTION, OWNER_QUESTION];

export const mockRefusal: AskResponse = {
  answer: "I couldn't find this in company knowledge.",
  grounded: false,
  evidence: [],
  path: [],
  warnings: [],
  latency_ms: 3100,
  qa_id: 43,
};

export const mockSources: Source[] = [
  ...mockAsk.evidence,
  { source: "adr", ref: "ADR-003", path: "adrs/ADR-003.md" },
  { source: "meeting", ref: "MTG-0402", path: "live/MTG-0402.md" },
].map((e) => ({
  path: e.path,
  ref: e.ref,
  type: e.source,
  content_hash: "3f9a1c0be27d4e51",
  ingested_at: "2026-09-18 10:12:04",
}));

export const mockAlerts: Alert[] = [
  {
    id: 2,
    kind: "contradiction",
    new_ref: "MTG-0402",
    existing_ref: "ADR-007",
    service: "svc-payments",
    reason: "MTG-0402 proposes moving payments storage to DynamoDB, but ADR-007 (accepted) keeps the ledger on Postgres for multi-row ACID.",
    confidence: 0.91,
    created_at: "2026-09-19 09:41:12",
    people: ["arjun", "priya"],
  },
  {
    id: 1,
    kind: "stale",
    new_ref: "ADR-007",
    existing_ref: "ADR-003",
    service: "svc-payments",
    reason: "ADR-003 (MongoDB) superseded by ADR-007 on 2026-03-12",
    confidence: null,
    created_at: "2026-09-18 10:12:04",
  },
];

export const mockIngest = (name: string): IngestResult => ({
  source_ref: name.replace(/\.[^.]+$/, ""),
  nodes_added: 14,
  alerts: name.startsWith("MTG-0402") ? [mockAlerts[0]] : [],
  took_ms: 21400,
});

const QUESTIONS = [
  SHOWCASE_QUESTION,
  OWNER_QUESTION,
  "Which service does TCK-142 migrate?",
  "Who attended the meeting where ADR-007 was decided?",
  "Is ADR-003 still the storage decision for payments?",
  "Which team owns svc-notify?",
  "Who is on the platform team?",
  "What did MTG-0305 decide about retries?",
  REFUSAL_QUESTION,
  "What's our mobile release cadence?",
];

export const mockEval: EvalLatest = {
  decision_brain: {
    run_at: "2026-09-19 08:02:10",
    grounded_ok: 9,
    total: 10,
    hallucinated_sources: 0,
    ref_recall: 0.93,
    stale_flagged: 1,
    results: QUESTIONS.map((q, i) => ({ q, grounded_ok: i !== 7, ref_recall: i === 7 ? 0.5 : 1 })),
  },
  raw_cognee: {
    run_at: "2026-09-19 08:05:47",
    grounded_ok: 7,
    total: 10,
    hallucinated_sources: 2,
    ref_recall: 0.71,
    stale_flagged: 0,
    results: QUESTIONS.map((q, i) => ({ q, grounded_ok: ![4, 8, 9].includes(i), ref_recall: [0, 3].includes(i) ? 0.5 : 0.8 })),
  },
};

export const mockGraph: GraphData = {
  nodes: [
    ...mockAsk.path.flatMap((e) => [e.from, e.to]),
    { id: "ADR-003", type: "Decision" },
    { id: "TCK-142", type: "Ticket" },
    { id: "svc-notify", type: "Service" },
    { id: "mei", type: "Person" },
  ]
    .filter((n, i, all) => all.findIndex((m) => m.id === n.id) === i)
    .map((n) => ({ ...n, label: n.id })),
  edges: [
    ...mockAsk.path.map((e) => ({ from: e.from.id, to: e.to.id, rel: e.rel })),
    { from: "ADR-007", to: "ADR-003", rel: "supersedes" },
    { from: "TCK-142", to: "svc-payments", rel: "affects" },
    { from: "TCK-142", to: "ADR-007", rel: "implements" },
    { from: "platform", to: "svc-notify", rel: "owns" },
    { from: "mei", to: "platform", rel: "member_of" },
  ],
};
