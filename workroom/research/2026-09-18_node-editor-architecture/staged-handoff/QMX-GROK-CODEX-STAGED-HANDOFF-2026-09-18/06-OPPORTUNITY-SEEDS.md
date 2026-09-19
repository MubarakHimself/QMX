# Opportunity seeds and journey traceability

**Status: optional opportunity space, not accepted implementation scope.** These 80 seeds translate recurring themes from the conversation into possible applications of the enabling architecture. They make no claim about profitability, feasibility of a specific model, available subscriptions or current QMX support.

Use CIS to add, challenge, split, merge and prioritize ideas; there is no ceiling. Do not expand every idea into a subsystem or make delivery of all ideas an architecture acceptance condition. For a retained idea, record the relevant user, starting state, operations, data/contracts, observable output, failure/recovery behavior, dependencies, unknowns and evidence required. Then connect selected opportunities to full user journeys and later UX work.

The input/output and journey columns below are the initial traceability, not complete designs. `OP-*` and `J*` identifiers are local to this handoff. Technical costs and scope decisions belong to the investigated architecture.

## Data acquisition and meaning

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-001 — Dataset recipe builder | Combine prices and non-price releases into an immutable dataset with explicit joins. | Recipe, releases, transformations → dataset and lineage | J06,J13 |
| OP-002 — Provider disagreement workbench | Compare matching observations without silently merging conflicting sources. | Two provider releases → attributed differences | J06,J20 |
| OP-003 — Historical universe builder | Construct sector/instrument membership as known at each evaluation time. | Membership and price histories → point-in-time universe | J06 |
| OP-004 — Data revision explorer | Inspect how later corrections change a study without rewriting the original run. | Original/revised releases → revision-impact report | J06,J18 |
| OP-005 — Corporate-action/normalization lab | Compare raw and explicitly adjusted series under declared methods. | Price/action inputs → labelled derived series | J06,J13 |
| OP-006 — Streaming capture and gap replay | Record accepted observations and diagnose missing or late intervals. | Subscription and capture policy → replayable data and gap report | J17,J18 |
| OP-007 — API/CLI/file provider wrapper | Expose a provider through a typed operation and configure it without private core edits. | Adapter/configuration → discoverable provider operation | J09,J20,J24 |
| OP-008 — Dataset quality and entitlement preview | Inspect schema, coverage, freshness and access before a large job. | Provider capability and sample → preflight report | J06,J20 |

## ML and feature experimentation

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-009 — Model comparison studio | Evaluate several models under one explicit data/split/evaluation protocol. | Models and pinned dataset → comparison artifacts | J07,J13 |
| OP-010 — Feature engineering workspace | Create reusable feature transforms with declared temporal semantics. | Data and feature code → versioned feature dataset | J06,J13,J24 |
| OP-011 — Neural portfolio candidate | Explore a neural allocation/sizing policy as an alternative implementation. | Training protocol and policy → candidate and evaluation evidence | J03,J07 |
| OP-012 — Tree-model intelligence candidate | Compare an alternative intelligence model against a baseline without assuming replacement is better. | Feature data and model → shadow comparison | J04,J13 |
| OP-013 — Clustering and segmentation study | Investigate data segments without forcing the output into a trading bot. | Dataset and clustering procedure → labels and diagnostics | J13 |
| OP-014 — Forecast evaluation bench | Measure prediction performance under declared horizons and information timing. | Forecasts and historical data → evaluation report | J06,J13 |
| OP-015 — Typed model-output adapter experiment | Investigate Jev/other typed decision outputs through a declared interface. | Verified provider/model interface → typed results and tests | J13,J24 |
| OP-016 — Model artifact lineage explorer | Link training data, weights, evaluation and inference deployment. | Model family and versions → provenance view | J04,J07,J18 |

## Portfolio and trading-system compositions

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-017 — Default-system version comparator | Compare complete Book/BMS versions without rescaling old trades as new runs. | Two complete configurations → rerun comparison | J03,J09 |
| OP-018 — Non-Book scalping system | Explore a different sizing/admission arrangement without fake Book/BMS records. | Policy, strategy and data → alternative system evidence | J03,J10 |
| OP-019 — Multiple sizing-policy laboratory | Compare policy semantics and risk units explicitly. | Policies and evaluation protocol → qualified comparison | J03 |
| OP-020 — Optional-intelligence experiment | Compare the same declared system with different or no intelligence input. | System variants → evidence and explanatory limits | J03,J04 |
| OP-021 — Strategy hybrid constructor | Author and evaluate combinations of two strategies through supported authoring operations. | Strategy definitions and construction script → candidates | J14,J15,J16 |
| OP-022 — Cross-account allocation study | Explore aggregate allocation while preserving per-account constraints and identity. | Accounts and policy inputs → analysis-only proposal | J03,J05 |
| OP-023 — Sequential deployment planner | Prepare a measured, explicit transition between validated system versions. | Readiness/state checks → deployment plan | J10,J18 |
| OP-024 — Supervised versus unattended profile | Compare operational requirements for local supervised and continuous hosted operation. | System capability needs → deployment profile options | J07,J10 |

