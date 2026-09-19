# Snow Pay: story bible

The fictional company behind the seed data. Every file under `data/seed/` must agree with this page. Canonical IDs are the only way sources refer to people, teams, services, decisions, meetings and tickets (display names and declared aliases are allowed in prose).

In-world "today" is **2026-04-02**.

## Teams and services

| Team (id) | Lead | Owns |
|---|---|---|
| Platform (`platform`) | `priya` | `svc-payments`, `svc-ledger`, `svc-auth` |
| Payments Product (`payments-product`) | `nora` | `svc-notify` |
| Data (`data`) | `lena` | `svc-reports` |

| Service | What it does |
|---|---|
| `svc-payments` | Public payments API: authorise, capture, refund |
| `svc-ledger` | Double-entry ledger behind every payment |
| `svc-auth` | API keys, sessions, tokens |
| `svc-notify` | Customer notifications (receipts, alerts) |
| `svc-reports` | Merchant reports and finance exports |

## People

| id | Name | Aliases | Team | Role |
|---|---|---|---|---|
| `priya` | Priya Sharma | Priya, P. Sharma | platform | Platform lead; owns the ledger decision |
| `marco` | Marco Rossi | Marco | platform | Backend engineer; wrote the original MongoDB ADR |
| `sam` | Samuel Okafor | Sam, Sam O. | platform | Security / auth engineer |
| `nora` | Nora Lindqvist | Nora | payments-product | Payments Product lead |
| `arjun` | Arjun Mehta | Arjun | payments-product | Product engineer; pushes for "scale" |
| `mei` | Mei Chen | Mei | payments-product | Notifications engineer |
| `lena` | Lena Fischer | Lena | data | Data lead |
| `diego` | Diego Alvarez | Diego | data | Data engineer |

## Decisions (ADRs)

| ADR | Title | Status | Date | Decided in | Owner | Affects | Supersedes |
|---|---|---|---|---|---|---|---|
| ADR-001 | JWT access tokens with 15-min expiry for svc-auth | accepted | 2026-01-15 | MTG-0115 | `sam` | svc-auth | |
| ADR-002 | Queue payment events through SQS | accepted | 2026-01-29 | MTG-0129 | `mei` | svc-notify, svc-payments | |
| ADR-003 | Use MongoDB for the payments ledger | **superseded** | 2025-10-02 | (predates notes) | `marco` | svc-payments, svc-ledger | |
| ADR-004 | Reports read from a nightly Postgres read replica | accepted | 2026-02-05 | MTG-0205 | `lena` | svc-reports, svc-ledger | |
| ADR-005 | Email-only customer notifications via SES | **superseded** | 2026-01-29 | MTG-0129 | `mei` | svc-notify | |
| ADR-006 | Rate-limit the public API at the gateway | accepted | 2026-02-19 | MTG-0219 | `sam` | svc-auth, svc-payments | |
| ADR-007 | Use Postgres for the payments ledger | accepted | 2026-03-12 | MTG-0312 | `priya` | svc-payments, svc-ledger | ADR-003 |
| ADR-008 | Idempotency keys on all payment writes | accepted | 2026-03-05 | MTG-0305 | `marco` | svc-payments | |
| ADR-009 | Multi-channel notifications (email, SMS, push) | accepted | 2026-03-20 | MTG-0320 | `nora` | svc-notify | ADR-005 |

Why ADR-007 happened: a double-refund incident (TCK-131, Feb 2026) showed MongoDB couldn't give multi-document ACID guarantees across ledger entries at our write pattern. Postgres gives serializable transactions. Marco (author of ADR-003) agreed.

## Meetings

| id | Date | Title | Attendees | Decisions |
|---|---|---|---|---|
| MTG-0115 | 2026-01-15 | Auth design review | sam, priya, marco | ADR-001 |
| MTG-0129 | 2026-01-29 | Notifications kickoff | mei, nora, arjun, priya | ADR-002, ADR-005 |
| MTG-0205 | 2026-02-05 | Reporting architecture | lena, diego, priya | ADR-004 |
| MTG-0219 | 2026-02-19 | API abuse response | sam, priya, arjun | ADR-006 |
| MTG-0226 | 2026-02-26 | Q2 offsite planning (noise) | nora, lena, priya | none |
| MTG-0305 | 2026-03-05 | Payments reliability | marco, priya, arjun | ADR-008 |
| MTG-0312 | 2026-03-12 | Architecture sync: ledger storage | priya, marco, arjun | ADR-007 |
| MTG-0320 | 2026-03-20 | Notifications v2 | nora, mei, arjun | ADR-009 |

## Tickets (highlights)

| id | Title | Assignee | Service | Refs | Status |
|---|---|---|---|---|---|
| TCK-118 | Nightly merchant report job times out | diego | svc-reports | ADR-004 | open |
| TCK-131 | Double refund on concurrent captures (incident) | marco | svc-ledger | ADR-003 | done |
| TCK-142 | Migrate ledger tables to Postgres | priya | svc-payments | ADR-007 | in_progress |
| TCK-147 | Add SMS provider to notify | mei | svc-notify | ADR-009 | open |

## Showcase chain (the demo path)

`svc-payments` ← affects ← `ADR-007` → decided_in → `MTG-0312` → attended_by → `priya` → member_of → `platform`; plus `TCK-142` → references → `ADR-007`, and `ADR-007` → supersedes → `ADR-003`.

## Eval answers (multi-hop)

| Question | Answer | Hops |
|---|---|---|
| Why is payments on Postgres, and who should I talk to about it now? | ADR-007 (ACID after TCK-131's double refund), decided in MTG-0312; Priya, Platform | svc-payments → ADR-007 → MTG-0312 → priya → platform |
| Who owns the service affected by TCK-118? | svc-reports → Data team, lead Lena | TCK-118 → svc-reports → data |
| Who decided how we send customer notifications, and which team is that? | ADR-009 (supersedes ADR-005), MTG-0320, Nora, Payments Product | svc-notify → ADR-009 → nora → payments-product |
| Who should I ask about auth token expiry? | ADR-001, Sam, Platform | svc-auth → ADR-001 → sam → platform |
| Do we still send notifications by email only? | No: ADR-005 was superseded by ADR-009 | stale |
| What's our mobile release cadence? | Not in company knowledge: refuse (nothing in the corpus; note: Kafka *is* mentioned, as ADR-002's rejected alternative, so it can't be the refusal question) | none |

## Live-demo file (not pre-ingested)

`data/live/MTG-0402.md` (2026-04-02, attendees arjun, nora, mei): Arjun proposes moving `svc-payments` storage to DynamoDB "for scale". Nobody mentions ACID or ADR-007. It contradicts active ADR-007.
