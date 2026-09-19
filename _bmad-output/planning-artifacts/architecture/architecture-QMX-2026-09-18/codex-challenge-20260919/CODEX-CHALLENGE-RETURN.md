# Codex Stage B challenge return

## Verdict

Candidate `qmx-workflows-arch-2026-09-18-a` is **directionally coherent but not architecture-complete and not ratified**.

The candidate gets several fundamentals right: no sixth product or scheduler, QMF remains one framework, Board layout is not execution state, specialists remain, product sessions—not tabs—own context, app-use cannot directly edit implementation, UI adapters are non-authoritative, Book/BMS remains the protected default rather than a source of dummy records, and mutation testing is optional evidence on disposable WSL/POSIX copies.

The reviewed design still permits incompatible or unsafe implementations at its most important failure seams. The top blockers are:

1. The accepted complete non-Book deployed alternative is withheld pending L36; sensing/research is not the required second complete path.
2. External-effect retry lacks a normative idempotency/reconciliation envelope.
3. Deployment handover lacks command-owner fencing, typed positions/orders and stale-predecessor protection.
4. Task completion, successor persistence and dispatch have no atomic crash/replay law.
5. Invocation and grants are not bound tightly enough to contribution version, installed instance/config revision and effect/parameter/account scope.
6. Recipe identity is defined as its output release, leaving no stable pre-execution recipe-definition identity.
7. Job, stream, package, session and cross-store recovery lifecycles remain incomplete.

Full counterexamples and repair choices are in `ARCHITECTURE-FINDINGS.md` (AF-01..AF-20).

## Coverage result

- Pass I was derived and frozen before candidate architecture/contracts/reviews were read.
- Frozen baseline SHA-256: `1c2c865d1cef50076682a737472174fa307cf1fc8eb3663b122ed04ab6f39fd8`.
- Scenario catalog: **85 unique scenarios** — 65 Pass-I and 20 clearly labeled Pass-II additions.
- BDD mapping: **85 catalog IDs = 85 feature IDs**, with zero missing, extra or duplicate IDs.
- High-risk combinations cover discovery/use races, external retries, crash/restart workflow dispatch, session concurrency, data provenance, replay/live streams, trading handover, distributed restore, composite authority and skill assurance.
- Remaining holes are decision/schema/recovery gaps, not a need for arbitrary scenario inflation.

## Bounded evidence

- Input archive SHA-256 matched exactly: `4247e7e84eba458a2d73c696dd2783b0635a36379dd9e3144da87a6cba478b87`.
- All 21 candidate manifest entries matched path, byte length and SHA-256.
- Docs and implementation revisions matched the requested commits.
- Focused QML research/mill slice: **47 passed**; QML default selection: **4 passed**.
- QMN conformance: **5 passed, 1 skipped**.
- QMA was source-inspected, not reported green. At the pinned revision its TaskGraph store is in memory, edges/successor walking/product sessions are absent, owner dispatch is not live, topology validation is incomplete, and ContributionHit remains proposed.
- No live broker/provider, secrets, paid service, mutation run or destructive action was used.
- No app/code change occurred, so Reticle was not applicable.

## Delivered package

1. `CODEX-CHALLENGE-RETURN.md` — this summary.
2. `INDEPENDENT-SCENARIO-BASELINE.md` — immutable Pass-I derivation and provenance.
3. `SCENARIO-CATALOG.jsonl` — documented proposed schema plus 85 records; no QMX persisted contract IDs invented.
4. `behavior/` — specification-only Given/When/Then files preserving every catalog ID.
5. `COVERAGE-AND-GAPS.md` — requirement/design/evidence trace and interaction matrix.
6. `ARCHITECTURE-FINDINGS.md` — severity-calibrated counterexamples and repairs.
7. `TEST-AND-MUTATION-PLAN.md` — completed evidence, ordered future gates and safe optional mutation plan.
8. `EVIDENCE-MANIFEST.json` — versions, source/hashes and diagnostic results.
9. `GROK-RECONCILIATION-HANDOFF.md` — prioritized reconciliation sequence and exact required output.
10. `diagnostics/` — compact raw integrity, test and environment logs.

## Evidence limits and stopping rule

BDD is specification, not proof that `.feature` files run. Existing package tests do not prove cross-component adoption. Public-domain meanings were checked against primary sources, but no donor runtime was adopted and no dependency was pinned by this challenge.

This Stage-B task now stops for Grok reconciliation. Do **not** start Documentation Factory, implementation, canonical-document edits or ratification from this return alone.
