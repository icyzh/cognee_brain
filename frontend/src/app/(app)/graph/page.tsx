"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { BASE, graph } from "@/lib/api";
import { Card, ErrorState, Pill } from "@/components/ui";
import type { GraphData, PathEdge } from "@/lib/types";

// Canvas + d3-force touch `window`, so no SSR.
const GraphCanvas = dynamic(() => import("@/components/GraphCanvas"), { ssr: false });

type View = { nodes: GraphData["nodes"]; links: { source: string; target: string; rel: string }[]; path: PathEdge[] };

function lastPath(): PathEdge[] {
  try {
    return JSON.parse(sessionStorage.getItem("lastPath") ?? "[]");
  } catch {
    return [];
  }
}

export default function GraphPage() {
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState("");
  const [depth, setDepth] = useState(2);
  const [cognee, setCognee] = useState(false); // Cognee's own rendered page instead of ours
  const [size, setSize] = useState({ width: 0, height: 0 });
  const box = useRef<HTMLDivElement>(null);

  const load = (f: string, d: number) =>
    graph(f || undefined, d).then(
      (g: GraphData) => {
        setError(null);
        // force-graph mutates links (ids → node objects), so hand it fresh copies.
        setView({ nodes: g.nodes.map((n) => ({ ...n })), links: g.edges.map((e) => ({ source: e.from, target: e.to, rel: e.rel })), path: lastPath() });
      },
      (e: Error) => setError(e.message),
    );

  useEffect(() => {
    load("", 2);
    const ro = new ResizeObserver(([e]) => setSize({ width: e.contentRect.width, height: e.contentRect.height }));
    if (box.current) ro.observe(box.current);
    return () => ro.disconnect();
  }, []);

  const dim = !!view?.path.length;

  const reload = (f: string) => {
    setFocus(f);
    setView(null);
    load(f, depth);
  };

  const legend: [string, string][] = [
    ["Service / Meeting", "bg-blue-500"],
    ["Decision", "bg-amber-500"],
    ["Ticket", "bg-orange-500"],
    ["Person / Team", "bg-emerald-500"],
  ];

  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          Knowledge graph
          {view && <Pill>{view.nodes.length} nodes · {view.links.length} links</Pill>}
          {dim && <Pill tone="green">last answer&apos;s path highlighted</Pill>}
        </span>
      }
      action={
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            reload(focus.trim());
          }}
        >
          <label htmlFor="focus" className="sr-only">
            Focus node
          </label>
          <input
            id="focus"
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            placeholder="Focus, e.g. ADR-007"
            className="h-8 w-40 rounded-md border border-zinc-200 bg-white px-2.5 text-[13px] outline-none focus:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-500"
          />
          <label htmlFor="depth" className="sr-only">
            Depth
          </label>
          <select
            id="depth"
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="h-8 rounded-md border border-zinc-200 bg-white px-2 text-[13px] dark:border-zinc-700 dark:bg-zinc-950"
          >
            {[1, 2, 3, 4].map((d) => (
              <option key={d} value={d}>
                {d} hop{d > 1 && "s"}
              </option>
            ))}
          </select>
          <button type="submit" className="h-8 rounded-md bg-zinc-950 px-3 text-[13px] font-medium text-white hover:bg-zinc-800 dark:bg-white dark:text-zinc-950 dark:hover:bg-zinc-200">
            Load
          </button>
          <button type="button" onClick={() => setCognee(!cognee)} className="h-8 rounded-md border border-zinc-200 px-3 text-[13px] hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-500">
            {cognee ? "Our view" : "Cognee view"}
          </button>
          {focus && (
            <button type="button" onClick={() => reload("")} className="h-8 rounded-md px-2 text-[13px] text-zinc-500 hover:text-zinc-950 dark:hover:text-zinc-50">
              Reset
            </button>
          )}
        </form>
      }
      bodyClassName="flex flex-col"
    >
      <div ref={box} className="relative h-[calc(100vh-260px)] min-h-[420px] overflow-hidden bg-[radial-gradient(circle,#e4e4e7_1px,transparent_1px)] [background-size:20px_20px] dark:bg-[radial-gradient(circle,#27272a_1px,transparent_1px)]">
        {cognee ? (
          <iframe src={`${BASE}/graph/cognee`} title="Cognee knowledge graph" className="absolute inset-0 size-full border-0 bg-white" />
        ) : error ? (
          <div className="p-5">
            <ErrorState message={error} onRetry={() => load(focus.trim(), depth)} />
          </div>
        ) : !view ? (
          <p className="animate-pulse p-5 font-mono text-xs text-zinc-500 dark:text-zinc-400">loading graph…</p>
        ) : !view.nodes.length ? (
          <p className="p-5 text-sm text-zinc-500 dark:text-zinc-400">No nodes{focus && ` around ${focus}`}.</p>
        ) : (
          size.width > 0 && <GraphCanvas data={view} path={view.path} width={size.width} height={size.height} onFocus={reload} />
        )}
      </div>
      <footer className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-zinc-100 px-5 py-3 text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
        {legend.map(([label, dot]) => (
          <span key={label} className="flex items-center gap-1.5">
            <span className={`size-2.5 rounded-full ${dot}`} />
            {label}
          </span>
        ))}
        <span className="ml-auto">scroll to zoom · drag to pan · click a node to focus</span>
      </footer>
    </Card>
  );
}
