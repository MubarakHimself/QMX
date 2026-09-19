# Operator intent, corrections and scope

> Process update: use `10-STAGED-PROCESS-AND-REVIEW-CONTRACT.md` for the Grok → Codex → Grok handoff and the latest delegation rules. Historical evidence is unchanged.

**Basis:** the conversation leading to this package, the original brief, and the supplied Codex intent ledger. This is a synthesis, not a fabricated transcript. `INT-*` identifiers are handoff-local retrieval aids, not minted QMX requirements, ADRs or contracts. Read the new full transcript before resolving ambiguities.

## Settled product direction

| ID | Direction to preserve | What not to infer |
|---|---|---|
| INT-01 | QMF is the one framework/construction kit. Existing libraries belong to the ecosystem. | Do not force every library into one namespace/process or introduce another general framework. |
| INT-02 | QMX Workflows composes purposeful capabilities; the exploratory surface is the Experimentation Board. | A board need not be a single runnable graph or a reusable production artifact. Do not rename it Research Board. |
| INT-03 | Defaults, reusable templates and custom creation all matter. | Do not give the user an empty canvas; do not restrict them to shipped nodes. |
| INT-04 | Node granularity is intentional and flexible. Notebooks/scripts can encapsulate work or expose selected stages/code for inspection. | Neither every variable nor no internal stage must become a node. |
| INT-05 | Connections have explicit meanings, compatible ports, references and cardinality. | No random wiring; no automatic execution because two cards were placed together. |
| INT-06 | Capabilities, extensions, workflows, mini-apps and widgets are related but distinct. | No compulsory one-to-one app/agent/department/workflow hierarchy. |
| INT-07 | Author through the copilot, manually, or with code/CLI/notebook tools. Deterministic and agentic work can coexist. | No mandatory agent for ordinary computation; no mandatory visual programming. |
| INT-08 | QuantMind/QMX Copilot can be the familiar identity, with independent sessions and specialists as useful. | Not one global transcript, one compulsory model, or a deletion of QMA specialists. |
| INT-09 | Authoring sessions can develop candidate implementations. App-use sessions inspect and invoke exposed operations without editing app implementation. | An app-use request must not silently escalate into developer authority. |
| INT-10 | Session-owned structured context, not automatic tab switching or internal screenshot interpretation, governs work. | A dashboard account filter is not a command target selector. |
| INT-11 | Apps describe their copilot context, operations, documentation/skills and lineage. A change request can hand work into an authoring session. | The app's manifest or text cannot grant its own permissions or require a whole private authoring transcript. |
| INT-12 | Broad memory/context capability, RLM where useful, skills/hooks, logs and traceability are important. | Memory, knowledge, active context, work records, telemetry and authority must not be one undifferentiated store. |
| INT-13 | Local file access, commands and external browser/computer use are legitimate provisionable capabilities. | No implied unrestricted filesystem/account access or invented browser availability. |
| INT-14 | Customizability is platform-wide, not confined to indicators. The user wants less recurring core maintenance. | Existing modular source alone does not prove an installable user-facing extension system. |
| INT-15 | Shareable/versioned packages can be installed in another person's QMX with their own configuration. | No compulsory marketplace, cloud tenancy or public publication. |
| INT-16 | Data handling deserves a first-class expansion assessment: multiple sources, data kinds, historical/live modes, APIs/CLIs, polling, streaming, resolution and provider settings. | Storage correctness is not the entire data product; market data access is not execution authority. |
| INT-17 | Research scope includes data, ML, sentiment, sector/industry studies, portfolios and tools, not only trading ideas. | Do not require all useful outputs to be bots or backtests. |
| INT-18 | QMF should construct materially different complete trading systems. Book/BMS/SQS/MIS are not the permanent ceiling. | No fake Book/BMS wrappers; do not casually delete current safety mechanisms before analysing responsibility. |
| INT-19 | QML, QMB, QMA, QMN and QMF all participate in the blast radius. Existing system behavior needs preservation and refactoring where justified. | Do not reduce the upgrade to QMN or to a visual overlay. |
| INT-20 | Sequential version development, evaluation and non-real-money validation precede deliberate deployment. | The user did not demand arbitrary hot replacement of live positions. |
| INT-21 | Continuous trading on a VPS is a central placement use case, with local or supervised operation also possible for other systems. | QMN's current implementation is more than a server label; audit host/policy separation rather than assume it. |
| INT-22 | Multiple brokers, accounts, currencies, instruments, data providers and execution environments must be explicit. | Same instrument label does not mean same venue identity; more accounts do not prove more adapter technologies. |
| INT-23 | GPU/local/server training and separate inference/deployment needs must be verified, including entitlement, availability and credentials. | No provider subscription or GPU exists merely because a request names it. |
| INT-24 | Agentic plugins and platform extensions can interact but have different responsibilities. | QMA's existing plugin loader does not automatically supply UI, trading or app-package contracts. |
| INT-25 | Trading-floor PM means Portfolio Manager. | Preserve genuine Product Manager references in BMAD/product work; migrate affected identities deliberately later. |
| INT-26 | Use BMAD architecture, CIS, available sub-agents and fresh studies; make the technical recommendations. | Do not ask the operator to design schemas or infer unlimited actual tooling. |
| INT-27 | Treat product references as sources of mental models, not mandatory dependencies. | Do not copy donor runtimes, proprietary features, object models or data without scrutiny. |
| INT-28 | Explore beyond examples and map ideas to journeys. | No fixed 40/80/200 ceiling, but no requirement to build all ideas. |
| INT-29 | Backend, data, persistence, APIs and extension/host contracts now; final visual design later. | A backend contract does not establish completed UI or full operational readiness. |
| INT-30 | Finish architecture with Documentation Factory handoff, then epics/stories and existing implementation automation in separate sessions. | Do not begin production implementation or automatically ratify drafts in this session. |

