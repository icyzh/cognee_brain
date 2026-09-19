"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { AnswerPanel, AnswerSkeleton } from "@/components/AnswerPanel";
import { AskBox } from "@/components/AskBox";
import { EvalBadge } from "@/components/EvalBadge";
import { Card, ErrorState, ICON, Icon, Pill, Stat } from "@/components/ui";
import { alerts, ask, evalLatest, history, sources } from "@/lib/api";
import type { Alert, AskResponse, EvalLatest, HistoryItem, Source } from "@/lib/types";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "done"; res: AskResponse }
  | { kind: "error"; message: string };

// KPI row: each figure loads on its own and shows "–" if its endpoint isn't there yet.
function useOverview() {
  const [ev, setEv] = useState<EvalLatest | null>(null);
  const [al, setAl] = useState<Alert[] | null>(null);
  const [src, setSrc] = useState<Source[] | null>(null);
  useEffect(() => {
    evalLatest().then(setEv, () => {});
    alerts().then(setAl, () => {});
    sources().then(setSrc, () => {});
  }, []);
  return { ev, al, src };
}

function Overview({ ev, al, src }: ReturnType<typeof useOverview>) {
  const pf = ev?.decision_brain;
  const raw = ev?.raw_cognee;
  const contradictions = al?.filter((a) => a.kind === "contradiction").length ?? 0;
  const types = src ? new Set(src.map((s) => s.type)).size : 0;
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
      <Stat
        label="Grounded answers"
        icon={ICON.check}
        value={pf ? `${pf.grounded_ok}/${pf.total}` : "–"}
        tone={pf ? "good" : "neutral"}
        hint={raw ? `raw Cognee: ${raw.grounded_ok}/${raw.total}` : pf ? "eval set" : "no eval run yet"}
      />
      <Stat
        label="Hallucinated sources"
        icon={ICON.shield}
        value={pf ? pf.hallucinated_sources : "–"}
        tone={pf ? (pf.hallucinated_sources ? "bad" : "good") : "neutral"}
        hint={raw ? `raw Cognee: ${raw.hallucinated_sources}` : undefined}
      />
      <Stat
        label="Open alerts"
        icon={ICON.alert}
        value={al ? al.length : "–"}
        tone={contradictions ? "bad" : "neutral"}
        hint={al ? `${contradictions} contradiction${contradictions === 1 ? "" : "s"} · ${al.length - contradictions} stale` : undefined}
      />
      <Stat
        label="Sources indexed"
        icon={ICON.sources}
        value={src ? src.length : "–"}
        hint={src ? `${types} source type${types === 1 ? "" : "s"}` : undefined}
      />
    </div>
  );
}

function Ask() {
  const initial = useSearchParams().get("q") ?? "";
  const [state, setState] = useState<State>({ kind: initial ? "loading" : "idle" });
  const last = useRef(initial);
  const overview = useOverview();
  const [recent, setRecent] = useState<HistoryItem[]>([]);
  useEffect(() => {
    history().then(setRecent, () => {});
  }, []);

  function run(question: string) {
    last.current = question;
    setState({ kind: "loading" });
    fetchAnswer(question);
  }

  async function fetchAnswer(question: string) {
    try {
      const res = await ask(question);
      setState({ kind: "done", res });
      try {
        sessionStorage.setItem("lastPath", JSON.stringify(res.path)); // highlighted on /graph
      } catch {}
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }

  // /ask?q=… (from the landing page) asks straight away.
  useEffect(() => {
    if (initial) fetchAnswer(initial);
  }, [initial]);

  return (
    <>
      <Overview {...overview} />
      <AskBox key={initial} initial={initial} busy={state.kind === "loading"} onAsk={run} />
      {state.kind === "idle" && recent.length > 0 && (
        <Card title="Recent answers" action={<Pill>stored · opens instantly</Pill>} bodyClassName="flex flex-col divide-y divide-zinc-100 dark:divide-zinc-800">
          {recent.map((h) => (
            <button
              key={h.question}
              type="button"
              onClick={() => setState({ kind: "done", res: h.response })}
              className="flex flex-col gap-1 px-5 py-3 text-left transition hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
            >
              <span className="flex flex-wrap items-center gap-2 text-sm font-medium">
                {h.question}
                {h.response.path.length > 0 && <Pill tone="green">{h.response.path.length} hops</Pill>}
                {h.response.warnings.map((w) => (
                  <Pill key={`${w.kind}-${w.node}`} tone={w.kind === "stale" ? "amber" : "red"}>{w.kind} · {w.node}</Pill>
                ))}
              </span>
              <span className="line-clamp-2 text-[13px] text-zinc-500 dark:text-zinc-400">{h.response.answer}</span>
            </button>
          ))}
        </Card>
      )}
      {state.kind === "idle" && recent.length === 0 && (
        <Card bodyClassName="flex flex-col items-center gap-3 px-6 py-14 text-center">
          <span className="flex size-10 items-center justify-center rounded-full bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
            <Icon d={ICON.graph} className="size-5" />
          </span>
          <p className="font-medium">Ask a question about your company&apos;s decisions</p>
          <p className="max-w-md text-sm text-zinc-500 dark:text-zinc-400">
            You&apos;ll get the answer, the documents it came from, and the path through the graph that connects them.
          </p>
        </Card>
      )}
      {state.kind === "loading" && <AnswerSkeleton />}
      {state.kind === "done" && <AnswerPanel res={state.res} />}
      {state.kind === "error" && <ErrorState message={state.message} onRetry={() => run(last.current)} />}
      <EvalBadge data={overview.ev} />
    </>
  );
}

export default function AskPage() {
  return (
    <Suspense>
      <Ask />
    </Suspense>
  );
}
