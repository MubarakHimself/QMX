# Grok desk-fix handoff

## Gate result

The machines are **close but not architecture-complete as written**. Repair is bounded to the Stage C candidate and already-folded docs. Do not reopen Pass I or OD-01; do not implement; do not rerun Documentation Factory.

## Repair order

1. **Fix normative identity and authority first.** Amend AD-23/24/29/31 and contracts for composition/PolicyPair identity, authoritative envelope/grant revalidation, canonical hash/key domains, immutable ChangeRequest plus separate validation/apply records, and recipe identity/lineage (RC-01..RC-05, RC-11..RC-12, RC-15).
2. **Finish durable machines.** Amend AD-25..28 contracts for fence attempt/reconcile, receiver-side outbox dedupe, graph/join identity, checkpoint generation/consistent cut/bootstrap, and stream control/evidence/leases (RC-06..RC-10).
3. **Finish lifecycle and public surface.** Correct the AD-2 manifest shape; add package transition/migration/lease/GC/scan-report records; complete the AD-3 descriptor; make supported doors per `op_id` (RC-13..RC-17).
4. **Reconcile ledgers and folded docs.** Remove stale OD-01 conditional text; update ADR-0024's skipped-recheck status without claiming Codex approval; repair SCN-0019..22 as listed in `DOCS-DRIFT.md`; update stale addendum/status prose.
5. **Run a focused document consistency check.** Verify every normative field appears in its representative schema, every schema uses the same identity vocabulary, every transition has a durable key/guard/evidence, and no doc says this return ratified the candidate.

## Exit criteria before epics resume

- All RC-01..RC-17 have an explicit fix or a clearly named deferred implementation concern that does not leave architecture behavior ambiguous.
- AF-01..AF-19 are re-dispositioned against corrected text; AF-20 remains claim-honest.
- OD-01 is nowhere presented as an open choice.
- `CONTRACTS.md` either is schema-complete as claimed or labels fragments honestly and points to the normative complete schema.
- ATC selection, evidence, admission, fencing, and adoption share one immutable composition/PolicyPair identity.
- Retry/restart behavior is decidable for invocation, grant revocation, fence, outbox, join, checkpoint, stream, session CAS, package lifecycle, and recipe release.
- The original 85 scenario IDs remain unchanged; any new acceptance examples supplement them rather than rewriting Pass I.
- ADR-0024 / SCN-0018..22 no longer overclaim the current contracts and do not claim Codex ratification.

When these conditions hold, Grok can resume epics without another discovery pass. A short diff-only consistency recheck is advisable if the repair changes machine semantics; it need not be another Pass I.
