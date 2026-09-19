# Staged execution and independent challenge contract

## Why the split exists

The operator explicitly wants broad autonomous exploration, installed BMAD architecture work, a separate Codex scenario/challenge session, and Grok reconciliation. This is deliberate separation of design and challenge, not evidence that either model is unable to reason or a claim that disagreement automatically improves quality. Judge findings by evidence and observable behavior.

## Stages and exits

| Stage | Owner | Required outcome | Stop/state |
|---|---|---|---|
| R, optional | Codex/browser-capable agent | Evidence-backed external product journeys | REFERENCE-RECON-RETURN.md; no changes to QMX |
| A | Grok | Fresh exploration plus complete internally reviewed BMAD architecture candidate | AWAITING_CODEX_CHALLENGE |
| B | Independent Codex session | Requirements-derived scenarios and design-specific counterexamples with coverage report | CHALLENGE_RETURNED, or a clearly bounded missing-input report |
| C | Grok | Reconciled architecture, retested affected assumptions, final technical status and Documentation Factory handoff | READY_FOR_DOCUMENTATION / READY_WITH_EXPLICIT_LIMITS / BLOCKED |
| D | Manually launched Documentation Factory | Its own thorough validation/integration according to installed skill and delegation | Epics/stories handoff or explicit blockers |
| E | Existing later workflow | Epics/stories, implementation, tests and later UI work | Existing pipeline controls |

These status labels describe proposed handoff states; they do not invent QMX runtime schema enums.

## Autonomous work, not continuous questioning

Use as many relevant subagents/dynamic workflows as supported. Investigators own bounded questions and evidence; the lead resolves cross-cutting choices. Keep a durable index and decisions so context compaction or session continuation does not lose work. Do not ask the operator routine technical questions or expect them to inspect schemas. Follow the installed skill's fast/autonomous conventions. Record assumptions, then present only real unresolved product/access/cost choices together at the stage end. Lack of approval for an external side effect is not overcome by an assumption.

Grok's own BMAD reviews remain mandatory. The Codex session adds an independent challenge; it does not replace those reviews. Documentation Factory later performs its own installed checks and routing, including returning issues or correcting them where authorized. We have not read the user's custom Documentation Factory skill here: each launched agent must discover and read it locally. Do not impose a fictional generic skill procedure.

## Stage A candidate freeze

Do not hand Codex only a vague outline. Provide the integrated spine, requirements, assumptions, proposed public interfaces, ownership/process/data boundaries, lifecycle/state transitions, compatibility/migration strategy, selected stack rationale, failure handling, example payloads and existing internal review findings. Incomplete parts remain explicitly marked; unanswered foundational questions cannot be hidden in placeholders.

Create `ARCHITECTURE-CANDIDATE-MANIFEST.json` with a stable candidate ID, UTC timestamp, exact source/worktree commits, dirty-state evidence if applicable, file hashes, scope and exclusions. Hashes identify this reviewed snapshot; they are not product fingerprints or cryptographic approval.

Create `CODEX-CHALLENGE-INPUTS.zip` with a short README, manifest, transcript/input locations, current requirements, candidate architecture/contracts, evidence, existing scenarios, reviews and `12-CODEX-SCENARIO-AND-ARCHITECTURE-CHALLENGE.md`. Omit secrets, caches, node_modules, venvs and unrelated personal files. If the full transcript cannot legitimately be copied, list its exact required attachment. Ensure paths in the handoff resolve in the transferred package.

Create `RESUME-STATE.md`: decisions made, sources read, uncertain findings, current workspace state, tests performed, files produced and exact resumption steps. Mark candidate `awaiting independent challenge`, never final merely because the internal review passed.

## Stage B review independence

Use two passes in a fresh Codex session. First derive candidate behaviors and hazards from operator intent, current public domain meanings and actual evidence without reading the proposed solution. Freeze that initial scenario list. Then read the candidate architecture and generate design-specific counterexamples, interface/state traces and coverage gaps. Existing scenario seeds are baseline coverage, not a limit.

Scenario oracles must describe what must be observably true and why. Distinguish requirements, present implementation, proposed behavior and reviewer recommendations. A current implementation limitation is not a reason to delete the operator's target. A new reviewer wish is not automatically a requirement.

## Review dispositions and material-change control

For each finding, Stage C records: finding/scenario IDs; accepted/rejected/deferred/duplicate/blocked disposition; rationale; exact design changes; affected requirements/contracts; evidence or planned implementation check; residual risk. Reject claims with counterevidence, not authority or model reputation.

Check the candidate hash and repository baseline on resume. If current work differs, record a delta. A reviewer result cannot silently approve files it never reviewed. Material changes to permissions, persistence, risk/account control, cross-app contracts, dependency/runtime semantics or the stack need a focused independent challenge of the delta. Minor editorial changes do not require a full new campaign. Prepare a concise recheck package and stop for that handoff only when needed.

Before a ready status, every blocker has either been fixed with appropriate design evidence or remains an explicit blocker. A deferral requires scope and consequence; marking an item deferred must not relabel an unsafe intended path as complete. Nonblocking future scenarios may remain outside the first increment, with traceability.

## Required behavioral trace chain

Operator intent / user goal → requirement → scenario → relevant invariant → contract/state/owner → observable result → intended implementation test → future UI journey. Existing names and meanings matter, but current accidental couplings must remain challengeable.

Each model should deliver at most a short operator routing summary plus exact file locations. The operator transfers packages, chooses only consequential unresolved options, and launches the next session; they are not the technical test oracle.
