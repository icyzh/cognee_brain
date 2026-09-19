"use client";

import { useEffect, useState } from "react";
import { typeStyle } from "@/components/HopPath";
import { IngestCard } from "@/components/IngestCard";
import { ingestSeed, sources } from "@/lib/api";
import { Card, ErrorState, Pill } from "@/components/ui";
import type { SeedIngestResult, Source } from "@/lib/types";

// Re-ingest data/seed. Unchanged files are skipped by content hash, so this is safe to press.
function SeedSync({ onDone }: { onDone: () => void }) {
  const [state, setState] = useState<
    | { kind: "idle" | "running" }
    | { kind: "done"; res: SeedIngestResult }
    | { kind: "error"; message: string }
  >({ kind: "idle" });

  async function run() {
    setState({ kind: "running" });
    try {
      const res = await ingestSeed();
      setState({ kind: "done", res });
      onDone();
    } catch (e) {
      setState({
        kind: "error",
        message: e instanceof Error ? e.message : String(e),
      });
    }
  }

  return (
    <Card title="Seed folder">
      <div className="flex flex-col gap-3">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Sync <code className="font-mono">data/seed/</code> into the graph.
          Only new or changed files are ingested; a fresh build takes a few
          minutes.
        </p>
        <button
          type="button"
          onClick={run}
          disabled={state.kind === "running"}
          className="self-start rounded-lg bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-wait disabled:opacity-60 dark:bg-white dark:text-zinc-950 dark:hover:bg-zinc-200"
        >
          {state.kind === "running" ? "Syncing…" : "Sync seed folder"}
        </button>
        {state.kind === "done" && (
          <p
            className="text-xs text-zinc-500 dark:text-zinc-400"
            aria-live="polite"
          >
            {state.res.ingested} ingested · {state.res.skipped} unchanged ·{" "}
            {state.res.took_s} s ·{" "}
            {state.res.showcase_missing.length ? (
              <span className="font-medium text-red-600 dark:text-red-400">
                {state.res.showcase_missing.length} expected edges missing
              </span>
            ) : (
              "all expected edges verified"
            )}
          </p>
        )}
        {state.kind === "error" && (
          <p role="alert" className="text-xs text-red-700 dark:text-red-300">
            Sync failed: {state.message}
          </p>
        )}
      </div>
    </Card>
  );
}

export default function SourcesPage() {
  const [rows, setRows] = useState<Source[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState("");

  // /sources#ADR-007 (from an alert) highlights that row once the table exists.
  const fetchRows = () =>
    sources().then(
      (r) => {
        setRows(r);
        const ref = decodeURIComponent(location.hash.slice(1));
        setFocus(ref);
        if (ref)
          requestAnimationFrame(() =>
            document.getElementById(ref)?.scrollIntoView({ block: "center" }),
          );
      },
      (e: Error) => setError(e.message),
    );

  function retry() {
    setError(null);
    fetchRows();
  }

  useEffect(() => {
    fetchRows();
  }, []);

  if (error) return <ErrorState message={error} onRetry={retry} />;

  const th =
    "px-5 py-2.5 text-left text-[11px] font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400";
  return (
    <div className="grid items-start gap-6 xl:grid-cols-3">
      <div className="flex flex-col gap-6 xl:sticky xl:top-20">
        <IngestCard
          title="Add company data"
          description="Upload ADRs, meeting notes and tickets. Each file is added to the knowledge graph and checked against the active decisions on its service."
          onIngested={fetchRows}
        />
        <SeedSync onDone={fetchRows} />
      </div>
      <Card
        title="Ingested files"
        action={rows && <Pill>{rows.length} files</Pill>}
        className="xl:col-span-2"
        bodyClassName="overflow-x-auto"
      >
        {!rows ? (
          <p className="animate-pulse p-5 font-mono text-xs text-zinc-500 dark:text-zinc-400">
            loading…
          </p>
        ) : !rows.length ? (
          <p className="p-5 text-sm text-zinc-500 dark:text-zinc-400">
            Nothing ingested yet. Sync the seed folder or upload files.
          </p>
        ) : (
          <table className="w-full text-[13px]">
            <thead className="bg-zinc-50 dark:bg-zinc-950/40">
              <tr>
                {["Ref", "Type", "Path", "Ingested", "Hash"].map((h) => (
                  <th key={h} className={th}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {rows.map((r) => (
                <tr
                  key={r.path}
                  id={r.ref}
                  className={
                    r.ref === focus
                      ? "bg-amber-50 dark:bg-amber-950/40"
                      : "hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
                  }
                >
                  <td className="px-5 py-3 font-mono font-semibold">{r.ref}</td>
                  <td className="px-5 py-3">
                    <span
                      className={`rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${typeStyle(r.type)}`}
                    >
                      {r.type}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono text-zinc-600 dark:text-zinc-400">
                    {r.path}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 tabular-nums text-zinc-600 dark:text-zinc-400">
                    {r.ingested_at}
                  </td>
                  <td className="px-5 py-3 font-mono text-zinc-500">
                    {r.content_hash.slice(0, 8)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
