# Grok Stage C: reconcile Codex challenge and finalize architecture

Resume the QMX architecture assignment using the installed `bmad-architecture` skill. Read the actual installed skill and existing resume state. Inputs: original Stage A candidate and manifest, current full transcript, Codex challenge ZIP, optional product reconnaissance, this handoff package, and the current repository/worktree evidence. No production implementation is authorized.

## Re-establish what was reviewed

Verify the candidate identity/file hashes reviewed by Codex. Read `RESUME-STATE.md`. Resolve current source refs and dirty/concurrent work without altering it. Separate changes since Stage A from findings about the reviewed candidate. The audit's old 8510c03 baseline and the newer-code correction remain historical evidence, not latest HEAD assertions.

Read `CODEX-CHALLENGE-RETURN.md`, scenario catalog, BDD files, coverage gaps, findings, diagnostic logs and reconciliation handoff. Treat Codex as an independent reviewer, not an infallible approval source. Verify consequential assertions and use subagents/dynamic workflows freely where beneficial.

## Resolve rather than summarize

Create `CHALLENGE-RECONCILIATION.md` with one disposition per finding: accepted/fixed, rejected with counterevidence, duplicate, explicitly deferred with scoped consequence, or unresolved/blocking. Preserve finding/scenario IDs, impacted requirement/decision/contract, exact change, evidence, and remaining test obligation. Do not silently drop or rewrite a scenario to make the design pass. A proposed new requirement needs an explicit disposition, not automatic scope inflation.

Revise the integrated architecture, requirements addendum, proposed contracts, owner/stack decisions, persistence/compute/rollout plans, migration sequence, skill/hook design and UI-readiness/user-journey maps together. Prove cross-document consistency. Reuse actual QML/QMA work and preserve current Book/BMS behavior as a regression baseline while enabling legitimate alternatives.

Rerun the installed BMAD architecture skill's applicable reviews and bounded diagnostics. Explain discrepancies in state-machine meaning, permission propagation, file/API/stream semantics, app composition, dependency versions, provider/account isolation and lifecycle readiness. Source, diagnostic-model execution, real current tests and future tests retain distinct evidence labels.

## Material-change recheck

If repairs materially alter previously challenged contracts (especially permissions, account control, persistence/restore, cross-app interoperability, policy interfaces or runtime/dependency selection), package only the relevant changes and scenarios for a focused independent Codex recheck. Do not claim the original review approved the new design. Return the exact recheck prompt/artifacts and stop at that deliberate boundary. Do not reopen all discovery for editorial changes.

## Delegation and final output

The operator does not routinely review technical artifacts. Complete delegated technical choices yourself using the installed skill. Do not impose blanket manual approval of every document; do not invent a human signature or permission for external side effects. Group genuinely unresolved business/product/access choices at the end, with recommendations and consequences.

Only after reconciliation, deliver final technical status, the required outputs in `09-OUTPUTS-AND-NEXT-STAGE.md`, the review/coverage ledger and exact next-session Documentation Factory prompt. In that prompt direct the model to read its installed Documentation Factory skill, the exported architecture-session transcript, final architecture, evidence and review disposition package. Let the skill route further checking and documentation work under actual delegation. Flag unresolved consequential decisions rather than silently converting them into ratified law. Require the later epics/stories handoff and do not launch those sessions yourself.

Final status must distinguish technical architecture readiness from implemented or operational readiness. A ready architecture is not a tested desktop, functioning broker connection, trained model or live-money authorization. Provide exact file paths and an operator summary under about 350 words: outcome, substantive changes, remaining genuine decisions/blockers, evidence limits, and the next manual launch step.
