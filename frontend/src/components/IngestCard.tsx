"use client";

import { useEffect, useRef, useState } from "react";
import { ALERTS_CHANGED, ingestFile, ingestStatus } from "@/lib/api";
import type { IngestResult } from "@/lib/types";
import { Card, ICON, Icon } from "./ui";

// POST /ingest returns after /add + the contradiction judge (~8 s, run side by side); cognify then
// builds the graph in the background (graph_status: "building").
const STEPS = ["parsing", "adding to Cognee", "checking contradictions"];
// ponytail: one request, so steps advance on typical timings, not server events.
const STEP_AT_MS = [0, 800, 3000];

type Row =
  | { name: string; kind: "queued" }
  | { name: string; kind: "running"; step: number }
  | { name: string; kind: "building"; res: IngestResult }
  | { name: string; kind: "done"; res: IngestResult }
  | { name: string; kind: "error"; message: string };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// The backend takes one ingest at a time: a live upload holds the lock while Cognee builds the graph.
async function waitForGraph(maxMs = 120_000) {
  for (let t = 0; t < maxMs; t += 2000) {
    if (!(await ingestStatus()).building) return;
    await sleep(2000);
  }
}

function Result({ res }: { res: IngestResult }) {
  return (
    <>
      {(res.took_ms / 1000).toFixed(1)} s ·{" "}
      {res.graph_status === "unchanged" ? "already ingested" : "added"} ·{" "}
      {res.alerts.length ? (
        <span className="font-medium text-red-600 dark:text-red-400">
          {res.alerts.length} new alert{res.alerts.length > 1 && "s"}
        </span>
      ) : (
        "no conflicts found"
      )}
    </>
  );
}

// Upload ADRs, meetings (.md) and tickets (.json) into the knowledge graph. Several files are ingested
// one after another; each is checked against the active decisions on its service.
export function IngestCard({
  title,
  description,
  onIngested,
  className,
}: {
  title: string;
  description: string;
  onIngested?: () => void;
  className?: string;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [dragging, setDragging] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const busy = rows.some(
    (r) => r.kind === "queued" || r.kind === "running" || r.kind === "building",
  );

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const setRow = (i: number, row: Row) =>
    setRows((rs) => rs.map((r, j) => (j === i ? row : r)));

  async function ingest(files: File[]) {
    if (!files.length || busy) return;
    setRows(files.map((f) => ({ name: f.name, kind: "queued" })));
    for (const [i, file] of files.entries()) {
      setRow(i, { name: file.name, kind: "running", step: 0 });
      timers.current = STEP_AT_MS.slice(1).map((ms, s) =>
        setTimeout(
          () =>
            setRows((rs) =>
              rs.map((r, j) =>
                j === i && r.kind === "running" ? { ...r, step: s + 1 } : r,
              ),
            ),
          ms,
        ),
      );
      try {
        await waitForGraph(); // a previous upload may still be building
        const res = await ingestFile(file);
        timers.current.forEach(clearTimeout);
        window.dispatchEvent(new Event(ALERTS_CHANGED));
        onIngested?.();
        if (res.graph_status === "building") {
          setRow(i, { name: file.name, kind: "building", res });
          await waitForGraph();
        }
        setRow(i, { name: file.name, kind: "done", res });
        onIngested?.();
      } catch (e) {
        timers.current.forEach(clearTimeout);
        setRow(i, {
          name: file.name,
          kind: "error",
          message: e instanceof Error ? e.message : String(e),
        });
      }
    }
  }

  return (
    <Card title={title} className={className}>
      <div className="flex flex-col gap-4">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          {description}
        </p>
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            ingest([...e.dataTransfer.files]);
          }}
          className={`flex flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition ${
            busy ? "cursor-wait opacity-60" : "cursor-pointer"
          } ${
            dragging
              ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
              : "border-zinc-200 bg-zinc-50 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-950/40 dark:hover:border-zinc-600"
          }`}
        >
          <input
            type="file"
            accept=".md,.json"
            multiple
            className="sr-only"
            disabled={busy}
            onChange={(e) => {
              ingest([...(e.target.files ?? [])]);
              e.target.value = "";
            }}
          />
          <span className="flex size-9 items-center justify-center rounded-full bg-white text-zinc-500 shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-700">
            <Icon d={ICON.upload} />
          </span>
          <span className="text-sm font-medium">
            {busy ? "Ingesting…" : "Drop files or click to upload"}
          </span>
          <span className="text-xs text-zinc-500 dark:text-zinc-400">
            ADR or meeting (.md with frontmatter{" "}
            <code className="font-mono">id</code>), ticket (.json)
          </span>
        </label>

        {rows.length > 0 && (
          <ol className="flex flex-col gap-3 text-sm" aria-live="polite">
            {rows.map((r, i) => (
              <li
                key={`${r.name}-${i}`}
                className="flex flex-col gap-1 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950/40"
              >
                <span className="flex items-center gap-2 font-medium">
                  {r.kind === "done" && (
                    <Icon d={ICON.check} className="size-4 text-emerald-600" />
                  )}
                  <span className="truncate font-mono text-xs">{r.name}</span>
                </span>
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  {r.kind === "queued" && "queued"}
                  {r.kind === "running" && `${STEPS[r.step]}…`}
                  {r.kind === "building" && (
                    <>
                      <Result res={r.res} /> · building the graph in Cognee…
                    </>
                  )}
                  {r.kind === "done" && <Result res={r.res} />}
                  {r.kind === "error" && (
                    <span className="text-red-700 dark:text-red-300">
                      failed: {r.message}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </Card>
  );
}
