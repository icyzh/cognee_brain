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
