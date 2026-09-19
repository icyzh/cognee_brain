import type { PathEdge } from "@/lib/types";

// Node-type colours from docs/architecture.excalidraw (Service/Meeting blue, Decision amber,
// Ticket orange, Person/Team green). Keys cover both graph node types and evidence source types.
const BLUE = "border-blue-300 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-200";
const AMBER = "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200";
const ORANGE = "border-orange-300 bg-orange-50 text-orange-900 dark:border-orange-800 dark:bg-orange-950/50 dark:text-orange-200";
const GREEN = "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200";
const ZINC = "border-zinc-300 bg-zinc-50 text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200";

const TYPE_STYLE: Record<string, string> = {
  service: BLUE,
  meeting: BLUE,
  decision: AMBER,
  adr: AMBER,
  ticket: ORANGE,
  person: GREEN,
  team: GREEN,
  org: GREEN,
};

export const typeStyle = (type: string) => TYPE_STYLE[type.toLowerCase()] ?? ZINC;

export function HopPath({ path }: { path: PathEdge[] }) {
  const nodes = [path[0].from, ...path.map((e) => e.to)];
  return (
    <ol className="flex flex-col font-mono text-[13px]">
      {nodes.map((n, i) => (
        <li key={`${n.id}-${i}`} className="flex flex-col">
          <div className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 ${typeStyle(n.type)}`}>
            <span className="truncate font-medium">{n.id}</span>
            <span className="shrink-0 text-[10px] uppercase tracking-wide opacity-70">{n.type}</span>
          </div>
          {i < path.length && (
            <div className="ml-4 flex items-center gap-2 border-l-2 border-dashed border-zinc-300 py-1.5 pl-4 text-[11px] text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
              {path[i].rel}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
