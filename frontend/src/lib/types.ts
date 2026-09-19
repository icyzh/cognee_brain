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
  latency_ms: number;
  qa_id: number;
}

// GET /sources row (backend/app/store.py `sources` table)
export interface Source {
  path: string;
  ref: string;
  type: string;
  content_hash: string;
  ingested_at: string;
}

// GET /alerts row (store.py `alerts` table; `people` = owner + raiser, from the graph)
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

// POST /ingest (multipart, one file), docs/phases/phase-4-differentiators.md §4B
export interface IngestResult {
  source_ref: string;
  nodes_added: number;
  alerts: Alert[];
  took_ms: number;
}

export interface EvalQuestion {
  q: string;
  grounded_ok: boolean;
  ref_recall: number;
}

export interface EvalSummary {
  run_at: string;
  grounded_ok: number;
  total: number;
  hallucinated_sources: number;
  ref_recall: number;
  stale_flagged: number;
  results: EvalQuestion[]; // per-question rows from eval_runs.results_json
}

// GET /eval/latest; a variant is null until it has been run
export interface EvalLatest {
  decision_brain: EvalSummary | null;
  raw_cognee: EvalSummary | null;
}

// GET /graph (backend/app/ingest/align.py `view`)
export interface GraphData {
  nodes: { id: string; type: string; label: string }[];
  edges: { from: string; to: string; rel: string }[];
}
