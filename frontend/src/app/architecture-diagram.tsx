"use client";

import "@excalidraw/excalidraw/index.css";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { ExcalidrawImperativeAPI, ExcalidrawInitialDataState } from "@excalidraw/excalidraw/types";

// Excalidraw touches window on import, so it only loads in the browser.
const Excalidraw = dynamic(() => import("@excalidraw/excalidraw").then((m) => m.Excalidraw), { ssr: false });

// Copied from docs/ by the predev/prebuild scripts in package.json.
const SCENE_URL = "/architecture.excalidraw";

function useDarkClass() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const html = document.documentElement;
    const sync = () => setDark(html.classList.contains("dark"));
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(html, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);
  return dark;
}

export function ArchitectureDiagram() {
  const [scene, setScene] = useState<ExcalidrawInitialDataState | null>(null);
  const [api, setApi] = useState<ExcalidrawImperativeAPI | null>(null);
  // Wheel and drag go to the page until the reader clicks in, so the diagram never traps scrolling.
  const [active, setActive] = useState(false);
  const dark = useDarkClass();

  useEffect(() => {
    fetch(SCENE_URL)
      .then((r) => r.json())
      .then((data) => setScene({ elements: data.elements, files: data.files, appState: { viewBackgroundColor: "#ffffff" } }));
  }, []);

  useEffect(() => {
    if (!api || !scene) return;
    // Wait a frame so Excalidraw has measured its container before fitting.
    const id = requestAnimationFrame(() => api.scrollToContent(api.getSceneElements(), { fitToContent: true }));
    return () => cancelAnimationFrame(id);
  }, [api, scene]);

  return (
    <div
      className="relative aspect-[1136/1072] w-full overflow-hidden rounded-xl"
      onMouseLeave={() => setActive(false)}
    >
      {scene ? (
        <Excalidraw
          initialData={scene}
          excalidrawAPI={setApi}
          viewModeEnabled
          zenModeEnabled
          theme={dark ? "dark" : "light"}
          UIOptions={{ canvasActions: { changeViewBackgroundColor: false, export: false, loadScene: false, saveToActiveFile: false, toggleTheme: false, clearCanvas: false, saveAsImage: false } }}
        />
      ) : (
        <div className="flex h-full items-center justify-center text-sm text-zinc-500 dark:text-zinc-400">Loading diagram…</div>
      )}
      {!active && (
        <button
          type="button"
          onClick={() => setActive(true)}
          className="group absolute inset-0 z-10 flex items-end justify-center pb-5"
          aria-label="Interact with the architecture diagram"
        >
          <span className="rounded-full bg-zinc-950/80 px-3.5 py-1.5 text-[13px] font-medium text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 dark:bg-white/85 dark:text-zinc-950">
            Click to pan and zoom
          </span>
        </button>
      )}
    </div>
  );
}
