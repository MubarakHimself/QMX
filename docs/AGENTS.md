---
id: DOC-AGENTS
title: QMF V1 Agent Entry Point
type: agents
status: provisional
sources: [docs/constitution.md, docs/architecture/overview.md, docs/architecture/dependencies.yaml, docs/architecture/stack.md, docs/registry/variables.yaml, docs/contracts/, docs/components/, docs/decisions/, docs/gap-report.md, docs/scenarios/]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# AGENTS.md — Read This First

QMF V1 is a reusable Python toolbox from which QMX trading applications will be built; it is not itself a trading application. Its fixed public roster is five libraries plus the Venue and Risk modules, with internal data seams and external providers kept distinct. This knowledge base is **provisional design**, not implementation or live-operation authority: unresolved gaps and conflicts must be ratified by the operator before affected work begins.

## Reading order

1. [`docs/constitution.md`](constitution.md) — the laws; violating one is a bug by definition.
2. [`docs/architecture/overview.md`](architecture/overview.md) — system context, component boundaries, and layers.
3. [`docs/gap-report.md`](gap-report.md) — conflicts, blockers, graveyard, and deferred scope.
4. The spec for every component you will touch in [`docs/components/`](components/).
5. Every boundary named by those specs in [`docs/contracts/`](contracts/).
6. [`docs/registry/variables.yaml`](registry/variables.yaml) for values and [`docs/glossary.md`](glossary.md) for terminology.
7. The applicable ADRs in [`docs/decisions/`](decisions/) and scenarios in [`docs/scenarios/`](scenarios/).

Do not start with a transcript or a study recommendation. The reference docs and their explicit GAP markers are the execution boundary.

## Hard rules

- Later direct operator corrections govern conflicting historical material; research remains evidence until adopted. See [L1–L3](constitution.md#laws).
- Documentation and review precede code generation or trading-node implementation. See [L4](constitution.md#laws).
- QMF is a toolbox, not an application: loops, scheduling, orchestration, and product UI stay outside it. See [L7–L8](constitution.md#laws).
- qmf-core is definitions-only and asset-neutral; broker, runtime, download, backtest, and node behavior do not belong there. See [L13 and L16](constitution.md#laws).
- The public roster remains five libraries and two modules. Internal seams do not become public packages by implication. See [L14](constitution.md#laws).
- Public contracts are versioned from birth; incompatible meaning mints a new version. See [L15](constitution.md#laws).
- Only a human may promote an artifact into the live zone. See [L17](constitution.md#laws).
- Preserve complete raw evidence, keep the off-machine direction, and expose research data through explicit splits. See [L18–L19](constitution.md#laws).
- Synthetic data may test infrastructure and failures, never trading edge. See [L20](constitution.md#laws).
- The first Venue target is the cTrader Open API from Python, never MQL, behind a venue-neutral seam. See [L21–L22](constitution.md#laws).
- Provisional contracts, recommendations, and unresolved GAPs authorize neither implementation nor live money. Destructive and live actions require a ratified contract and explicit human authority. See [L29](constitution.md#laws).
- Never revive a dead decision. Check the [graveyard](gap-report.md#dead-decisions--18) before proposing a component, service, formula, or term that resembles old material.

## Before changing anything

1. Identify each affected `COMP-*` ID in [`dependencies.yaml`](architecture/dependencies.yaml).
2. Use the documentation-factory skill's `scripts/blast_radius.py`, passing the component ID and `--root .`; read every document it returns.
3. Read the component's `depends_on` and interface list. Every `CT-*` must resolve in [`docs/contracts/`](contracts/), and every peer must exist in the dependency manifest.
4. Read [`variables.yaml`](registry/variables.yaml). Never hardcode or restate a value that has a `registry:*` key; a null value remains unresolved.
5. Search [`gap-report.md`](gap-report.md) for every relevant component, contract, and term. A blocking gap means the affected behavior is not buildable.
6. Read the applicable scenario. A scenario labelled **blocked specification** is not complete, test-complete, releasable, or permission to fill placeholders.
7. Record any approved change in a new ADR and in [`changelog.md`](changelog.md). Do not mutate an existing ADR to rewrite history.

## Architecture preflight — before building anything new

Answer these items in the plan and the new ADR before writing code for a component, service, module, table, endpoint, adapter, or package.

1. **Read the inventory.** Cite [`dependencies.yaml`](architecture/dependencies.yaml), [`stack.md`](architecture/stack.md), and every plausible existing component spec.
2. **Prove reuse-or-new.** For each candidate component, state the exact authority boundary or contract mismatch that prevents reuse. If an existing component can own the behavior, extend it and stop.
3. **Keep the axes separate.** `layer`, `kind`, `roster_role`, and `distribution` mean different things. Distribution and package identity remain null until GAP-0002 is ratified.
4. **If new is required,** state what unique authority it owns, what it may never do, every contract at its boundary, and which existing authority becomes narrower.
5. **Check the graveyard.** A dead decision ends reuse of that idea unless a later operator ruling explicitly replaces it.
6. **Record the verdict.** Write `reuse COMP-<NAME>` or `new COMP-<NAME>` and the evidence in the ADR. An unrecorded verdict means the preflight did not happen.

## Change protocol

Before modifying component X:

1. Run blast-radius analysis for X and every directly affected peer.
2. Read the constitution, dependency manifest, target specs, contracts, registry entries, ADRs, gaps, and scenarios returned by the analysis.
3. Confirm that each prerequisite decision is ratified and every blocking gap for the slice is answered. A recommendation is not an answer.
4. Draft a new ADR with the architecture-preflight verdict and contract/version impact.
5. Update reference docs, registry/contracts, scenarios, gap status, index, and changelog in the same change.
6. Run the documentation-factory validators and do not report success while citations, graph alignment, or non-provisional release gates fail.

## Where answers live

| Question | Canonical document |
|---|---|
| What may never be violated? | [`constitution.md`](constitution.md) |
| What components exist and how do they connect? | [`overview.md`](architecture/overview.md) and [`dependencies.yaml`](architecture/dependencies.yaml) |
| What does a component own or refuse to own? | Its file in [`components/`](components/) |
| What crosses a boundary? | The matching file in [`contracts/`](contracts/) |
| What is the exact value? | [`registry/variables.yaml`](registry/variables.yaml) |
| Why was a direction chosen? | [`decisions/`](decisions/) and the decision locator in [`index.md`](index.md) |
| What is undecided, dead, deferred, or out of scope? | [`gap-report.md`](gap-report.md) |
| What behavior should a future test demonstrate? | [`scenarios/`](scenarios/) and [`fixtures-and-scenarios.md`](lenses/testing/fixtures-and-scenarios.md) |
| What changed in the knowledge base? | [`changelog.md`](changelog.md) |

## Current release gate

No QMF implementation, live venue connection, order submission, paper-mode transition, operational restore, destructive migration, or release-quality acceptance claim is authorized by this provisional corpus. The operator must resolve the two conflicts and the applicable blocking gaps, then ratify the packet before provisional statuses can be removed.
