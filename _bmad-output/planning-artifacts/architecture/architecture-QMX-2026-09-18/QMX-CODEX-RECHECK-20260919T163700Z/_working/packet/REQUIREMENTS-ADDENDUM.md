---
name: Workflows construction kit — requirements addendum
sitting: architecture-QMX-2026-09-18
status: proposed — Stage C reconciled; not ratified; Documentation Factory not issued
---

# Requirements addendum (Stage C candidate)

These are **proposed** requirements. They are not ratified. IDs are sitting-local (`WF-R-*`). Codex Pass-I BR-* / P1-* remain independent and are not replaced.

## Enabling requirements (must be true of the kit)

| ID | Requirement | Spine | Journeys |
|---|---|---|---|
| WF-R-01 | QMF remains the one framework; no sixth COMP without named amendment | AD-1 | J08, J24 |
| WF-R-02 | Artifact Library kinds stay the Workbench AD-3 roster; discovery adds ContributionHit without new kinds | AD-2 | J12, J19 |
| WF-R-03 | Every public operation has a versioned descriptor (AD-3) shared by app, copilot, workflow, CLI | AD-3, AD-21 | J09 |
| WF-R-04 | Experimentation Board is a layout projection; Graph Template is the reusable DAG; Task Graph is one Mission | AD-4, AD-6, AD-7 | J15, J16 |
| WF-R-05 | Authoring vs app-use product sessions are distinct authority overlays | AD-8, AD-9 | J01, J02 |
| WF-R-06 | App-use cannot edit implementation, install code, or widen its grants | AD-8, AD-29 | J01 |
| WF-R-07 | Four composition modes: artifact consume, operation invoke, coordinating workflow, composite app | AD-10 | J12 |
| WF-R-08 | Default Book/BMS system remains evaluable and deployable with regression | AD-11 | J03, J10 |
| WF-R-09 | Non-Book / non-trading work is honest: no dummy Book/BMS/MIS; data/ML need not be a bot | AD-11 class 3 | J06, J13 |
| WF-R-10 | A complete Alternative Trading Composition (portfolio/risk/sizing, not research) can be authored, validated, simulated, paper-traded, and live-deployed without Book keys; QML/QMB/MIS/QMN adopt the selected composition; sequential paper-then-live + L17; sensing is not this requirement | AD-11, AD-23 | J03b |
| WF-R-11 | Data recipes pin definition identity plus inputs/transforms/splits; provider ≠ venue; preview ≠ export ≠ stream | AD-12, AD-31 | J06, J17 |
| WF-R-12 | Sequential stopped/flat handover is the default deploy path and is fenced | AD-14, AD-25 | J10 |
| WF-R-13 | Packages export/install without author secrets or private chats; scanner is the oracle | AD-18, AD-30 | J08, J24 |
| WF-R-14 | Copilot discovers host-granted descriptors; prose is not authorization | AD-9, AD-24 | J11, J19 |
| WF-R-15 | UI host contribution contracts exist; chrome remains GAP-0081 | AD-17 | J19 |
| WF-R-16 | Headless/CLI/library parity of operation meaning across **supported** doors; QMB is the only operator CLI | AD-21 | J09 |
| WF-R-17 | Portfolio Manager is the trading-floor Role **label**; identities not rewritten | AD-22 | — |
| WF-R-18 | Mutation testing is optional test-strength, not a runtime | AD-19 | — |
| WF-R-19 | Public invocations carry logical/attempt identity, contribution tuple, instance, config revision, grant snapshot, and effect-specific idempotency | AD-24 | J26 |
| WF-R-20 | Grants are structured records bound to version, instance, effect, parameter ceiling, account scope, audience, expiry | AD-24 | J01 |
| WF-R-21 | Completing a task and dispatching successors is one recoverable outbox transition | AD-26 | J27 |
| WF-R-22 | JobHandle uses QMA AD-17 vocabulary; partial artifacts are labelled; first durable terminal wins | AD-26 | — |
| WF-R-23 | Fan-out/join has declared algebra for empty/missing/duplicate/late/failed partitions and partial retry | AD-26 | — |
| WF-R-24 | Replay-to-live has epoch/sequence, atomic cutover, bounded backpressure, and shared consumer leases | AD-28 | J17 |
| WF-R-25 | Product-session mutations are compare-and-set; reconnect does not replay intent | AD-29 | J01 |
| WF-R-26 | Cross-store restore uses an application checkpoint manifest and quarantines orphans | AD-27 | — |
| WF-R-27 | Pin/invoke revalidates contribution availability; tombstone ≠ other-version resolve | AD-30 | J08 |
| WF-R-28 | Change requests carry base identity and apply evidence; app-use cannot apply | AD-29 | J01 |

## Explicit non-requirements (this increment)

- Implementing every OP-* seed or donor feature
- Hot replacement of live positions
- Marketplace / SaaS tenancy
- Importing n8n, Hermes, OpenBB, LEAN, or json-render as the domain runtime
- Filling GAP-0085 / GAP-0063 / GAP-0058 / GAP-0062
- Ratifying ADR-0023 (mill remains provisional; code is reused)
- Treating Codex BDD files as executed tests
- Self-ratifying this architecture or starting Documentation Factory from Stage C

## Mapping to operator INT-*

INT-01..30 in `02-OPERATOR-INTENT-AND-SCOPE.md` are preserved. Conflicts with current law are in `CONFLICT-REGISTER.md`. INT-18 vs L36 is **closed**: named L36 amendment (default implementation, not ceiling). Documentation Factory writes the constitution text.
