// Shared by the graph page and the (client-only, dynamically imported) 3D canvas.

// Same palette as HopPath / architecture.excalidraw, as hex for WebGL.
const HEX: Record<string, string> = {
  service: "#3b82f6",
  meeting: "#3b82f6",
  decision: "#f59e0b",
  ticket: "#f97316",
  person: "#10b981",
  team: "#10b981",
};
export const hex = (type: string) => HEX[type.toLowerCase()] ?? "#a1a1aa";

// Link ends start as ids and become node objects once the simulation runs.
export const idOf = (x: unknown) => String(x && typeof x === "object" ? (x as { id: unknown }).id : x);
