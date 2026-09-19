"use client";

import { useEffect, useState } from "react";
import { ALERTS_CHANGED, timeline } from "@/lib/api";
import type { TimelineEntry } from "@/lib/types";
import { Card, Pill } from "./ui";

const STYLE: Record<TimelineEntry["status"], string> = {
  active: "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/40",
  superseded: "border-zinc-200 bg-zinc-50 text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400",
  proposed: "border-dashed border-red-300 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
};

// Decision history of the service the answer is about: validity intervals, not just a stale flag.
// The date input answers "what was true on that day?"; open contradictions show as proposals.
export function Timeline({ service }: { service: string }) {
  const [asOf, setAsOf] = useState("");
  const [entries, setEntries] = useState<TimelineEntry[] | null>(null);

  useEffect(() => {
    let live = true;
    const load = () => timeline(service, asOf || undefined).then((t) => live && setEntries(t.entries), () => live && setEntries(null));
    load();
    window.addEventListener(ALERTS_CHANGED, load); // a live upload adds a proposal
    return () => {
      live = false;
      window.removeEventListener(ALERTS_CHANGED, load);
    };
  }, [service, asOf]);

  if (!entries?.length) return null;
  return (
    <Card
      title={`Decision timeline · ${service}`}
      action={
        <label className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          as of
          <input
            type="date"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            className="rounded-md border border-zinc-200 bg-transparent px-2 py-1 font-mono text-xs dark:border-zinc-700"
          />
        </label>
      }
    >
      <ol className="flex flex-col gap-2 font-mono text-[13px]">
        {entries.map((e) => (
          <li key={`${e.ref}-${e.contradicts ?? ""}`} className={`flex flex-col gap-1 rounded-lg border px-3 py-2 ${STYLE[e.status]} ${e.in_force ? "ring-2 ring-emerald-500/60" : ""}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className={`font-medium ${e.status === "superseded" ? "line-through" : ""}`}>{e.ref}</span>
              <span className="flex items-center gap-2 text-[11px]">
                {e.valid_from} → {e.valid_to ?? (e.status === "proposed" ? "proposal" : "now")}
                {e.in_force && <Pill tone="green">in force{asOf ? ` on ${asOf}` : ""}</Pill>}
                {e.status === "superseded" && <Pill>superseded by {e.superseded_by?.join(", ")}</Pill>}
                {e.status === "proposed" && <Pill tone="red">contradicts {e.contradicts}</Pill>}
              </span>
            </div>
            <span className="font-sans text-[13px]">{e.title}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
