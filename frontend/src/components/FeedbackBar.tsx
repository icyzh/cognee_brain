"use client";

import { useState } from "react";
import { feedback } from "@/lib/api";

export function FeedbackBar({ qaId }: { qaId: number }) {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function send(helpful: boolean) {
    setState("sending");
    try {
      await feedback(qaId, helpful);
      setState("sent");
    } catch {
      setState("error");
    }
  }

  if (state === "sent") return <p className="text-[13px] text-zinc-500 dark:text-zinc-400">Thanks for the feedback.</p>;

  const btn =
    "flex size-8 items-center justify-center rounded-lg border border-zinc-200 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-800 dark:hover:bg-zinc-900";
  return (
    <div className="flex items-center gap-2 text-[13px] text-zinc-500 dark:text-zinc-400">
      <span>Was this helpful?</span>
      <button type="button" className={btn} disabled={state === "sending"} onClick={() => send(true)} aria-label="Helpful">
        👍
      </button>
      <button type="button" className={btn} disabled={state === "sending"} onClick={() => send(false)} aria-label="Not helpful">
        👎
      </button>
      {state === "error" && <span className="text-red-600 dark:text-red-400">Couldn&apos;t send, try again.</span>}
    </div>
  );
}
