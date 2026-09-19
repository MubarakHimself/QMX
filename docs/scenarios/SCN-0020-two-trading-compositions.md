---
id: SCN-0020
title: Two honest trading compositions — default Book path and ATC
type: scenario
status: ratified
component: COMP-QMB
depends_on: [COMP-QMB, COMP-QML, COMP-QMN, COMP-QMF-RISK]
decisions: [DEC-0424, DEC-0436, DEC-0438, DEC-0448, DEC-0450]
sources: [_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/JOURNEYS.md, _docwork/workflows-increment-brief.md, _docwork/riders/workflows-construction-kit-2026-09-19.md, docs/decisions/ADR-0024-workflows-construction-kit.md]
generated: 2026-09-19
verified: 2026-09-19
stale_after: 90d
---

# SCN-0020: Two honest trading compositions — default Book path and ATC

This scenario pins the two honest trading compositions (J03, J03b, J10): the default Book/BMS path remains the regression compile path; an Alternative Trading Composition (ATC) with Book/BMS/bot keys **absent** (not null) and a complete `PolicyPair` validates and simulates; dummy Book is `INVALID_INPUT`; sensing/`UngovernedWorkConfig` is not this journey; deploy uses sequential fencing; live follows paper then L17. [DEC-0424] [DEC-0436] [DEC-0438] [DEC-0448]

This document is a **specification of intended behavior**, not evidence that the code does this today. At `integration@270e992` `AlternativeRunConfig` / `PolicyPair` are not in code; QML→QMB→QMN cross-component integration is unsupported. [DEC-0450]

## Given

Three config types exist; they are not optional fields on one type. [DEC-0424]

1. **`ResolvedRunConfig`** — `book_fp1` / `bms_fp1` / `bot_fp1` / fragments **required**; default path to governed evidence, node-paper, live, L17 seats.
2. **`AlternativeRunConfig`** — Book/BMS/bot keys **absent, not null**; complete second trading system defined by a `PolicyPair` (`AccountingPolicy` + `RiskPolicy`), command binding, admission, evidence, and journey.
3. **`UngovernedWorkConfig`** — those keys absent; ungoverned library work, data-ML, recipes, QMN sensing-only. Sensing-only is **not a seat** and is **not** class (2).

L36 remains bot → Book → BMS → operator as the **default** authority chain. Book/BMS are the default implementations of accounting and risk/sizing roles, not the only implementations the kit may host. QMN remains the only venue importer. [DEC-0448]

Dummy (mechanical): a CT-22/CT-27/CT-33, or an ATC `PolicyPair`, minted solely to satisfy a required field, or whose policy is identity / no-op / unlimited / pass-through, or sentinel fps (`NULL_BOOK`, empty-object Book, `mis_ref: null` as fake MIS) — is dummy and is `INVALID_INPUT` at compile, register, validate, simulate, and seat. [DEC-0424] [DEC-0448]

## When

**(A) Default Book path (J03).** A composition using `ResolvedRunConfig` is validated, simulated, and (separately) deployed through existing QMN seats.

**(B) ATC path (J03b).** An `AlternativeRunConfig` with a complete `PolicyPair` and **no** Book/BMS/bot keys is selected. QML authoring, QMB backtest/optimize, optional MIS binding, and QMN adopt it. Validate/simulate write ATC journal rows. Paper-then-live uses J10 fencing with an ATC `composition_fp` and a QMN token after L17. [DEC-0424] [DEC-0436]

**(C) Sequential fenced handover (J10).** An old `composition_fp` with typed positions/orders is replaced: operator requests replacement; AD-25 states run to `fenced-activate` with a new command-owner epoch and token. [DEC-0438]

## Then

**(1) Default Book path regression holds.** CT-22/CT-27 remain required on `ResolvedRunConfig`. Existing compile/fragment tests are not weakened to admit ATC or ungoverned through `ResolvedRunConfig`. [DEC-0424]

**(2) ATC with zero Book keys validates and simulates.** When ATC is selected, consumers adopt it — they do not stay secretly Book-shaped. Evidence is QMB JSONL tagged `composition_class: alternative` plus CT-07 lineage to the PolicyPair hash; it is not a Book journal and not qmf-core. QMB issues internal ATC-simulate tokens. [DEC-0424] [DEC-0436] [DEC-0438]

**(3) Dummy is INVALID_INPUT.** Dummy Book/BMS or dummy PolicyPair is refused at compile, register, validate, simulate, and seat. [DEC-0424] [DEC-0448]

**(4) Sensing is not this journey.** Calling sensing, research, or `UngovernedWorkConfig` an Alternative Trading Composition is forbidden. [DEC-0424] [DEC-0436]

**(5) Sequential fencing.** One command owner per `(account, venue, role)`. Transition order: `idle` → `drain-requested` → `draining` → (`residuals-attributed` \| `unknown-blocked`) → `predecessor-acked` → `fenced-activate` → `active` → `retired`. UNKNOWN orders block (`unknown-blocked`) and are terminal for that attempt until operator reconcile — never an automatic retry. A restarted predecessor without the current token is refused. Software rollback after a new-owner fill cannot unfill. [DEC-0438]

**(6) Live after paper + L17.** Admission checks PolicyPair completeness, grants, health, sequential paper-then-live readiness, and L17 human promote before any live `VenueClientKind`. Live ATC without paper-then-live + L17 is `not_promoted`. [DEC-0436] [DEC-0448]

## Failure branches

**Branch A — dummy Book as “alternative system”.** A caller mints `NULL_BOOK` / empty Book / pass-through PolicyPair to satisfy fields. Outcome: `INVALID_INPUT`. [DEC-0424] [DEC-0448]

**Branch B — sensing labeled ATC.** Research/sensing/`UngovernedWorkConfig` is treated as a complete trading composition or a QMN seat. Forbidden. [DEC-0424] [DEC-0436]

**Branch C — hot-swap of live positions.** Two command owners on one `(account, venue, role)`, or live mid-position swap without fencing. Forbidden. [DEC-0438]

**Branch D — weakening ResolvedRunConfig tests.** Compile tests are altered to admit ATC or ungoverned keys through type (1). Forbidden. [DEC-0424]

**Branch E — claiming ATC implemented at 270e992.** Treating this scenario as proof that `AlternativeRunConfig` / `PolicyPair` exist in code. Forbidden. [DEC-0450]

## Worked numbers

None. This is a registry-independent composition-identity scenario. The load-bearing distinctions are: `ResolvedRunConfig` (required Book keys) vs `AlternativeRunConfig` (keys absent + complete PolicyPair) vs `UngovernedWorkConfig` (not a seat); dummy → `INVALID_INPUT`; live only after paper + L17 (DEC-0424, DEC-0436, DEC-0448).
