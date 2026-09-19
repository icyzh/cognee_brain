import type { AskResponse } from "@/lib/types";
import { EvidenceCard } from "./EvidenceCard";
import { FeedbackBar } from "./FeedbackBar";
import { HopPath } from "./HopPath";
import { Card, ICON, Icon, Pill } from "./ui";
import { WarningBanner } from "./WarningBanner";

const seconds = (ms: number) => <span className="font-mono text-xs text-zinc-500 dark:text-zinc-400">{(ms / 1000).toFixed(1)} s</span>;

export function AnswerPanel({ res }: { res: AskResponse }) {
  if (!res.grounded) {
    return (
      <Card
        title="Answer"
        action={
          <div className="flex items-center gap-3">
            {seconds(res.latency_ms)}
            <Pill>Not grounded</Pill>
          </div>
        }
      >
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <span className="flex size-10 items-center justify-center rounded-full bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
            <Icon d={ICON.shield} className="size-5" />
          </span>
          <div className="flex flex-col gap-1">
            <p className="font-medium">Not in company knowledge</p>
            <p className="max-w-md text-sm text-zinc-500 dark:text-zinc-400">
              {res.answer} Nothing relevant was retrieved, so Permafrost declines instead of guessing.
            </p>
          </div>
          <FeedbackBar key={res.qa_id} qaId={res.qa_id} />
        </div>
      </Card>
    );
  }

  return (
    <div className="grid items-start gap-6 xl:grid-cols-3">
      <div className="flex flex-col gap-6 xl:col-span-2">
        <Card
          title="Answer"
          action={
            <div className="flex items-center gap-3">
              {seconds(res.latency_ms)}
              <Pill tone="green">
                <Icon d={ICON.check} className="size-3" />
                Grounded
              </Pill>
            </div>
          }
          bodyClassName="flex flex-col gap-4 p-5"
        >
          <p className="text-[17px] leading-relaxed">{res.answer}</p>
          {res.warnings.map((w) => (
            <WarningBanner key={`${w.kind}-${w.node}`} w={w} />
          ))}
          <div className="border-t border-zinc-100 pt-4 dark:border-zinc-800">
            <FeedbackBar key={res.qa_id} qaId={res.qa_id} />
          </div>
        </Card>
        {res.evidence.length > 0 && (
          <Card title="Evidence" action={<Pill>{res.evidence.length} sources</Pill>}>
            <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
              {res.evidence.map((e) => (
                <EvidenceCard key={e.ref} e={e} />
              ))}
            </div>
          </Card>
        )}
      </div>
      {res.path.length > 0 && (
        <Card title="Reasoning path" action={<Pill>{res.path.length} {res.path.length === 1 ? "hop" : "hops"}</Pill>}>
          <HopPath path={res.path} />
        </Card>
      )}
    </div>
  );
}

export function AnswerSkeleton() {
  const bar = "animate-pulse rounded-md bg-zinc-100 dark:bg-zinc-800";
  return (
    <div className="grid items-start gap-6 xl:grid-cols-3" aria-busy="true">
      <Card title="Answer" action={<span className="animate-pulse font-mono text-xs text-zinc-500 dark:text-zinc-400">retrieving from graph…</span>} className="xl:col-span-2" bodyClassName="flex flex-col gap-3 p-5">
        <div className={`h-4 w-full ${bar}`} />
        <div className={`h-4 w-4/5 ${bar}`} />
        <div className={`h-9 w-full ${bar}`} />
        <div className="grid gap-3 pt-2 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className={`h-24 ${bar}`} />
          ))}
        </div>
      </Card>
      <Card title="Reasoning path" bodyClassName="flex flex-col gap-3 p-5">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className={`h-9 ${bar}`} />
        ))}
      </Card>
    </div>
  );
}
