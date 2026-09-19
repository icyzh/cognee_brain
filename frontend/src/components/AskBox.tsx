"use client";

import { useState } from "react";
import { SUGGESTED } from "@/lib/mock";
import { Card, ICON, Icon } from "./ui";

export function AskBox({ initial, busy, onAsk }: { initial: string; busy: boolean; onAsk: (q: string) => void }) {
  const [q, setQ] = useState(initial);

  function submit(question: string) {
    setQ(question);
    if (question.trim()) onAsk(question.trim());
  }

  return (
    <Card bodyClassName="flex flex-col gap-3 p-4">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submit(q);
        }}
      >
        <label htmlFor="q" className="sr-only">
          Question
        </label>
        <div className="relative min-w-0 flex-1">
          <Icon d={ICON.search} className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
          <input
            id="q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ask why… e.g. why is payments on Postgres?"
            autoFocus
            className="h-11 w-full rounded-lg border border-zinc-200 bg-white pl-10 pr-3.5 text-[15px] outline-none transition focus:border-zinc-400 focus:ring-4 focus:ring-zinc-100 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-500 dark:focus:ring-zinc-800"
          />
        </div>
        <button
          type="submit"
          disabled={busy || !q.trim()}
          className="h-11 rounded-lg bg-zinc-950 px-5 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-white dark:text-zinc-950 dark:hover:bg-zinc-200"
        >
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-zinc-500 dark:text-zinc-400">Try</span>
        {SUGGESTED.map((s) => (
          <button
            key={s}
            type="button"
            disabled={busy}
            onClick={() => submit(s)}
            className="rounded-md border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-left text-xs text-zinc-600 hover:border-zinc-300 hover:text-zinc-950 disabled:opacity-50 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400 dark:hover:border-zinc-700 dark:hover:text-zinc-50"
          >
            {s}
          </button>
        ))}
      </div>
    </Card>
  );
}
