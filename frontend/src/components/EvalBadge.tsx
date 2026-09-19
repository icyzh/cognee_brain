"use client";

import type { EvalLatest, EvalSummary } from "@/lib/types";
import { ICON, Icon } from "./ui";

const mark = (ok?: boolean | null) =>
  ok === undefined || ok === null ? (
    <span className="text-zinc-400">–</span>
  ) : ok ? (
    <span className="text-emerald-600 dark:text-emerald-400">✓</span>
  ) : (
    <span className="text-red-600 dark:text-red-400">✗</span>
  );

const pct = (x?: number) => (x === undefined ? "–" : `${Math.round(x * 100)}%`);
const frac = (n?: number, d?: number) => (n === undefined ? "–" : d === undefined ? `${n}` : `${n}/${d}`);

function Summary({ name, s }: { name: string; s: EvalSummary | null }) {
  return (
    <tr>
      <td className="px-5 py-2.5 font-medium">{name}</td>
      <td className="px-5 py-2.5 font-mono tabular-nums">{s ? `${s.grounded_ok}/${s.total}` : "not run"}</td>
      <td className="px-5 py-2.5 font-mono tabular-nums">{frac(s?.path_ok, s?.path_total)}</td>
      <td className="px-5 py-2.5 font-mono tabular-nums">{frac(s?.stale_flagged, s?.stale_total)}</td>
      <td className="px-5 py-2.5 font-mono tabular-nums">{pct(s?.ref_recall)}</td>
      <td className="px-5 py-2.5 font-mono tabular-nums">{s?.hallucinated_sources ?? "–"}</td>
    </tr>
  );
}

const th = "px-5 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400";

// Eval badge + drill-down: Permafrost vs raw Cognee, overall and per question.
export function EvalBadge({ data }: { data: EvalLatest | null }) {
  const pf = data?.decision_brain;
  if (!pf) return null;
  const raw = data.raw_cognee;
  const rawByQ = new Map(raw?.results.map((r) => [r.q, r]));

  return (
    <details className="group rounded-xl border border-zinc-200 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] dark:border-zinc-800 dark:bg-zinc-900">
      <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-5 py-2.5 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-3">
          <span className="text-sm font-semibold tracking-tight">Evaluation</span>
          <span className="rounded-md bg-emerald-50 px-2 py-0.5 font-mono text-xs text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
            Eval {pf.grounded_ok}/{pf.total} grounded · {pf.hallucinated_sources} hallucinated sources
          </span>
        </span>
        <span className="flex items-center gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Permafrost vs raw Cognee
          <Icon d={ICON.chevron} className="size-4 transition group-open:rotate-90" />
        </span>
      </summary>
      <div className="overflow-x-auto border-t border-zinc-100 text-[13px] dark:border-zinc-800">
        <table className="w-full">
          <thead className="bg-zinc-50 dark:bg-zinc-950/40">
            <tr>
              <th className={th}>Variant</th>
              <th className={th}>Grounded OK</th>
              <th className={th}>Verified path</th>
              <th className={th}>Stale flagged</th>
              <th className={th}>Ref recall</th>
              <th className={th}>Hallucinated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            <Summary name="Permafrost" s={pf} />
            <Summary name="Raw Cognee" s={raw} />
          </tbody>
        </table>
        <table className="w-full border-t border-zinc-100 dark:border-zinc-800">
          <thead className="bg-zinc-50 dark:bg-zinc-950/40">
            <tr>
              <th className={th}>Question</th>
              <th className={`${th} !text-center`}>Permafrost</th>
              <th className={`${th} !text-center`}>Raw Cognee</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {pf.results.map((r) => {
              const b = rawByQ.get(r.q);
              return (
                <tr key={r.q} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/40">
                  <td className="px-5 py-2.5 text-zinc-700 dark:text-zinc-300">{r.q}</td>
                  <td className="whitespace-nowrap px-5 py-2.5 text-center font-mono tabular-nums">
                    {mark(r.grounded_ok)} {pct(r.ref_recall)}
                    {r.path_ok != null && <> · path {mark(r.path_ok)}</>}
                    {r.stale_ok != null && <> · stale {mark(r.stale_ok)}</>}
                  </td>
                  <td className="whitespace-nowrap px-5 py-2.5 text-center font-mono tabular-nums">
                    {mark(b?.grounded_ok)} {pct(b?.ref_recall)}
                    {b?.path_ok != null && <> · path {mark(b.path_ok)}</>}
                    {b?.stale_ok != null && <> · stale {mark(b.stale_ok)}</>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="border-t border-zinc-100 px-5 py-2.5 font-mono text-[11px] text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
          ✓/✗ = grounded correct · % = expected refs cited · path = verified hop path ends at the right team · run {pf.run_at}
        </p>
      </div>
    </details>
  );
}