## Questions delegated to the architecture lead

Resolve with evidence: where shared contracts live; whether a focused new library is needed; how a general workflow relates to QMA; exact session and app-context schemas; durable writer/record ownership; the full alternative-policy lifecycle; data recipes and heterogeneous payloads; install/compatibility mechanisms; compute/provider integration; how UI contributions are hosted; and which current constraints need amendment.

The operator supplies outcomes and use cases. The architect proposes the machinery, comparisons and migration plan. Those technical recommendations are not already accepted simply because they appear in this package.

## Latest corrections that defeat earlier readings

The conversation evolved. Preserve the final position rather than replaying every earlier debate:

- One familiar copilot identity is now compatible with the desired experience; the latest distinction is **authoring vs app-use product sessions**, with their own scope and tools. This is not approval for one global Agent or removal of specialists.
- QMF must permit constructing different systems. Book variations alone do not satisfy that goal.
- The node editor is for intentional operations, with notebook/code flexibility, not a compulsory visualisation of every concept.
- “Identity-bearing” means recording exact semantic versions/inputs, not banning change. Normal rollout is sequential, not mandatory hot-swapping.
- The audit's QML absence statements were revision-limited. Read the delta correction before planning new work.
- UI reference screenshots are inspiration, not shipped QMX functionality, numerical trading evidence, final navigation or accepted layouts.
- The full transcript is a requirement/idea source, not a literal implementation backlog.

## Source pointers

Original brief: `evidence/original-workflows-architecture-prompt.md`.

Audit intent record, unchanged and baseline-limited: `evidence/audit/INTENT-AND-AUTHORITY-LEDGER.md`.

Newer-code correction: `evidence/review-delta.md`.

The new exported transcript supplied beside this ZIP contains the complete current discussion. The older `evidence/earlier-session-snapshot.md` ends earlier and is retained only for audit provenance.


## September 18 process and composition update

The operator delegates ordinary technical review to the installed skills/models and does not want routine midpoint questioning or manual inspection of every document. Grok should explore broadly with useful subagents, then use installed BMAD architecture. A deliberate independent Codex scenario/challenge session now separates Grok's complete candidate from its final reconciliation. The operator transfers artifacts; Documentation Factory and implementation remain later sessions. Read files 10–13 for the exact staged exits.

Cross-app composition includes saved-output reuse, operation invocation, optional coordinating workflows and composite apps assembled from supported contributions. Apps may use internal typed APIs and files/streams with explicit contracts; no transport choice was dictated. Copilot discovery and scope must adapt to registered contributions without self-granting permissions. New Hermes references supplement previous studies. mutmut is a tool to evaluate for real Python tests, not a replacement for scenario generation. The authoring/app-use session distinction, specialists, and Portfolio Manager correction remain in force.
