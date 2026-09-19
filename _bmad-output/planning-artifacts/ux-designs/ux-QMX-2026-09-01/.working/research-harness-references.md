# Research-harness references (brainstorming evidence)

Research date: 2026-09-12. Scope: primary-source inspection of the official
`synthetic-sciences` repositories (`openscience`, `delphi`) and the repository
linked by [openresearch.sh](https://openresearch.sh/). This is evidence for QMA
experimentation, not an approved architecture or a recommendation to install/run
these projects.

## Identity and source status

- **Synthetic Sciences — verified repository publisher.** The GitHub organization
  describes itself as an AI research lab, links `syntheticsciences.ai`, and lists
  OpenScience and Delphi as its repositories: [organization profile](https://github.com/synthetic-sciences).
- **OpenResearch — verified repository link, publisher label is alphaXiv.** The
  official site’s GitHub link resolves to `alphaXiv/OpenResearch`; the alphaXiv
  organization links `alphaxiv.org` and lists OpenResearch: [site](https://openresearch.sh/),
  [repository](https://github.com/alphaXiv/OpenResearch), [alphaXiv profile](https://github.com/alphaXiv).
  The requested label “Alpha Active” is **not verified** by these primary sources;
  retain it as a user-dictated label only.
- **Confidence convention.** “Advertised” means README/landing copy; “documented”
  means repository docs/skills; “code-confirmed” means an inspected source module.

## OpenResearch (alphaXiv/OpenResearch)

**Advertised/documented mechanisms.** The README advertises a local-first workspace
for literature review, hypothesis development, experiments, and artifacts; parallel
agents use independent sessions/worktrees; experiments are a Git-native tree and
each run archives its recorded commit immutably; logs, diffs, files, results and
artifacts stay tied to producing work; and the autonomous loop is propose → modify
code → run → inspect evidence → choose next action: [README](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/README.md#L37-L56).
The website’s visual preview also shows directions with run counts and states, but
that is product marketing/UI evidence rather than an execution guarantee: [site](https://openresearch.sh/).

**Documented experiment protocol; selected implementation checks.** The `orx-experiment-tree` skill instructs agents to keep a
node provisional until a run answers it; answered nodes freeze permanently. A child
inherits the parent’s run command, and only committed code/config may differ. It
explicitly prescribes “stacked bushes”: fan co-equal options within one decision,
then descend from the confirmed winner for the next decision, avoiding a flat sweep
or an unrelated single-child chain: [experiment-tree skill](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-experiment-tree/SKILL.md#L21-L87).
The same skill specifies a per-completion loop: wait for the first completion,
reconcile all terminal runs, read logs/diffs, then repair, refill, promote, or stop;
drain is the exit condition. It recommends stopping when the goal is met or after
about three consecutive failed/regressed runs, and writing a project artifact:
[loop](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-experiment-tree/SKILL.md#L89-L196).
The implementation creates every experiment as an `orx/<slug>` branch from the
parent/base branch and persists parent, description, command and chat-session IDs:
[experiments.rs](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/src/local/experiments.rs#L62-L121).
Per-agent isolation is code-confirmed: one `opencode serve` child per chat session
runs in its private worktree: [opencode.rs](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/src/local/opencode.rs#L0-L8).

**Evidence, stop, resume limits.** `orx-evidence` says run logs are the evidence
channel, requires metrics/configuration in stdout, and warns that status alone or
truncated output is not evidence: [evidence skill](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-evidence/SKILL.md#L1-L47).
The docs expose cancel, wait, and opt-in wake-up commands; wake resumes the agent
after success/failure, not a general checkpoint protocol: [compute skill](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-compute/SKILL.md#L63-L91).
No explicit monetary/token budget model was found in these inspected OpenResearch
skills; compute sizing and fixed run contracts are documented, so QMA must not infer
cost accounting from the tree alone.

## Delphi (synthetic-sciences/delphi)

**Advertised/documented.** Delphi indexes repositories, papers, documentation,
datasets and local folders; exposes MCP tools for indexing/search, symbols/callers,
token-budgeted context packs, reproducible context sessions for handoffs, and
policy-gated research jobs. Completed indexing creates immutable source snapshots:
[README](https://raw.githubusercontent.com/synthetic-sciences/delphi/master/README.md#L67-L90).

**Code-confirmed ingestion/provenance.** Snapshot contracts hash every normalized
item and the ordered snapshot content with SHA-256; snapshot metadata includes source
type, logical source ID, version, content hash and token totals: [contracts.py](https://github.com/synthetic-sciences/delphi/blob/master/backend/synsc/snapshots/contracts.py#L1-L202).
The snapshot service pins capture reads to one MVCC snapshot, copies chunks and
embeddings, then seals the immutable version; its source queries cover repo commit,
paper PDF hash, dataset and documentation versions: [service.py](https://github.com/synthetic-sciences/delphi/blob/master/backend/synsc/snapshots/service.py#L527-L563),
[service.py capture/seal](https://github.com/synthetic-sciences/delphi/blob/master/backend/synsc/snapshots/service.py#L683-L749).
This is a useful QMA pattern: resolve a logical source, capture a content-addressed
version, and attach retrieval/evidence to that version—not merely to a mutable URL.

## OpenScience (synthetic-sciences/openscience)

**Advertised/documented.** OpenScience describes a workbench that reads literature,
writes/runs code and experiments, records every step, supports Python/R/files,
connectors, bounded worker delegation and reviewable outputs: [README](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/README.md#L25-L33),
[workflow](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/README.md#L85-L106).

**Documented design and source-inspected evidence checks.** The scientific-harness design separates server
admission/identity/decisions/cancellation/replay/recovery from the model/tool loop,
and treats files, Results, jobs and permissions as owned services: [design](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/docs/notes/scientific-harness-design.md#L12-L57).
`research_contract` has typed domains/templates, required deliverables, stages,
checks, and preregistration. Non-pending checks require runtime-verified evidence
references; artifact refs are checked for active session lineage and SHA-256 blob
integrity: [contract schema](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/backend/cli/src/tool/research-contract.ts#L8-L73),
[evidence validation](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/backend/cli/src/tool/research-contract.ts#L233-L311).
The artifact store records version hashes, producing session/message/execution IDs,
command/code, stdout/stderr, model/provider, inputs, permissions, environment and
capture quality: [artifact store](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/backend/cli/src/artifact/store.ts#L9-L50).
Task evidence is derived from persisted tool records, not worker prose: [task-evidence.ts](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/backend/cli/src/tool/task-evidence.ts#L0-L5).

**Budget/stop/resume (strongest directly reusable mechanism).** Contract limits are
explicit for model calls, tool calls, tokens, minutes and USD; limits are authorized
from user text and stored as runtime state: [limits](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/backend/cli/src/tool/research-contract.ts#L212-L231).
At the finalization boundary the runtime disallows new optional work, preserves
partial Results/checkpoints, and tells the user to continue/resume. `/resume` starts
a fresh bounded runtime epoch from the existing contract/checkpoints, resetting only
that epoch’s counters and retaining prior state: [research.ts](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/backend/cli/src/session/research.ts#L1201-L1204),
[resume](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/backend/cli/src/session/research.ts#L1333-L1377).

## Mechanisms to evaluate for QMA (not design approval)

1. Test a **source identity → immutable snapshot → evidence reference** chain (Delphi).
2. Test a **hypothesis/protocol contract** with stages, required artifacts, checks,
   preregistration and typed evidence (OpenScience).
3. Test **per-completion fanout/selection** with bounded siblings and explicit repair,
   selection, refill and stop transitions (OpenResearch). Its experiment-selection
   use of “promote” is not QMA vocabulary: QMX reserves promotion for the human
   live-zone act. Do not import a universal tree shape or stopping threshold.
4. Measure budget accounting, partial-finalization and resume as first-class state;
   do not claim any mechanism is suitable for QMA until benchmarked against QMA’s
   workstation/Docker-worker constraints and existing Loop/GraphTemplate/Skill
   boundaries.

The protocols above are optional methods to learn from, not a mandatory QMX
research pipeline. QMA already has source evidence custody, ExperimentSpec and
bounded Loop/GraphTemplate/Skill concepts; adapt or extend those owners instead of
adding duplicate state stores. Protect evidence and comparison rules without
restricting ordinary Python exploration to the donors' templates. See
`feature-impact-register.md` for the local-document baseline and reconciliation
questions, including supervisor placement and research retrieval depth.

## Explicit limits

These findings are repository/documentation observations, not a performance claim;
no project was installed or executed. OpenResearch’s README/skills document the
experiment tree but do not establish a complete cost ledger. Delphi’s retrieval
quality numbers and OpenScience’s benchmark ambitions are not evidence that either
system improves QMA outcomes. Preserve QMA’s own contracts and terminology; borrow
only mechanisms that pass a focused experiment.
