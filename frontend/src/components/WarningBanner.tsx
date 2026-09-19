import type { Warning } from "@/lib/types";

const STYLE = {
  stale: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200",
  contradiction: "border-red-300 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
};

export function WarningBanner({ w }: { w: Warning }) {
  return (
    <div role="alert" className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-[13px] ${STYLE[w.kind]}`}>
      <svg viewBox="0 0 24 24" className="mt-px size-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 3 22 20H2zM12 9v5M12 17v.01" />
      </svg>
      <span>
        <span className="font-semibold">{w.kind === "stale" ? "Stale" : "Contradiction"}:</span> {w.message}
      </span>
    </div>
  );
}
