"use client";

import { useEffect, useState } from "react";
import { typeStyle } from "@/components/HopPath";
import { sources } from "@/lib/api";
import { Card, ErrorState, Pill } from "@/components/ui";
import type { Source } from "@/lib/types";

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
        if (ref) requestAnimationFrame(() => document.getElementById(ref)?.scrollIntoView({ block: "center" }));
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

  const th = "px-5 py-2.5 text-left text-[11px] font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400";
  return (
    <Card title="Ingested files" action={rows && <Pill>{rows.length} files</Pill>} bodyClassName="overflow-x-auto">
      {!rows ? (
        <p className="animate-pulse p-5 font-mono text-xs text-zinc-500 dark:text-zinc-400">loading…</p>
      ) : !rows.length ? (
        <p className="p-5 text-sm text-zinc-500 dark:text-zinc-400">
          Nothing ingested yet. Run <code className="font-mono">POST /ingest</code>.
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
                className={r.ref === focus ? "bg-amber-50 dark:bg-amber-950/40" : "hover:bg-zinc-50 dark:hover:bg-zinc-800/40"}
              >
                <td className="px-5 py-3 font-mono font-semibold">{r.ref}</td>
                <td className="px-5 py-3">
                  <span className={`rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${typeStyle(r.type)}`}>{r.type}</span>
                </td>
                <td className="px-5 py-3 font-mono text-zinc-600 dark:text-zinc-400">{r.path}</td>
                <td className="whitespace-nowrap px-5 py-3 tabular-nums text-zinc-600 dark:text-zinc-400">{r.ingested_at}</td>
                <td className="px-5 py-3 font-mono text-zinc-500">{r.content_hash.slice(0, 8)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
