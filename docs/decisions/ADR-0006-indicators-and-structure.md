---
id: ADR-0006
title: Indicator protocol, canonical arithmetic, and causal structure lifecycle
type: adr
status: ratified
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-REGISTRY]
decisions: [DEC-0055, DEC-0056, DEC-0058, DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134]
sources: [DEC-0126, DEC-0127, DEC-0128, DEC-0129, DEC-0130, DEC-0131, DEC-0132, DEC-0133, DEC-0134, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/.memlog.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/reviews/review-ict-edge-cases.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/reviews/review-general-ta-edge-cases.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/reviews/review-adversarial-3.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 1y
---

# ADR-0006: Indicator protocol, canonical arithmetic, and causal structure lifecycle

Date: 2026-08-20 (supersedes the 2026-08-18 placeholder text of this ADR, which recorded only the library split and left every protocol question GAP-defined). status: ratified — corpus signed off by the operator 2026-08-21 (conditional go-ahead in the PRD session; the independent contradiction sweep passed); the underlying rulings are operator-ratified (indicators/structure sitting, 2026-08-20).

## Context

The 2026-08-18 baseline split wrapped indicator arithmetic (qmf-indicators) from QMX-owned causal structure (qmf-structure) but left GAP-0031 through GAP-0034 open: no indicator protocol, no canonical arithmetic reference, no light-versus-heavy rule, and no structure lifecycle law. The 2026-08-20 sitting closed all four (spine AD-22 through AD-25), and its increment reviewer gate — an adversarial pass that found 36 conformant-but-divergent implementation pairs, plus two school-spanning edge-case lenses — amended the four new ADs and eight earlier ones (AD-2, AD-7, AD-8, AD-12, AD-14, AD-16, AD-17, AD-21) with additive contract surface. No ratified ruling was reversed. (DEC-0126, DEC-0130, DEC-0131)

## Options considered

1. **Adopt a third-party indicator/structure platform's contracts** — prohibited standing: the build-our-own boundary (DEC-0013) and the dead strategy-family-library entry (DEC-0014) forbid transplanting foreign platform contracts; retail structure libraries also repaint, which the lifecycle law exists to prevent.
2. **Reimplement reference arithmetic to own the numbers** — rejected: wrap-not-reimplement stands (DEC-0055); where the reference implements a formula, wrapping it is mandatory and reimplementation is a contract defect (DEC-0127).
3. **Two contracts, one law** — selected: CT-16 for values-per-instant, CT-17 for objects-with-lifetimes, both under identity-as-entire-configuration, typed refusals, and the same extension/graduation mechanics. (DEC-0126, DEC-0129)

## Ruling

- **CT-16 (AD-22):** one indicator contract, two conformant modes (batch + streaming) bound by a tier-2 equality law; series vocabulary (`Bar`, `Tick`/`Quote`, `BarSpec`, exact rationals) defined in qmf-core; `BarSpec` replaces bare "timeframe"; identity is the entire declared configuration and that fingerprint is the only dedup key; outputs are full-length, index-aligned, presence-mapped, and carry per-sample knowable-at; instances are shared per configuration, not per consumer. (DEC-0126)
- **Canonical arithmetic (AD-23):** TA-Lib 0.7.1 + 0.7.1 pinned as lockfile-resolved artifact hashes plus an identity-bearing reference-configuration record asserted at import; the QMX implementation is canonical where the reference lacks a formula; upgrades are gated with per-configured-indicator format mints; tolerances are integer ULP counts. (DEC-0127)
- **Light vs heavy (AD-24):** light iff four declared-and-benchmark-proven bounds hold; classification per configuration; the verdict is machine-scoped, display-only, and never identity; heavy by default until the live-path rung has a baseline; the same bounds bind structure families. (DEC-0128)
- **Causal structure lifecycle (AD-25):** a family is a type of chart object; objects are minted once at observation with observed-at (known-at semantics), anchor span, and a precise confirmation rule; lifecycle and interaction records are append-only edges with current state a read-time fold; evidence class is identity; the emission invariant is checked in-component now; the seed four families are candidates, not a privileged set. (DEC-0129)
- **Standing rules:** school-neutral vocabulary everywhere (DEC-0132); the plain-Python escape hatch with the experiment-to-extension graduation path is a first-class design feature, not an afterthought (DEC-0133). The freeze-choice count moves to four-of-six ratified (DEC-0134, superseding DEC-0124). The light/heavy vibe split of DEC-0056 is superseded by the four-bound rule (DEC-0128).

## Architecture preflight — reuse-or-new verdict

**Verdict: reuse.** Every ruling lands in an existing component: COMP-QMF-INDICATORS (CT-16, AD-23/24 machinery), COMP-QMF-STRUCTURE (CT-17, AD-25), COMP-QMF-CORE (series vocabulary, conversion boundaries, exact rationals — shared nouns per AD-2), COMP-QMF-DATA (bar aggregation as a fingerprinted derivation; purge/embargo manifest fields), and COMP-QMF-REGISTRY (new record and edge kinds through the existing kinds-addable mechanism). No new component is minted; custom indicators and families arrive as AD-2 extensions outside the roster, which is the ratified mechanism, not a component addition. Dead-list check: DEC-0014 (no strategy-family libraries — TA-Lib is arithmetic, wrapped under DEC-0013/DEC-0055, not a strategy family), DEC-0034 (no universal card — record kinds stay per-kind), DEC-0037 (no graph database — lifecycle edges stay pinned JSONL), and DEC-0057 (custom-indicator discovery stays out of scope) all remain honored.

## Consequences

- CT-16 and CT-17 carry ratified schemas and invariants; their component specs derive authority boundaries and failure modes from AD-22..AD-25 instead of GAP markers. GAP-0031..GAP-0034 move to answered; GAP-0033 was the last nonblocking gap.
- Research and the live path compute the same numbers by construction: one contract, shared instances, equality-law-bound modes, and a single canonical arithmetic per formula.
- The vocabulary shifts are binding on all documentation: `BarSpec` never bare "timeframe"; "family" means chart-object type only; no school names in rules (L32); presence maps instead of NaN.
- Deferred by design, not omitted: GAP-0016/GAP-0017 stay with the backtesting sitting (DEC-0121) — the in-component emission invariant is a cheap guard, not that gate; L2/footprint series vocabulary, bar-builder derivation details, and the six-stage latency decomposition sit in the spine's Deferred table; venue/risk/backtesting gaps (GAP-0035 and later) stay open and untouched here.

## Blast radius

Component specs qmf-indicators and qmf-structure (rewritten), qmf-core, qmf-data, qmf-registry (amendment ripple); contracts CT-16 and CT-17 (filled); registry `variables.yaml` (canonical reference pinned; BarSpec/presence/evidence-class enums added); constitution (L32, L33); glossary (BarSpec, presence map, knowable-at, evidence class, anchor span, interaction record, exact rational, PriceDelta, derived-series identity, standing object); gap report; stack; performance-budget, observability, bug-triage, ops, testing, and data lenses; traceability; index and architecture overview counts.
