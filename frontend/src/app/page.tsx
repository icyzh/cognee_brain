import type { ReactNode } from "react";
import { SHOWCASE_QUESTION, mockAsk } from "@/lib/mock";
import { ArchitectureDiagram } from "./architecture-diagram";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "./theme-toggle";

const REPO = "https://github.com/icyzh/cognee_brain";
const DOCS = `${REPO}/blob/main/docs/architecture.md`;

// Lucide-style 24px stroke icons, stroked with currentColor.
function Icon({ d, className = "size-5" }: { d: ReactNode; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {d}
    </svg>
  );
}

const DOC = <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5" />;

const SOURCES: { label: string; icon: ReactNode }[] = [
  { label: "ADRs & docs", icon: <>{DOC}<path d="M9 13h6M9 17h4" /></> },
  { label: "Tickets", icon: <path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4z" /> },
  { label: "Meeting notes", icon: <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" /> },
  {
    label: "Org chart",
    icon: (
      <>
        <circle cx="12" cy="5" r="2.5" />
        <circle cx="5" cy="19" r="2.5" />
        <circle cx="19" cy="19" r="2.5" />
        <path d="M12 7.5V12M5 16.5V12h14v4.5" />
      </>
    ),
  },
];

const FEATURES: { title: string; body: ReactNode; icon: ReactNode }[] = [
  {
    title: "Answers with sources",
    body: (
      <>
        Every answer comes with an <code className="font-mono text-[13px]">evidence[]</code> list that points to the
        exact ADR, ticket or meeting it used.
      </>
    ),
    icon: <>{DOC}<path d="m9 14 2 2 4-4" /></>,
  },
  {
    title: "A visible multi-hop path",
    body: "See how the answer was found, step by step: Service → Decision → Meeting → Person → Team.",
    icon: (
      <>
        <circle cx="5" cy="6" r="2" />
        <circle cx="19" cy="6" r="2" />
        <circle cx="12" cy="18" r="2" />
        <path d="M7 6h10M6 8l5 8.5M18 8l-5 8.5" />
      </>
    ),
  },
  {
    title: "Links the LLM can't make up",
    body: "Links like owns, decided_in and supersedes come from source metadata and canonical IDs, and ingestion checks that every one exists in the graph.",
    icon: (
      <>
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </>
    ),
  },
  {
    title: "Stale-decision warnings",
    body: "If an answer cites a decision that was later superseded, it says so, before anyone acts on outdated information.",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
  },
  {
    title: "Says so when it doesn't know",
    body: "A grounding guard answers only from what was retrieved. If nothing relevant turns up, it declines instead of guessing.",
    icon: <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" />,
  },
  {
    title: "Nothing heavy to host",
    body: "Cognee Cloud manages the graph, vectors and LLM over REST. You run one FastAPI app and one SQLite file.",
    icon: (
      <>
        <path d="M7 18a4.5 4.5 0 0 1-.5-9 6 6 0 0 1 11.3 1.5A4 4 0 0 1 17 18z" />
      </>
    ),
  },
];

const STEPS: { title: string; body: ReactNode }[] = [
  {
    title: "Ingest",
    body: (
      <>
        Load Markdown ADRs, JSON tickets, meeting notes and <code className="font-mono text-[13px]">team.json</code>. A
        content hash skips files that were already loaded.
      </>
    ),
  },
  {
    title: "Build",
    body: (
      <>
        Metadata becomes typed graph edges. Cognee&apos;s <code className="font-mono text-[13px]">cognify</code> adds
        entities, topics and the reasoning behind decisions, then connects them to the same IDs.
      </>
    ),
  },
  {
    title: "Answer",
    body: (
      <>
        <code className="font-mono text-[13px]">POST /ask</code> runs a{" "}
        <code className="font-mono text-[13px]">GRAPH_COMPLETION</code> search, checks that the answer is grounded and
        flags superseded decisions. It returns the answer, its evidence and the path.
      </>
    ),
  },
];

function Eyebrow({ children }: { children: ReactNode }) {
  return <span className="font-mono text-[13px] text-blue-700 dark:text-blue-400">{children}</span>;
}

function AnswerMock() {
  const { answer, evidence, path, warnings } = mockAsk;
  const nodes = [path[0].from, ...path.map((e) => e.to)];
  return (
    <div
      id="ask"
      className="mt-14 w-full max-w-[1200px] scroll-mt-24 overflow-hidden rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 text-left shadow-[0_1px_2px_rgba(0,0,0,0.04),0_24px_64px_-32px_rgba(10,10,11,0.18)]"
    >
      <div className="flex h-12 items-center gap-6 border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-5 text-[13px] text-zinc-500 dark:text-zinc-400">
        <span className="font-medium text-zinc-950 dark:text-zinc-50">Ask</span>
        <span>Graph explorer</span>
        <span>Sources</span>
      </div>
      <div className="grid lg:grid-cols-3">
        <div className="flex flex-col gap-5 p-7 lg:col-span-2 lg:border-r lg:border-zinc-100">
          <form action="/ask" className="flex gap-2">
            <label htmlFor="q" className="sr-only">
              Question
            </label>
            <input
              id="q"
              name="q"
              defaultValue={SHOWCASE_QUESTION}
              className="h-11 min-w-0 flex-1 rounded-[10px] border border-zinc-200 dark:border-zinc-800 px-3.5 text-[15px] outline-none focus:border-zinc-400 dark:focus:border-zinc-600"
            />
            <button type="submit" className="h-11 rounded-[10px] bg-zinc-950 dark:bg-white px-4 text-sm font-medium text-white dark:text-zinc-950">
              Ask
            </button>
          </form>
          <p className="text-[17px] leading-relaxed">{answer}</p>
          {warnings.map((w) => (
            <div
              key={w.node}
              className="flex items-center gap-2 self-start rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 px-2.5 py-1.5 text-[13px] text-red-700 dark:text-red-300"
            >
              <Icon className="size-3.5" d={<path d="M12 3 22 20H2zM12 9v5M12 17v.01" />} />
              {w.message}
            </div>
          ))}
          <div className="flex flex-col gap-2.5">
            <div className="font-mono text-xs text-zinc-500 dark:text-zinc-400">EVIDENCE</div>
            <div className="grid gap-2.5 sm:grid-cols-3">
              {evidence.map((e) => (
                <div key={e.ref} className="flex flex-col gap-1.5 rounded-[10px] border border-zinc-100 dark:border-zinc-800 px-3.5 py-3">
                  <span className="font-mono text-xs text-blue-700 dark:text-blue-400">{e.path}</span>
                  <span className="text-[13px] leading-snug text-zinc-700 dark:text-zinc-300">“{e.snippet}”</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-3.5 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-7 lg:border-t-0">
          <div className="font-mono text-xs text-zinc-500 dark:text-zinc-400">PATH · {path.length} HOPS</div>
          <ol className="flex flex-col font-mono text-[13px]">
            {nodes.map((n, i) => {
              const last = i === nodes.length - 1;
              return (
                <li key={n.id} className="flex flex-col">
                  <div
                    className={`flex justify-between rounded-lg border bg-white dark:bg-zinc-950 px-3 py-2.5 ${
                      last ? "border-blue-700 text-blue-700 dark:border-blue-400 dark:text-blue-400" : "border-zinc-200 dark:border-zinc-800"
                    }`}
                  >
                    <span>{n.id}</span>
                    <span className={last ? "" : "text-zinc-400 dark:text-zinc-500"}>{n.type.toLowerCase()}</span>
                  </div>
                  {!last && (
                    <div className="ml-4 border-l border-zinc-300 dark:border-zinc-700 py-1 pl-4 text-[11px] text-zinc-500 dark:text-zinc-400">
                      {path[i].rel}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-10 border-b border-zinc-100 dark:border-zinc-800 bg-white/85 dark:bg-zinc-950/85 backdrop-blur">
        <div className="mx-auto flex h-[72px] max-w-[1200px] items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-12">
            <a href="#top" aria-label="Permafrost home" className="flex items-center gap-2.5">
              <Logo />
              <span className="text-[19px] font-semibold tracking-tight">Permafrost</span>
            </a>
            <nav aria-label="Primary" className="hidden gap-8 text-sm text-zinc-600 dark:text-zinc-400 md:flex">
              <a href="#features" className="hover:text-zinc-950 dark:hover:text-zinc-50">Features</a>
              <a href="#architecture" className="hover:text-zinc-950 dark:hover:text-zinc-50">Architecture</a>
              <a href="#how" className="hover:text-zinc-950 dark:hover:text-zinc-50">How it works</a>
              <a href={DOCS} className="hover:text-zinc-950 dark:hover:text-zinc-50">Docs</a>
            </nav>
          </div>
          <div className="flex items-center gap-2.5">
            <ThemeToggle />
            <a
              href={REPO}
              className="hidden h-9 items-center gap-2 rounded-lg border border-zinc-200 dark:border-zinc-800 px-3.5 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900 sm:flex"
            >
              <Icon
                className="size-4"
                d={<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21" />}
              />
              GitHub
            </a>
            <a
              href="/ask"
              className="flex h-9 items-center rounded-lg bg-zinc-950 dark:bg-white px-4 text-sm font-medium text-white dark:text-zinc-950 hover:bg-zinc-800 dark:hover:bg-zinc-200"
            >
              Get started
            </a>
          </div>
        </div>
      </header>

      <main>
        <section id="top" className="flex flex-col items-center gap-7 px-4 pt-20 text-center sm:px-6 sm:pt-28">
          <a
            href="#architecture"
            className="flex items-center gap-2 rounded-full border border-zinc-200 dark:border-zinc-800 py-1.5 pl-3.5 pr-3.5 text-[13px] text-zinc-600 dark:text-zinc-400 hover:border-zinc-300 dark:hover:border-zinc-700 sm:pr-1.5"
          >
            Company memory that never melts
            <span className="hidden rounded-full bg-zinc-100 dark:bg-zinc-800 px-2.5 py-0.5 font-medium text-zinc-950 dark:text-zinc-50 sm:inline">Read the design →</span>
          </a>
          <h1 className="max-w-[960px] text-5xl font-semibold leading-[1.04] tracking-[-0.045em] sm:text-7xl">
            Ask why.
            <br />
            <span className="text-zinc-500 dark:text-zinc-400">Get the answer, the evidence and the path.</span>
          </h1>
          <p className="max-w-[640px] text-lg leading-relaxed text-zinc-600 dark:text-zinc-400 sm:text-[19px]">
            Permafrost connects your docs, tickets, meeting notes and org chart into one knowledge graph, then answers
            questions with cited sources and the chain of links behind them.
          </p>
          <div className="flex flex-wrap justify-center gap-3 pt-1">
            <a
              href="/ask"
              className="flex h-12 items-center rounded-[10px] bg-zinc-950 dark:bg-white px-5 text-[15px] font-medium text-white dark:text-zinc-950 hover:bg-zinc-800 dark:hover:bg-zinc-200"
            >
              Get started
            </a>
            <a
              href="#architecture"
              className="flex h-12 items-center rounded-[10px] border border-zinc-200 dark:border-zinc-800 px-5 text-[15px] font-medium hover:bg-zinc-50 dark:hover:bg-zinc-900"
            >
              View architecture
            </a>
          </div>
          <AnswerMock />
        </section>

        <section aria-label="Sources" className="flex flex-col items-center gap-7 px-4 py-20 sm:px-6">
          <span className="text-sm text-zinc-500 dark:text-zinc-400">One graph from four kinds of company knowledge</span>
          <ul className="flex flex-wrap justify-center gap-x-16 gap-y-4 text-[17px] font-medium text-zinc-600 dark:text-zinc-400">
            {SOURCES.map((s) => (
              <li key={s.label} className="flex items-center gap-2.5">
                <Icon d={s.icon} />
                {s.label}
              </li>
            ))}
          </ul>
        </section>

        <section id="features" className="scroll-mt-16 border-t border-zinc-100 dark:border-zinc-800 px-4 py-28 sm:px-6">
          <div className="mx-auto flex max-w-[1200px] flex-col gap-14">
            <div className="flex max-w-[720px] flex-col gap-4">
              <Eyebrow>FEATURES</Eyebrow>
              <h2 className="text-4xl font-semibold leading-[1.1] tracking-[-0.04em] sm:text-5xl">
                Structure from metadata.
                <br />
                <span className="text-zinc-500 dark:text-zinc-400">Meaning from the LLM.</span>
              </h2>
              <p className="text-[17px] leading-relaxed text-zinc-600 dark:text-zinc-400">
                Keyword search finds the pieces. Chatbots give answers with no sources. Permafrost stores the links
                between documents as graph edges, so every answer shows where it came from.
              </p>
            </div>
            <div className="grid gap-px overflow-hidden rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-200 dark:bg-zinc-800 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((f) => (
                <div key={f.title} className="flex flex-col gap-3 bg-white dark:bg-zinc-950 p-9">
                  <span className="text-blue-700 dark:text-blue-400">
                    <Icon d={f.icon} className="size-[22px]" />
                  </span>
                  <h3 className="mt-2 text-lg font-semibold tracking-tight">{f.title}</h3>
                  <p className="text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-400">{f.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="architecture" className="scroll-mt-16 border-y border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-4 py-28 sm:px-6">
          <div className="mx-auto flex max-w-[1200px] flex-col gap-12">
            <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end lg:gap-20">
              <div className="flex flex-col gap-4">
                <Eyebrow>ARCHITECTURE</Eyebrow>
                <h2 className="max-w-[680px] text-4xl font-semibold leading-[1.1] tracking-[-0.04em] sm:text-5xl">
                  From raw files to a grounded answer.
                </h2>
              </div>
              <p className="max-w-[420px] leading-relaxed text-zinc-600 dark:text-zinc-400">
                The Next.js frontend talks to FastAPI over REST. The backend calls Cognee Cloud, which manages the
                graph, vectors and LLM. Question history lives in one local SQLite file.
              </p>
            </div>
            <figure className="flex flex-col gap-4">
              <div className="rounded-2xl border border-zinc-200 bg-white p-2 dark:border-zinc-800 dark:bg-[#121212] sm:p-4">
                <ArchitectureDiagram />
              </div>
              <figcaption className="flex flex-col justify-between gap-1 font-mono text-xs text-zinc-500 dark:text-zinc-400 md:flex-row">
                <span>docs/architecture.excalidraw · click to pan and zoom</span>
                <span>Company data → Hybrid ingest → Cognee graph + vectors → POST /ask → Answer + evidence + path</span>
              </figcaption>
            </figure>
          </div>
        </section>

        <section id="how" className="scroll-mt-16 px-4 py-28 sm:px-6">
          <div className="mx-auto flex max-w-[1200px] flex-col gap-12">
            <div className="flex flex-col gap-4">
              <Eyebrow>HOW IT WORKS</Eyebrow>
              <h2 className="text-4xl font-semibold leading-[1.1] tracking-[-0.04em] sm:text-5xl">
                Three steps. <span className="text-zinc-500 dark:text-zinc-400">No database server.</span>
              </h2>
            </div>
            <ol className="grid gap-10 md:grid-cols-3">
              {STEPS.map((s, i) => (
                <li key={s.title} className="flex flex-col gap-3 border-t border-zinc-950 dark:border-zinc-100 pt-6">
                  <span className="font-mono text-[13px] text-zinc-500 dark:text-zinc-400">0{i + 1}</span>
                  <span className="text-[22px] font-semibold tracking-tight">{s.title}</span>
                  <p className="text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-400">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="px-4 pb-10 sm:px-6">
          <div className="mx-auto flex max-w-[1200px] flex-col gap-10">
            <div className="flex flex-col justify-between gap-8 rounded-[20px] bg-zinc-950 p-10 text-white dark:bg-zinc-900 dark:ring-1 dark:ring-zinc-800 sm:p-[72px] lg:flex-row lg:items-center">
              <div className="flex flex-col gap-3">
                <h2 className="text-3xl font-semibold leading-[1.1] tracking-[-0.04em] sm:text-[44px]">
                  Stop searching. Start asking why.
                </h2>
                <p className="text-zinc-400">Run it locally in minutes. No Docker, no database server.</p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-3">
                <a
                  href={`${REPO}#run-locally`}
                  className="flex h-12 items-center rounded-[10px] bg-white px-5 text-[15px] font-medium text-zinc-950 hover:bg-zinc-200"
                >
                  Get started
                </a>
                <a
                  href={DOCS}
                  className="flex h-12 items-center rounded-[10px] border border-zinc-700 px-5 text-[15px] font-medium hover:bg-zinc-900 dark:hover:bg-zinc-800"
                >
                  Read the docs
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto mt-auto flex w-full max-w-[1200px] flex-col justify-between gap-2 border-t border-zinc-100 dark:border-zinc-800 px-4 py-6 text-[13px] text-zinc-500 dark:text-zinc-400 sm:flex-row sm:px-6">
        <span>© Permafrost · built on Cognee</span>
        <span className="font-mono text-xs">Next.js · FastAPI · Cognee Cloud · SQLite</span>
      </footer>
    </div>
  );
}
