"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { alerts as fetchAlerts } from "@/lib/api";
import { IngestCard } from "@/components/IngestCard";
import { Card, ErrorState, Pill } from "@/components/ui";
import type { Alert } from "@/lib/types";

const refLink = (ref: string | null) =>
  ref && (
    <Link href={`/sources#${ref}`} className="font-mono underline decoration-dotted underline-offset-2 hover:decoration-solid">
      {ref}
    </Link>
  );

function AlertRow({ a }: { a: Alert }) {
  const red = a.kind === "contradiction";
  return (
    <article className={`flex flex-col gap-1.5 border-l-[3px] px-5 py-4 ${red ? "border-red-500" : "border-amber-400"}`}>
      <h3 className="text-[15px] font-semibold">
        {red ? (
          <>
            {refLink(a.new_ref)} contradicts {refLink(a.existing_ref)}
          </>
        ) : (
          <>
            {refLink(a.existing_ref)} is stale{a.new_ref && <> · superseded by {refLink(a.new_ref)}</>}
          </>
        )}
      </h3>
      {a.reason && <p className="text-sm leading-snug text-zinc-600 dark:text-zinc-300">{a.reason}</p>}
      <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-zinc-500 dark:text-zinc-400">
        {a.service && <Pill>{a.service}</Pill>}
        {a.people?.length ? <Pill>{a.people.join(", ")}</Pill> : null}
        {a.confidence != null && <Pill tone={red ? "red" : "amber"}>confidence {a.confidence.toFixed(2)}</Pill>}
        <span className="ml-auto font-mono">{a.created_at}</span>
      </div>
    </article>
  );
}

function AlertSection({ title, items, tone }: { title: string; items: Alert[]; tone: "red" | "amber" }) {
  return (
    <Card title={title} action={<Pill tone={items.length ? tone : "zinc"}>{items.length}</Pill>} bodyClassName="divide-y divide-zinc-100 dark:divide-zinc-800">
      {items.length ? (
        items.map((a) => <AlertRow key={a.id} a={a} />)
      ) : (
        <p className="px-5 py-6 text-sm text-zinc-500 dark:text-zinc-400">None.</p>
      )}
    </Card>
  );
}

export default function AlertsPage() {
  const [list, setList] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    fetchAlerts().then(
      (a) => {
        setError(null);
        setList(a);
      },
      (e: Error) => setError(e.message),
    );

  useEffect(() => {
    load();
  }, []);

  const contradictions = list?.filter((a) => a.kind === "contradiction") ?? [];
  const stale = list?.filter((a) => a.kind === "stale") ?? [];

  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="grid items-start gap-6 xl:grid-cols-3">
      <IngestCard
        title="Live ingest"
        description="Add a doc to the graph. It is checked against every active decision on the same service."
        onIngested={load}
        className="xl:sticky xl:top-20"
      />

      <div className="flex flex-col gap-6 xl:col-span-2">
        {!list ? (
          <Card bodyClassName="p-5">
            <p className="animate-pulse font-mono text-xs text-zinc-500 dark:text-zinc-400">loading alerts…</p>
          </Card>
        ) : (
          <>
            <AlertSection title="Contradictions" items={contradictions} tone="red" />
            <AlertSection title="Stale decisions" items={stale} tone="amber" />
          </>
        )}
      </div>
    </div>
  );
}