## Research and authoring procedures

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-025 — WF1-style cited research pipeline | Gather authorized material and produce structured hypotheses with unresolved details preserved. | Sources and research task → candidate table | J14,J22 |
| OP-026 — Research-to-code procedure | Convert selected candidates into QML artifacts through explicit authoring and conformance. | Hypotheses and authoring tools → executable candidates | J14,J03 |
| OP-027 — Bounded diagnosis-and-revision loop | Use results to propose targeted changes with budgets and recorded stop reasons. | Experiment results → revised candidate and justification | J14,J16 |
| OP-028 — Dictionary authoring helper | Create and validate reusable vocabulary entries without turning every entry into a node. | Authored definitions → versioned vocabulary content | J14,J15 |
| OP-029 — Experiment notebook-to-operation | Wrap a useful script/notebook behind tested input/output contracts. | Notebook and contract → reusable capability | J09,J24 |
| OP-030 — Study procedure capture | Extract deliberate reusable steps from a successful exploration, not every incidental tool call. | Selected operations/history → template candidate | J15 |
| OP-031 — Candidate-review table | Inspect claims, open questions and result links across a candidate collection. | Candidate/evidence refs → reviewable table | J14,J19 |
| OP-032 — Partial hypothesis experimentation | Test a specified component without fabricating missing exits or full-system claims. | Partial candidate and declared test scope → limited result | J14,J15 |

## Intelligence and analytical mini-apps

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-033 — Energy-sector intelligence workspace | Combine industry data, market data and declared analysis tools. | Sector recipe and methods → app/report outputs | J06,J13,J19 |
| OP-034 — Macroeconomic release monitor | Track releases, revisions and analysis with explicit timing. | Macro provider and workflow → briefing/evidence | J06,J17,J23 |
| OP-035 — Liquidity-state monitor | Investigate liquidity measures using appropriate supported observations. | Market data and feature method → labelled measures | J04,J17 |
| OP-036 — Sentiment analysis comparison | Compare methods against defined examples and source evidence. | Authorized news/text and methods → evaluation | J13,J14 |
| OP-037 — Cross-market relationship study | Study related instrument series without implying permission to trade each instrument. | Separate sources and instruments → relationship diagnostics | J06,J13 |
| OP-038 — Daily analytical briefing | Aggregate selected app/workflow outputs without inventing a trading recommendation or certainty. | Pinned completed results → attributed briefing | J23,J19 |
| OP-039 — Economic heatmap component | Present normalized metrics with documented units and update timing. | Declared metric releases → reusable widget | J06,J19,J24 |
| OP-040 — Universe screener recipe | Filter a supported universe through explicit data/feature criteria. | Universe plus filters → inspectable candidate set | J06,J16 |

## Workflow construction and runtime

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-041 — Typed fan-out/join builder | Apply explicit broadcast, zip, keyed or Cartesian mappings. | Typed collections → attributed parallel work | J16 |
| OP-042 — Reusable subworkflow library | Publish tested compositions with versioned inputs/outputs. | Workflow definition → reusable template | J15,J12 |
| OP-043 — Selected-subgraph execution | Run a valid board portion without executing unrelated drafts. | Selection and resolved inputs → scoped run | J15 |
| OP-044 — Dependency-aware rerun planner | Identify affected outputs and permissible cache reuse after a change. | Version diff and lineage → rerun plan | J15,J18 |
| OP-045 — Error and recovery branch patterns | Expose meaningful failure handling instead of hidden retries. | Failure classification → bounded recovery procedure | J16,J18 |
| OP-046 — Human-review checkpoint | Pause a procedure and resume with an explicit recorded decision. | Candidate/evidence → review record and continuation | J14,J18 |
| OP-047 — Schedule and webhook triggers | Start authorized workflows from explicit events with deduplication. | Trigger and workflow versions → durable invocation | J23,J17 |
| OP-048 — Run comparison and trace inspector | Inspect inputs, attempts, outputs and skipped/failed branches. | Run references → evidence-centred comparison | J09,J16,J18 |

## Copilot and agent skills

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-049 — App-use explanation companion | Explain a result using its exact inputs and work records. | App/run context → grounded explanation | J01,J19 |
| OP-050 — App-use change-request builder | Package an observed problem into a scoped authoring handoff. | Result plus user intent → change-request artifact | J01 |
| OP-051 — Session history retrieval | Retrieve relevant past decisions without mixing current command targets. | Authorized query/scope → cited historical context | J02 |
| OP-052 — Capability-aware authoring assistant | Discover shipped tools and missing requirements before writing custom code. | Goal and catalogue → proposed composition | J15,J20,J24 |
| OP-053 — Skill activation evaluation | Measure desired and undesired activation with neighbor skills present. | Skill/cases → versioned activation report | J11 |
| OP-054 — Skill ablation comparison | Compare behavior with and without a skill under matched conditions. | Pinned eval setup → incremental-value evidence | J11 |
| OP-055 — Specialist delegation inspector | Show authorized specialist work and its outputs without requiring many permanent chat panes. | Tasks/agents/work records → work view | J14,J19 |
| OP-056 — App integration profile authoring | Declare allowed context/actions and docs for an app-use companion. | App contracts → validated profile candidate | J01,J19,J24 |

