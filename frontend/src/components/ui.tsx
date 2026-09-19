import type { ReactNode } from "react";

// Lucide-style 24px stroke icons, stroked with currentColor.
export function Icon({ d, className = "size-4" }: { d: ReactNode; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {d}
    </svg>
  );
}

export const ICON = {
  ask: <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12zM9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6M12 16.5v.01" />,
  alert: <path d="M12 3 22 20H2zM12 9v5M12 17v.01" />,
  sources: (
    <>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
    </>
  ),
  graph: (
    <>
      <circle cx="5" cy="6" r="2" />
      <circle cx="19" cy="6" r="2" />
      <circle cx="12" cy="18" r="2" />
      <path d="M7 6h10M6 8l5 8.5M18 8l-5 8.5" />
    </>
  ),
  shield: <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" />,
  check: <path d="M20 6 9 17l-5-5" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  upload: <path d="M12 16V4M7 9l5-5 5 5M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />,
  offline: <path d="M2 2l20 20M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5.2-2.8M19 13a10 10 0 0 0-2-1.5M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8A15 15 0 0 0 10.7 5M12 20h.01" />,
  chevron: <path d="m9 6 6 6-6 6" />,
};

export function Card({
  title,
  action,
  children,
  className = "",
  bodyClassName = "p-5",
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={`rounded-xl border border-zinc-200 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] dark:border-zinc-800 dark:bg-zinc-900 ${className}`}>
      {title && (
        <header className="flex min-h-12 items-center justify-between gap-3 border-b border-zinc-100 px-5 py-2.5 dark:border-zinc-800">
          <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
          {action}
        </header>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

const TONE = {
  neutral: "text-zinc-950 dark:text-zinc-50",
  good: "text-emerald-600 dark:text-emerald-400",
  bad: "text-red-600 dark:text-red-400",
};

export function Stat({ label, value, hint, tone = "neutral", icon }: { label: string; value: ReactNode; hint?: ReactNode; tone?: keyof typeof TONE; icon: ReactNode }) {
  return (
    <Card bodyClassName="flex flex-col gap-1.5 p-5">
      <div className="flex items-center justify-between text-[13px] text-zinc-500 dark:text-zinc-400">
        {label}
        <Icon d={icon} className="size-4 text-zinc-400 dark:text-zinc-500" />
      </div>
      <div className={`text-[28px] font-semibold leading-none tracking-tight tabular-nums ${TONE[tone]}`}>{value}</div>
      <div className="min-h-4 text-xs text-zinc-500 dark:text-zinc-400">{hint}</div>
    </Card>
  );
}

export function Pill({ children, tone = "zinc" }: { children: ReactNode; tone?: "zinc" | "green" | "red" | "amber" }) {
  const t = {
    zinc: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950/60 dark:text-emerald-300",
    red: "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-950/60 dark:text-red-300",
    amber: "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-950/60 dark:text-amber-300",
  }[tone];
  return <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-transparent ring-inset ${t}`}>{children}</span>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const offline = message.startsWith("Can't reach");
  return (
    <Card bodyClassName="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/60 dark:text-red-400">
        <Icon d={offline ? ICON.offline : ICON.alert} className="size-5" />
      </span>
      <div className="flex flex-col gap-1">
        <p className="font-medium">{offline ? "Backend unreachable" : "Request failed"}</p>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">{message}</p>
        {offline && (
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Start it with <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono dark:bg-zinc-800">cd backend && uv run uvicorn app.main:app --port 8000</code>, or set{" "}
            <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono dark:bg-zinc-800">NEXT_PUBLIC_USE_MOCK=1</code> in <code className="font-mono">.env.local</code>.
          </p>
        )}
      </div>
      <button type="button" onClick={onRetry} className="mt-1 h-9 rounded-lg bg-zinc-950 px-4 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-white dark:text-zinc-950 dark:hover:bg-zinc-200">
        Retry
      </button>
    </Card>
  );
}
