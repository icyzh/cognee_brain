"use client";

import { useEffect, useRef } from "react";
import ForceGraph2D, { type ForceGraphMethods } from "react-force-graph-2d";
import type { GraphData, PathEdge } from "@/lib/types";

// Same palette as HopPath / architecture.excalidraw, as hex for the canvas.
const HEX: Record<string, string> = {
  service: "#3b82f6",
  meeting: "#3b82f6",
  decision: "#f59e0b",
  ticket: "#f97316",
  person: "#10b981",
  team: "#10b981",
};
const hex = (type: string) => HEX[type.toLowerCase()] ?? "#a1a1aa";

// Link ends start as ids and become node objects once the simulation runs.
const idOf = (x: unknown) => String(x && typeof x === "object" ? (x as { id: unknown }).id : x);

type Node = GraphData["nodes"][number];
type Link = { source: string; target: string; rel: string };

export default function GraphCanvas({
  data,
  path,
  width,
  height,
  onFocus,
}: {
  data: { nodes: Node[]; links: Link[] };
  path: PathEdge[];
  width: number;
  height: number;
  onFocus: (id: string) => void;
}) {
  const fg = useRef<ForceGraphMethods<Node, Link>>(undefined);

  useEffect(() => {
    fg.current?.d3Force("charge")?.strength(-220);
    fg.current?.d3Force("link")?.distance(60);
  }, [data]);

  const onPath = new Set(path.flatMap((e) => [e.from.id, e.to.id]));
  const dim = onPath.size > 0;
  const pathEdge = (l: { source?: unknown; target?: unknown }) => {
    const [s, t] = [idOf(l.source), idOf(l.target)];
    return path.some((e) => (e.from.id === s && e.to.id === t) || (e.from.id === t && e.to.id === s));
  };

  return (
    <ForceGraph2D<Node, Link>
      ref={fg}
      width={width}
      height={height}
      graphData={data}
      cooldownTicks={120}
      onEngineStop={() => fg.current?.zoomToFit(400, 40)}
      nodeLabel={(n) => `${n.type}: ${n.label}`}
      nodeVal={(n) => (onPath.has(n.id) ? 4 : 1.5)}
      nodeColor={(n) => (dim && !onPath.has(n.id) ? `${hex(n.type)}55` : hex(n.type))}
      nodeCanvasObjectMode={() => "after"}
      nodeCanvasObject={(n, ctx, scale) => {
        if (scale < 1 && !onPath.has(n.id)) return; // path labels always, the rest once zoomed in
        const dark = document.documentElement.classList.contains("dark");
        ctx.font = `${(onPath.has(n.id) ? 12 : 10) / scale}px ui-monospace, monospace`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = dark ? "#e4e4e7" : "#27272a";
        ctx.fillText(n.id, n.x ?? 0, (n.y ?? 0) + 8);
      }}
      linkLabel={(l) => l.rel}
      linkColor={(l) => (pathEdge(l) ? "#2563eb" : dim ? "#a1a1aa44" : "#a1a1aa")}
      linkWidth={(l) => (pathEdge(l) ? 3 : 1)}
      linkDirectionalArrowLength={4}
      linkDirectionalArrowRelPos={1}
      onNodeClick={(n) => onFocus(n.id)}
    />
  );
}
