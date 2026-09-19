import {
  OWNER_QUESTION,
  SHOWCASE_QUESTION,
  mockAlerts,
  mockAsk,
  mockEval,
  mockGraph,
  mockIngest,
  mockRefusal,
  mockSources,
} from "./mock";
import type { Alert, AskResponse, EvalLatest, GraphData, IngestResult, Source } from "./types";

export const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "1";

export class ApiError extends Error {}

// Fired after a live ingest so the nav badge refetches its alert count.
export const ALERTS_CHANGED = "alerts-changed";

// A FormData body is sent as multipart; anything else as JSON.
async function request<T>(path: string, body?: unknown, timeoutMs = 25_000): Promise<T> {
  let res: Response;
  const form = body instanceof FormData;
  try {
    res = await fetch(BASE + path, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined || form ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : form ? body : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    throw new ApiError(
      e instanceof DOMException && e.name === "TimeoutError"
        ? `The backend took longer than ${timeoutMs / 1000} s to answer.`
        : `Can't reach the backend at ${BASE}.`,
    );
  }
  if (!res.ok) {
    // FastAPI puts the reason in `detail` (a string, or {error} for knowledge-layer failures)
    const detail = await res.json().then((b) => b?.detail, () => undefined);
    const why = typeof detail === "string" ? detail : detail?.error;
    throw new ApiError(why ? `${why} (${res.status})` : `The backend returned ${res.status} ${res.statusText}.`);
  }
  return res.json();
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function ask(question: string): Promise<AskResponse> {
  if (USE_MOCK) {
    await delay(1200);
    return [SHOWCASE_QUESTION, OWNER_QUESTION].includes(question.trim()) ? mockAsk : mockRefusal;
  }
  return request("/ask", { question });
}

export async function feedback(qa_id: number, helpful: boolean): Promise<void> {
  if (USE_MOCK) return;
  await request("/feedback", { qa_id, helpful });
}

export async function sources(): Promise<Source[]> {
  if (USE_MOCK) return mockSources;
  return request("/sources");
}

export async function alerts(): Promise<Alert[]> {
  if (USE_MOCK) return mockAlerts;
  return request("/alerts");
}

// Live ingest returns after /add + the contradiction judge (~8 s); cognify finishes in the background.
export async function ingestFile(file: File): Promise<IngestResult> {
  if (USE_MOCK) {
    await delay(6000);
    return mockIngest(file.name);
  }
  const body = new FormData();
  body.append("file", file);
  return request("/ingest", body, 60_000);
}

export async function evalLatest(): Promise<EvalLatest> {
  if (USE_MOCK) return mockEval;
  return request("/eval/latest");
}

export async function graph(focus?: string, depth = 2): Promise<GraphData> {
  if (USE_MOCK) return mockGraph;
  const qs = focus ? `?${new URLSearchParams({ focus, depth: String(depth) })}` : "";
  return request(`/graph${qs}`);
}
