# Phase 3: Frontend Ask experience

> **Goal:** the answer, evidence and path are *visible* in the browser in one glance. The UI is where judges see grounding and multi-hop.
> **Tracks:** Frontend · **Est:** 2 h · **Depends on:** P0 (types + mock), then P2 (live API) · **Unblocks:** P4
> ← [Phase 2](phase-2-query-pipeline.md) · next → [Phase 4](phase-4-differentiators.md)

---

## Structure (`frontend/src/`)
```
lib/
  types.ts        # AskResponse, Evidence, PathEdge, Warning, Alert (from the P2 contract)
  api.ts          # ask(), feedback(), alerts(), ingestFile(), evalLatest(); base URL from NEXT_PUBLIC_API_URL
  mock.ts         # showcase + refusal responses (used when NEXT_PUBLIC_USE_MOCK=1)
app/
  layout.tsx      # top nav: Ask · Alerts · Sources (· Graph if stretch)
  page.tsx        # Ask
  alerts/page.tsx # built in P4
  sources/page.tsx
components/
  AskBox.tsx
  AnswerPanel.tsx
  WarningBanner.tsx   # stale (amber) / contradiction (red)
  EvidenceCard.tsx
  HopPath.tsx
  FeedbackBar.tsx
  EvalBadge.tsx       # wired in P4
```

## Tasks

### Wiring
- [x] `lib/types.ts` mirrors the P2 contract exactly
- [x] `lib/api.ts`: `fetch` wrappers with a timeout (25 s) and typed errors; mock switch via env
- [x] `frontend/.env.local.example`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

### Ask page (`/`)
- [x] `AskBox`: input + button, Enter to submit, **3 suggested-question chips** (showcase, refusal, one more multi-hop) that also serve as demo shortcuts
- [x] Loading state: skeleton + a "retrieving from graph…" line (queries take 10–13 s against Cognee Cloud (P2 measured))
- [x] `AnswerPanel`: answer text; if `grounded=false`, a neutral "Not in company knowledge" state (a feature, not an error)
- [x] `WarningBanner`: one per warning; amber = stale, red = contradiction
- [x] `EvidenceCard`: source-type chip (ADR / Ticket / Meeting), ref, snippet, file path; the colour per source matches the diagram
- [x] `HopPath`: horizontal chain of pills `svc-payments → ADR-007 → MTG-0312 → priya → platform` with the rel label on each arrow and a hop count. Pill colour by node type. Wraps on narrow screens.
- [x] `FeedbackBar`: 👍/👎 → `POST /feedback`
- [x] Error state: backend down or timeout → message + retry button

### Sources page (`/sources`)
- [x] Table: ref, type, path, ingested_at, hash (short)

### Styling
- [x] Tailwind 4 only; no component library needed
- [x] Node-type colours consistent with `architecture.png` (Service blue, Decision amber, Person/Team green, stale red)

### Stretch: graph explorer (`/graph`)
- [x] Only if P4 is done early. Consider `react-force-graph-2d` (1 dependency) over `GET /graph?focus=&depth=2`, and highlight the last answer's path.

---

## Acceptance criteria
- With `NEXT_PUBLIC_USE_MOCK=1`: the full Ask page renders the showcase answer (works before the backend is ready)
- Against the live backend: the showcase chip → answer, 3 evidence cards, 4-hop path and a stale banner in ≤ 15 s (P2 measured 10–13 s; the cached fallback covers slower runs)
- The refusal chip → the "Not in company knowledge" state
- `npm run lint` and `npm run build` pass

## Exit gate
End-to-end browser demo of the showcase + refusal against the live API.

## If behind
Drop `/sources`. `HopPath` can be plain text with arrows. Keep the evidence cards; they are the grounding proof.
