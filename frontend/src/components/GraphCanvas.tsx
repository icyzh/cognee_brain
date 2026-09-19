"use client";

import { useEffect, useMemo, useRef } from "react";
import ForceGraph3D, { type ForceGraphMethods } from "react-force-graph-3d";
import SpriteText from "three-spritetext";
import { hex, idOf } from "@/lib/graph";
import type { GraphData, PathEdge } from "@/lib/types";

const REL = 6; // sphere radius = REL * cbrt(nodeVal)

type Node = GraphData["nodes"][number] & { x?: number; y?: number; z?: number };
export type Link = { source: string; target: string; rel: string };

export default function GraphCanvas({
  data,
  path,
  width,
  height,
  selected,
  onSelect,
}: {
  data: { nodes: Node[]; links: Link[] };
  path: PathEdge[];
  width: number;
  height: number;
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const fg = useRef<ForceGraphMethods<Node, Link>>(undefined);

  useEffect(() => {
    fg.current?.d3Force("charge")?.strength(-160);
    fg.current?.d3Force("link")?.distance(50);
  }, [data]);

  // The selected node plus everything one edge away stays lit; the rest dims.
  const lit = useMemo(() => {
    if (!selected) return null;
    const ids = new Set([selected]);
    for (const l of data.links) {
      const [s, t] = [idOf(l.source), idOf(l.target)];
      if (s === selected) ids.add(t);
      if (t === selected) ids.add(s);
    }
    return ids;
  }, [selected, data]);

  // Fly the camera to the selected node, keeping it in front.
  useEffect(() => {
    const n = selected && data.nodes.find((x) => x.id === selected);
    if (!n || n.x === undefined) return;
    const ratio = 1 + 260 / Math.max(Math.hypot(n.x, n.y ?? 0, n.z ?? 0), 1);
    fg.current?.cameraPosition({ x: n.x * ratio, y: (n.y ?? 0) * ratio, z: (n.z ?? 0) * ratio }, { x: n.x, y: n.y ?? 0, z: n.z ?? 0 }, 900);
  }, [selected, data]);

  const onPath = new Set(path.flatMap((e) => [e.from.id, e.to.id]));
  const pathEdge = (l: { source?: unknown; target?: unknown }) => {
    const [s, t] = [idOf(l.source), idOf(l.target)];
    return path.some((e) => (e.from.id === s && e.to.id === t) || (e.from.id === t && e.to.id === s));
  };
  const touches = (l: { source?: unknown; target?: unknown }) => !!selected && (idOf(l.source) === selected || idOf(l.target) === selected);
  const focusSet = lit ?? (onPath.size ? onPath : null); // what stays bright
  const val = (n: Node) => (n.id === selected ? 5 : onPath.has(n.id) || lit?.has(n.id) ? 3 : 1.5);
  const idle = "#71717a"; // resting link colour, readable on both themes
  const dark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");

  return (
    <ForceGraph3D<Node, Link>
      ref={fg}
      width={width}
      height={height}
      graphData={data}
      backgroundColor="rgba(0,0,0,0)"
      showNavInfo={false}
      cooldownTicks={120}
      onEngineStop={() => !selected && fg.current?.zoomToFit(600, 60)}
      nodeLabel={(n) => `${n.type}: ${n.label}`}
      nodeVal={val}
      nodeColor={(n) => (focusSet && !focusSet.has(n.id) ? `${hex(n.type)}30` : hex(n.type))}
      nodeOpacity={0.95}
      nodeRelSize={REL}
      nodeResolution={16}
      linkOpacity={0.55}
      nodeThreeObjectExtend
      nodeThreeObject={(n: Node) => {
        // Small graph: label everything. Big graph: only where the eye should go.
        if (focusSet ? !focusSet.has(n.id) : data.nodes.length > 80) return undefined as never;
        const label = new SpriteText(n.id, n.id === selected ? 5 : 3.5, dark ? "#e4e4e7" : "#18181b");
        label.fontFace = "ui-monospace, monospace";
        label.fontWeight = n.id === selected ? "700" : "400";
        // three ships no types here; SpriteText is a THREE.Sprite. Sit above the sphere and draw over it.
        const sprite = label as unknown as { position: { set(x: number, y: number, z: number): void }; material: { depthTest: boolean }; renderOrder: number };
        sprite.position.set(0, REL * Math.cbrt(val(n)) + 5, 0);
        sprite.material.depthTest = false;
        sprite.renderOrder = 1;
        return label;
      }}
      linkLabel={(l) => l.rel}
      linkColor={(l) => (touches(l) ? "#10b981" : pathEdge(l) ? "#2563eb" : focusSet ? `${idle}30` : idle)}
      linkWidth={(l) => (touches(l) || pathEdge(l) ? 1.8 : 0.6)}
      linkDirectionalArrowLength={3}
      linkDirectionalArrowRelPos={1}
      linkDirectionalParticles={(l) => (touches(l) ? 2 : 0)}
      linkDirectionalParticleWidth={1.6}
      onNodeClick={(n) => onSelect(n.id === selected ? null : n.id)}
      onBackgroundClick={() => onSelect(null)}
    />
  );
}
