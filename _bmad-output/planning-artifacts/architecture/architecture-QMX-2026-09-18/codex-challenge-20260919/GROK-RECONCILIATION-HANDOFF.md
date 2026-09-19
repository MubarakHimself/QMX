# Grok reconciliation handoff

## Resume point

Reconcile Stage-A candidate `qmx-workflows-arch-2026-09-18-a` against this independent Stage-B challenge. Do **not** treat either document set as ratified. Do not start Documentation Factory or coding during reconciliation.

Pinned inputs:

- docs: `b8b4d21a3d6ec33158254f1827912c8fc0c4dcc3`
- implementation: `270e992995c2378ca63cf6343254ef8140a8c97e`
- stale audit revision excluded from absence claims: `8510c032496bb870824ecc5c4f807e8a4e4f167e`
- input ZIP SHA-256: `4247e7e84eba458a2d73c696dd2783b0635a36379dd9e3144da87a6cba478b87`
- frozen independent baseline SHA-256: `1c2c865d1cef50076682a737472174fa307cf1fc8eb3663b122ed04ab6f39fd8`

## Required inputs to read

1. Candidate `ARCHITECTURE-SPINE.md`, `CONTRACTS.md`, `JOURNEYS.md`, `REQUIREMENTS-ADDENDUM.md`, `CONFLICT-REGISTER.md` and `reviews/` from the original challenge archive.
2. `INDEPENDENT-SCENARIO-BASELINE.md` first, preserving its Pass-I provenance.
3. `ARCHITECTURE-FINDINGS.md` and `COVERAGE-AND-GAPS.md`.
4. `SCENARIO-CATALOG.jsonl` plus `behavior/` for exact scenario IDs.
5. `TEST-AND-MUTATION-PLAN.md` and `EVIDENCE-MANIFEST.json` for evidence boundaries.

## Non-negotiable operator corrections

- QMF is one framework, not a set of competing frameworks.
- Book/BMS is the default, not the universal ceiling; no dummy Book/BMS records.
- Data/ML work need not be a bot or trading-wrapped.
- Sessions own context and grants; tabs do not.
- App-use cannot edit implementation or self-apply a change; it hands off to authoring and validation.
- Specialists remain available; do not collapse them into one global agent.
- Trading-floor PM means **Portfolio Manager**.
- mutmut is an optional test-strength principle: WSL/POSIX on Windows, disposable copy only, never `mutmut apply` on the shared worktree.
- BDD/Gherkin is specification, not an assertion that feature files execute.

## Reconciliation order

### Gate 1 — foundational scope decision

**AF-01: complete non-Book deployment.** The frozen requirement says at least one complete non-Book composition can be validated, simulated and deployed. AD-11 refuses live/node-paper without Book pending L36. Choose one explicit outcome:

1. retain the accepted requirement and define the alternative’s accounting, risk, command, admission, evidence and end-to-end journey; or
2. narrow/defer the requirement through an explicit operator/constitutional amendment with consequences recorded.

Do not call sensing/research alone a complete second trading system, and do not synthesize Book/BMS placeholders.

### Gate 2 — external-effect and command safety

Reconcile together:

- **AF-02** operation idempotency, logical invocation/attempt identity and unknown-outcome reconciliation;
- **AF-03** deployment command-owner epoch/fencing, residuals, unknown orders and predecessor restart;
- **AF-05** invocation binding to contribution version, installed instance and config revision;
- **AF-10** structured grants bound to version/instance/effect/parameters/account scope.

Required output: one compatible invocation/authority envelope and one fenced deployment transition, with explicit owner and state vocabulary. Avoid overlapping partial schemas.

### Gate 3 — durable workflow and recovery

Reconcile together:

- **AF-04** atomic predecessor completion/successor dispatch and crash recovery;
- **AF-07** JobHandle attempts, partial artifacts, cancel/complete winner and parent state vocabulary;
- **AF-12** join/mapping completion, late/missing/failed partitions and branch retry;
- **AF-13** cross-store checkpoint/restore/reference reconciliation.

Required output: transaction/outbox/replay boundaries, owner-specific storage, checkpoint manifest and failure journeys. Do not invent a second scheduler or central evidence database.

### Gate 4 — package, session and stream lifecycles

Reconcile:

- **AF-08** replay/live sequence, cutover, gaps, bounded backpressure and shared consumer leases;
- **AF-09** product-session CAS and reconnect without replayed intent;
- **AF-11** package installation/activation/migration/index/rollback/uninstall and verified secret stripping;
- **AF-14** change-request base identity, conflict/rebase, validation and application evidence;
- **AF-15** discovery-pin-invoke availability race.

Required output: explicit state machines or normative transition tables and corresponding journey updates.

### Gate 5 — identity and contract completeness

Reconcile:

- **AF-06** recipe-definition identity distinct from output-release fp1;
- **AF-16** finite `event`, provider-versus-venue fields and complete descriptor examples;
- **AF-17** view/shared-parameter/reconnect DTOs without UI authority;
- **AF-18** headless semantic parity while QMB remains the only operator CLI;
- **AF-19** complete data recipe temporal/unit/licensing/environment policies.

Required output: normative schemas or explicit references to their owner; representative payloads must not contradict the spine.

## Evidence classifications to preserve

| Claim | Status at `270e992` |
|---|---|
| QML Stage-0/mill/store | Existing, bounded test evidence |
| QMF data/risk ownership and QMB default doors | Existing package evidence |
| QMN closed venue selector | Existing, bounded conformance evidence |
| QMA durable Task Graph edges/successors | Proposed; current store is in-memory and edges are dropped |
| Full DAG validator | Proposed repair; current validator misses self-loop/long cycle |
| ContributionHit | Proposed additive amendment; current wire union has two classes |
| Product sessions and live owner dispatch | Proposed; runtime absent |
| QML→QMB→QMN journey | Unproven integration |
| Complete non-Book deployed alternative | Not supplied; candidate holds it pending L36 |

## Required reconciliation output

Return a concise decision ledger, not a competing replacement architecture. For every AF-01..AF-20 item record:

- `accept | accept-with-change | reject-with-evidence | defer-with-authority`;
- exact candidate AD/contract/journey sections changed or retained;
- parent law/owner affected;
- scenario IDs that prove the decision;
- implementation status (`existing | connect | amend | new | deferred`);
- test/evidence required before an implementation claim;
- any operator decision still required.

Then report whether the revised candidate is ready for a separate operator acceptance gate. Do not self-ratify it, do not fold it into canonical docs, and do not code.

## Compact routing

- Start with AF-01 because it changes the accepted scope.
- Treat AF-02/03/04/05/10/12/13 as the safety/recovery block.
- Use the 85 scenario IDs as reconciliation oracles; do not replace them with an arbitrary smaller count.
- Preserve Pass-I rows as independent requirements. Pass-II additions may be changed or rejected only with evidence.
- When a candidate statement and representative payload differ, reconcile the normative source explicitly rather than relying on prose priority by accident.
