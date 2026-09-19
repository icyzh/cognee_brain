"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ALERTS_CHANGED, alerts as fetchAlerts, ingestFile } from "@/lib/api";
import { Card, ErrorState, ICON, Icon, Pill } from "@/components/ui";
import type { Alert, IngestResult } from "@/lib/types";

const STEPS = ["parsing", "structural", "cognify", "checking contradictions"];
// ponytail: POST /ingest is one request, so steps advance on typical timings, not server events.
// Stream progress (SSE) from the backend if the estimate drifts.
const STEP_AT_MS = [0, 1500, 4000, 15000];

type Upload =
  | { kind: "idle" }
  | { kind: "running"; name: string; step: number }
  | { kind: "done"; res: IngestResult }
  | { kind: "error"; message: string };

const refLink = (ref: string | null) =>
  ref && (
    <Link href={`/sources#${ref}`} className="font-mono underline decoration-dotted underline-offset-2 hover:decoration-solid">
      {ref}
    </Link>
  );

function AlertRow({ a }: { a: Alert }) {
  const red = a.kind === "contradiction";
  return (
    <article className={`flex flex-col gap-1.5 border-l-[3px] px-5 py-4 ${red ? "border-red-500" : "border-amber-400"}`}>
      <h3 className="text-[15px] font-semibold">
        {red ? (
          <>
            {refLink(a.new_ref)} contradicts {refLink(a.existing_ref)}
          </>
        ) : (
          <>
            {refLink(a.existing_ref)} is stale{a.new_ref && <> · superseded by {refLink(a.new_ref)}</>}
          </>
        )}
      </h3>
      {a.reason && <p className="text-sm leading-snug text-zinc-600 dark:text-zinc-300">{a.reason}</p>}
      <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-zinc-500 dark:text-zinc-400">
        {a.service && <Pill>{a.service}</Pill>}
        {a.people?.length ? <Pill>{a.people.join(", ")}</Pill> : null}
        {a.confidence != null && <Pill tone={red ? "red" : "amber"}>confidence {a.confidence.toFixed(2)}</Pill>}
        <span className="ml-auto font-mono">{a.created_at}</span>
      </div>
    </article>
  );
}

function AlertSection({ title, items, tone }: { title: string; items: Alert[]; tone: "red" | "amber" }) {
  return (
    <Card title={title} action={<Pill tone={items.length ? tone : "zinc"}>{items.length}</Pill>} bodyClassName="divide-y divide-zinc-100 dark:divide-zinc-800">
      {items.length ? (
        items.map((a) => <AlertRow key={a.id} a={a} />)
      ) : (
        <p className="px-5 py-6 text-sm text-zinc-500 dark:text-zinc-400">None.</p>
      )}
    </Card>
  );
}

export default function AlertsPage() {
  const [list, setList] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upload, setUpload] = useState<Upload>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const load = () =>
    fetchAlerts().then(
      (a) => {
        setError(null);
        setList(a);
      },
      (e: Error) => setError(e.message),
    );

  useEffect(() => {
    load();
    return () => timers.current.forEach(clearTimeout);
  }, []);

  async function ingest(file: File | undefined) {
    if (!file || upload.kind === "running") return;
    setUpload({ kind: "running", name: file.name, step: 0 });
    timers.current = STEP_AT_MS.slice(1).map((ms, i) =>
      setTimeout(() => setUpload((u) => (u.kind === "running" ? { ...u, step: i + 1 } : u)), ms),
    );
    try {
      const res = await ingestFile(file);
      setUpload({ kind: "done", res });
      await load();
      window.dispatchEvent(new Event(ALERTS_CHANGED));
    } catch (e) {
      setUpload({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    } finally {
      timers.current.forEach(clearTimeout);
    }
  }

  const contradictions = list?.filter((a) => a.kind === "contradiction") ?? [];
  const stale = list?.filter((a) => a.kind === "stale") ?? [];

  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="grid items-start gap-6 xl:grid-cols-3">
      <Card title="Live ingest" className="xl:sticky xl:top-20">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Add a doc to the graph. It is checked against every active decision on the same service.
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
              ingest(e.dataTransfer.files[0]);
            }}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition ${
              dragging
                ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                : "border-zinc-200 bg-zinc-50 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-950/40 dark:hover:border-zinc-600"
            }`}
          >
            <input
              type="file"
              accept=".md,.json,.txt"
              className="sr-only"
              disabled={upload.kind === "running"}
              onChange={(e) => {
                ingest(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            <span className="flex size-9 items-center justify-center rounded-full bg-white text-zinc-500 shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-700">
              <Icon d={ICON.upload} />
            </span>
            <span className="text-sm font-medium">Drop a file or click to upload</span>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">ADR or meeting (.md), ticket (.json)</span>
          </label>

          {upload.kind === "running" && (
            <ol className="flex flex-col gap-2 text-sm" aria-live="polite">
              <li className="truncate font-mono text-xs text-zinc-500 dark:text-zinc-400">{upload.name}</li>
              {STEPS.map((s, i) => (
                <li key={s} className="flex items-center gap-2.5">
                  <span
                    className={`flex size-5 items-center justify-center rounded-full text-[10px] ${
                      i < upload.step
                        ? "bg-emerald-500 text-white"
                        : i === upload.step
                          ? "animate-pulse bg-zinc-950 text-white dark:bg-white dark:text-zinc-950"
                          : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800"
                    }`}
                  >
                    {i < upload.step ? <Icon d={ICON.check} className="size-3" /> : i + 1}
                  </span>
                  <span className={i > upload.step ? "text-zinc-400 dark:text-zinc-500" : ""}>
                    {s}
                    {i === upload.step && "…"}
                  </span>
                </li>
              ))}
            </ol>
          )}
          {upload.kind === "done" && (
            <div className="flex flex-col gap-1 rounded-lg bg-zinc-50 p-3 text-sm dark:bg-zinc-950/40" aria-live="polite">
              <span className="flex items-center gap-2 font-medium">
                <Icon d={ICON.check} className="size-4 text-emerald-600" />
                <span className="font-mono">{upload.res.source_ref}</span> ingested
              </span>
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                {(upload.res.took_ms / 1000).toFixed(1)} s · {upload.res.nodes_added} nodes added ·{" "}
                {upload.res.alerts.length ? (
                  <span className="font-medium text-red-600 dark:text-red-400">
                    {upload.res.alerts.length} new alert{upload.res.alerts.length > 1 && "s"}
                  </span>
                ) : (
                  "no conflicts found"
                )}
              </span>
            </div>
          )}
          {upload.kind === "error" && (
            <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
              Ingest failed: {upload.message}
            </p>
          )}
        </div>
      </Card>

      <div className="flex flex-col gap-6 xl:col-span-2">
        {!list ? (
          <Card bodyClassName="p-5">
            <p className="animate-pulse font-mono text-xs text-zinc-500 dark:text-zinc-400">loading alerts…</p>
          </Card>
        ) : (
          <>
            <AlertSection title="Contradictions" items={contradictions} tone="red" />
            <AlertSection title="Stale decisions" items={stale} tone="amber" />
          </>
        )}
      </div>
    </div>
  );
}
