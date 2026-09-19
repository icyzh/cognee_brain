"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { ICON, Icon } from "@/components/ui";
import { ALERTS_CHANGED, BASE, USE_MOCK, alerts } from "@/lib/api";
import { ThemeToggle } from "../theme-toggle";

const NAV = [
  { href: "/ask", label: "Ask", icon: ICON.ask, sub: "Answers with evidence and the path behind them" },
  { href: "/alerts", label: "Alerts", icon: ICON.alert, sub: "Contradictions and stale decisions, checked on every ingest" },
  { href: "/sources", label: "Data", icon: ICON.sources, sub: "Add company docs and see every file in the knowledge graph" },
  { href: "/graph", label: "Graph", icon: ICON.graph, sub: "Entities and links in Cognee" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const page = NAV.find((n) => n.href === pathname);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    const refresh = () => alerts().then((a) => setAlertCount(a.length), () => {});
    refresh();
    window.addEventListener(ALERTS_CHANGED, refresh);
    return () => window.removeEventListener(ALERTS_CHANGED, refresh);
  }, []);

  const links = (vertical: boolean) =>
    NAV.map((n) => (
      <Link
        key={n.href}
        href={n.href}
        aria-current={pathname === n.href ? "page" : undefined}
        className={`flex shrink-0 items-center gap-2.5 rounded-lg px-2.5 text-sm text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950 aria-[current=page]:bg-zinc-100 aria-[current=page]:font-medium aria-[current=page]:text-zinc-950 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50 dark:aria-[current=page]:bg-zinc-800 dark:aria-[current=page]:text-zinc-50 ${
          vertical ? "h-9" : "h-8"
        }`}
      >
        <Icon d={n.icon} />
        {n.label}
        {n.href === "/alerts" && alertCount > 0 && (
          <span className="ml-auto rounded-full bg-red-600 px-1.5 text-[11px] font-medium leading-[18px] text-white" aria-label={`${alertCount} open alerts`}>
            {alertCount}
          </span>
        )}
      </Link>
    ));

  return (
    <div className="flex min-h-screen flex-1 bg-zinc-50 dark:bg-zinc-950">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-zinc-200 bg-white lg:flex dark:border-zinc-800 dark:bg-zinc-900">
        <Link href="/" className="flex h-14 items-center gap-2.5 border-b border-zinc-100 px-5 dark:border-zinc-800">
          <Logo className="size-6" />
          <span className="font-semibold tracking-tight">Permafrost</span>
        </Link>
        <nav aria-label="App" className="flex flex-col gap-0.5 p-3">
          <span className="px-2.5 pb-1.5 pt-2 text-[11px] font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500">Workspace</span>
          {links(true)}
        </nav>
        <div className="mt-auto flex items-center justify-between gap-2 border-t border-zinc-100 p-3 dark:border-zinc-800">
          <div className="flex min-w-0 flex-col px-1.5">
            <span className="flex items-center gap-1.5 text-xs font-medium">
              <span className={`size-1.5 rounded-full ${USE_MOCK ? "bg-amber-500" : "bg-emerald-500"}`} />
              {USE_MOCK ? "Mock data" : "Live API"}
            </span>
            <span className="truncate font-mono text-[11px] text-zinc-500 dark:text-zinc-400">{USE_MOCK ? "NEXT_PUBLIC_USE_MOCK=1" : BASE.replace(/^https?:\/\//, "")}</span>
          </div>
          <ThemeToggle />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white/85 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/85">
          <div className="flex h-14 items-center justify-between gap-4 px-4 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <Link href="/" aria-label="Permafrost home" className="lg:hidden">
                <Logo className="size-6" />
              </Link>
              <div className="flex min-w-0 flex-col">
                <h1 className="text-[15px] font-semibold leading-tight tracking-tight">{page?.label}</h1>
                <p className="hidden truncate text-xs text-zinc-500 sm:block dark:text-zinc-400">{page?.sub}</p>
              </div>
            </div>
            <div className="lg:hidden">
              <ThemeToggle />
            </div>
          </div>
          <nav aria-label="App" className="flex gap-1 overflow-x-auto border-t border-zinc-100 px-3 py-1.5 lg:hidden dark:border-zinc-800">
            {links(false)}
          </nav>
        </header>
        <main className="flex-1 px-4 py-6 lg:px-8">
          <div className="mx-auto flex max-w-[1400px] flex-col gap-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