## Packaging and mini-app interoperability

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-057 — Extension scaffold generator | Create a documented package using actual public interfaces. | Contribution type and tests → package candidate | J08,J24 |
| OP-058 — Install preflight inspector | Explain dependencies, permissions and configuration before activation. | Package manifest → install plan/refusal | J08,J21 |
| OP-059 — Cross-app exported analysis | Let one app invoke another app’s versioned operation. | Export/dependency contract → attributed result | J12 |
| OP-060 — Reusable widget catalogue | Register rich views against explicit results and actions. | Component implementation/spec → discoverable view | J19,J24 |
| OP-061 — Mini-app parameter linking | Bind shared dates, universes or models without hidden global mutable state. | App configuration → explicit linked parameters | J19,J02 |
| OP-062 — App version diff and lineage | Explain what changed between versions and which evidence supported it. | Version manifests → change/readiness view | J01,J21 |
| OP-063 — Private-to-shareable export | Remove private chats/credentials while retaining useful docs and allowed lineage. | Installed app and export policy → distributable package | J08,J22 |
| OP-064 — Dependant-aware uninstall | Detect affected apps/workflows before disabling a provider or extension. | Dependency graph → safe removal plan | J12,J21 |

## Compute and operational tooling

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-065 — Execution environment preflight | Test actual hardware, dependencies and access for a requested workload. | Requirement and provider config → placement result | J07,J20 |
| OP-066 — CLI-backed operation inspector | Show structured progress, logs, outputs and cancellation for a command operation. | Typed command request → tracked invocation | J09 |
| OP-067 — Training-to-inference transfer | Move validated model artifacts between different compute environments. | Model/checkpoint and compatibility → inference candidate | J04,J07 |
| OP-068 — Long-run recovery console | Inspect unfinished, interrupted and unknown work using authoritative records. | Run state → recovery options | J18 |
| OP-069 — Resource and quota overview | Expose current environment/data-provider limits before large fan-outs. | Configured/observed usage → planning view | J07,J16,J20 |
| OP-070 — Deployment readiness dashboard | Present validated prerequisites, latency measurements and unresolved conditions. | Deployment candidate and checks → readiness evidence | J10,J19 |
| OP-071 — Multi-account operations view | Aggregate readouts with unambiguous account/currency/mode labels. | Authorized per-account data → attributed dashboard | J05,J19 |
| OP-072 — Backup/restore verification recipe | Validate artifacts and linked records after restoration. | Backup manifest → restore consistency report | J18 |

## Quality, compatibility and governance tools

| Seed | Purpose | Inputs → outputs | Journey probes |
|---|---|---|---|
| OP-073 — Contract conformance runner | Check contributed operations against declared schemas and behavioral fixtures. | Contribution plus contract → test evidence | J09,J24 |
| OP-074 — Default-system regression suite | Preserve current behavior while the policy/host boundaries change. | Pinned baseline and new implementation → regression results | J03,J10 |
| OP-075 — Provider compatibility comparison | Compare semantics before replacing a data source. | Old/new provider mapping → migration assessment | J06,J20 |
| OP-076 — Context/permission red-team suite | Probe app content and memory for scope escalation and target confusion. | Profiles plus adversarial cases → findings | J01,J02,J22 |
| OP-077 — Result comparability checker | Identify valid and invalid comparisons across differing accounting/policy assumptions. | Run semantics → comparability report | J03,J13 |
| OP-078 — Package migration rehearsal | Test reversible and forward-only changes on disposable data. | Versions and fixtures → migration evidence | J08,J21 |
| OP-079 — Scenario coverage explorer | Link requirements, journeys, tests and unanswered risks. | Architecture/test register → coverage report | J01,J03,J18,J24 |
| OP-080 — Extension-maintenance boundary audit | Verify a new user capability can be added without editing private host internals. | Package/changed-files evidence → coupling assessment | J08,J12,J24 |


## How to choose implementation examples

Prefer a small set that jointly exposes the hardest contracts: an alternative non-Book trading composition, a non-trading multi-source ML study, an app-use/authoring handoff, and an installable headless capability consumed by another app. Add a streaming or remote failure case so a static happy path cannot pass for complete lifecycle support.

An early usable slice is not the scope ceiling. Conversely, the opportunity catalogue is not a promise to implement all donor-product features. Record what will be enabled by public interfaces, what requires later domain work, what is merely speculative, and what current evidence rules out.
