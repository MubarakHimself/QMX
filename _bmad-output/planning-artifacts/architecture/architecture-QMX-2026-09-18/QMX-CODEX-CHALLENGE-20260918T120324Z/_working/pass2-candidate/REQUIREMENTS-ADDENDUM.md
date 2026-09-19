---
name: Workflows construction kit — requirements addendum
sitting: architecture-QMX-2026-09-18
status: proposed — for Documentation Factory after Stage C
---

# Requirements addendum (Stage A candidate)

These are **proposed** requirements for later Documentation Factory / epics. They are not ratified. IDs are sitting-local (`WF-R-*`).

## Enabling requirements (must be true of the kit)

| ID | Requirement | Spine | Journeys |
|---|---|---|---|
| WF-R-01 | QMF remains the one framework; no sixth COMP without named amendment | AD-1 | J08, J24 |
| WF-R-02 | Artifact Library kinds stay the Workbench AD-3 roster; discovery adds ContributionHit without new kinds | AD-2 | J12, J19 |
| WF-R-03 | Every public operation has a versioned descriptor (AD-3) shared by app, copilot, workflow, CLI | AD-3, AD-21 | J09 |
| WF-R-04 | Experimentation Board is a layout projection; Graph Template is the reusable DAG; Task Graph is one Mission | AD-4, AD-6, AD-7 | J15, J16 |
| WF-R-05 | Authoring vs app-use product sessions are distinct authority overlays | AD-8, AD-9 | J01, J02 |
| WF-R-06 | App-use cannot edit implementation, install code, or widen its grants | AD-8 | J01 |
| WF-R-07 | Four composition modes: artifact consume, operation invoke, coordinating workflow, composite app | AD-10 | J12 |
| WF-R-08 | Default Book/BMS system remains evaluable and deployable with regression | AD-11 | J03, J10 |
| WF-R-09 | Non-Book / non-trading work is honest: no dummy Book/BMS/MIS | AD-11 | J03, J06, J13 |
| WF-R-10 | Live/node-paper without Book is refused until L36 amendment | AD-11 | J03, J10 |
| WF-R-11 | Data recipes pin inputs/transforms/splits; provider ≠ venue; preview ≠ export ≠ stream | AD-12 | J06, J17 |
| WF-R-12 | Sequential stopped/flat handover is the default deploy path | AD-14 | J10 |
| WF-R-13 | Packages export/install without author secrets or private chats | AD-18 | J08, J24 |
| WF-R-14 | Copilot discovers host-granted descriptors; prose is not authorization | AD-9 | J11, J19 |
| WF-R-15 | UI host contribution contracts exist; chrome remains GAP-0081 | AD-17 | J19 |
| WF-R-16 | Headless/CLI/library parity of operation meaning | AD-21 | J09 |
| WF-R-17 | Portfolio Manager is the trading-floor Role **label**; identities not rewritten | AD-22 | — |
| WF-R-18 | Mutation testing is optional test-strength, not a runtime | AD-19 | — |

## Explicit non-requirements (this increment)

- Implementing every OP-* seed or donor feature
- Hot replacement of live positions
- Marketplace / SaaS tenancy
- Importing n8n, Hermes, OpenBB, LEAN, or json-render as the domain runtime
- Filling GAP-0085 / GAP-0063 / GAP-0058 / GAP-0062
- Ratifying ADR-0023 (mill remains provisional; code is reused)

## Mapping to operator INT-*

INT-01..30 in `02-OPERATOR-INTENT-AND-SCOPE.md` are preserved. Conflicts with current law are in `CONFLICT-REGISTER.md`. Live non-Book (INT-18 vs L36) is the only constitution-level hold.
