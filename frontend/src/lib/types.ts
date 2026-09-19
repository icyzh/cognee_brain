// POST /ask contract (docs/phases/phase-2-query-pipeline.md, extends architecture.md §4)

export type SourceType = "adr" | "ticket" | "meeting" | "org";

export interface Evidence {
  source: SourceType;
  ref: string;
  path: string;
  snippet: string;
}

export interface NodeRef {
  id: string;
  type: string;
}

export interface PathEdge {
  from: NodeRef;
  rel: string;
  to: NodeRef;
}

export interface Warning {
  kind: "stale" | "contradiction";
  node: string;
  message: string;
}

export interface AskResponse {
  answer: string;
  grounded: boolean;
  evidence: Evidence[];
  path: PathEdge[];
  warnings: Warning[];
  experts?: { id: string; team: string | null; score: number }[]; // PageRank over verified edges, best first
  unsupported_citations?: string[]; // IDs the answer cites that were not in the retrieved context
  latency_ms: number;
  qa_id: number;
  cached?: boolean; // served from the last grounded answer because the live call failed or took > 20 s
}

// GET /sources row (backend/app/store.py `sources` table)
export interface Source {
  path: string;
  ref: string;
  type: string;
  content_hash: string;
  ingested_at: string;
}

// GET /alerts row (store.py `alerts` table; `people` = owner + raiser, from document frontmatter)
export interface Alert {
  id: number;
  kind: "contradiction" | "stale";
  new_ref: string | null;
  existing_ref: string | null;
  service: string | null;
  reason: string | null;
  confidence: number | null;
  created_at: string;
  people?: string[];
}

// POST /ingest with no file: batch re-ingest of data/seed (unchanged files skipped)
export interface SeedIngestResult {
  files: number;
  ingested: number;
  skipped: number;
  nodes: number;
  edges: number;
  showcase_missing: [string, string, string][];
  took_s: number;
}

// POST /ingest (multipart, one file), docs/phases/phase-4-differentiators.md §4B
export interface IngestResult {
  source_ref: string;
  nodes_added: number;
  // "building": the alert check is done, the graph (cognify) finishes in the background (~15–30 s)
  graph_status?: "building" | "unchanged";
  alerts: Alert[];
  took_ms: number;
}

export interface EvalQuestion {
  q: string;
  kind?: "multi-hop" | "single-hop" | "refusal" | "stale";
  grounded_ok: boolean;
  ref_recall: number;
  hallucinated?: string[];
  path_ok?: boolean | null; // null: question has no expected path
  stale_ok?: boolean | null; // null: question has no stale decision to flag
  answer?: string;
}

export interface EvalSummary {
  run_at: string;
  grounded_ok: number;
  total: number;
  hallucinated_sources: number;
  ref_recall: number;
  stale_flagged: number;
  stale_total?: number;
  path_ok?: number;
  path_total?: number;
  results: EvalQuestion[]; // per-question rows from eval_runs.results_json
}

// GET /eval/latest; a variant is null until it has been run
export interface EvalLatest {
  decision_brain: EvalSummary | null;
  cognee_prompted?: EvalSummary | null; // ablation: our system prompt, none of our layers
  raw_cognee: EvalSummary | null;
}

// GET /graph (backend/app/ingest/align.py `view`)
export interface GraphData {
  nodes: { id: string; type: string; label: string }[];
  edges: { from: string; to: string; rel: string }[];
}

// GET /timeline?service=&as_of= (backend/app/analysis/timeline.py)
export interface TimelineEntry {
  ref: string;
  title: string;
  status: "active" | "superseded" | "proposed";
  valid_from: string;
  valid_to: string | null;
  in_force: boolean;
  superseded_by?: string[];
  contradicts?: string;
}

export interface TimelineData {
  service: string;
  as_of: string | null;
  entries: TimelineEntry[];
}

// GET /history row: a stored /ask response, opened instantly from the Ask start screen
export interface HistoryItem {
  question: string;
  asked_at: string;
  response: AskResponse;
}
