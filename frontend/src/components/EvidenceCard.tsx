import type { Evidence } from "@/lib/types";
import { typeStyle } from "./HopPath";

const LABEL: Record<string, string> = { adr: "ADR", ticket: "Ticket", meeting: "Meeting", org: "Org" };

export function EvidenceCard({ e }: { e: Evidence }) {
  return (
    <article className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-zinc-50/60 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/40">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[13px] font-semibold">{e.ref}</span>
        <span className={`rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${typeStyle(e.source)}`}>{LABEL[e.source] ?? e.source}</span>
      </div>
      <p className="text-[13px] leading-snug text-zinc-700 dark:text-zinc-300">“{e.snippet}”</p>
      <span className="mt-auto truncate font-mono text-[11px] text-zinc-500 dark:text-zinc-400">{e.path}</span>
    </article>
  );
}
