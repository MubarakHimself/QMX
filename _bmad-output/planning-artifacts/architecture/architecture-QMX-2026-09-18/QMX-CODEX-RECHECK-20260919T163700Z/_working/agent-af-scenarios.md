# AF / Stage-C scenario audit

Scope: audit of `CHALLENGE-RECONCILIATION.md` AF-01..AF-20 against the packet's AD-23..AD-31 material, `CONTRACTS.md`, and the preserved scenario catalog. This is a trace audit, not an implementation claim and does not modify canonical packet files.

## Overall finding

No AF item is fully closed as an evidenced behavior. AF-01 through AF-19 are **partially closed**: each has a candidate design/contract disposition, but the reconciliation explicitly says statuses are requirement-to-design trace, not implemented behavior (CHALLENGE-RECONCILIATION.md:424), and the new AD-23..AD-31 machines are “not evidenced” (same file:440). AF-20 is **open** for the integration question: it correctly records P2-INT-001 as unsupported and all other scenarios as specified-not-executed (CHALLENGE-RECONCILIATION.md:348-357; 438-440).

The apparent “closed” language is limited to transcript/operator decisions (for example OD-01 and C-05), not proof that the AF requirement works. The document itself says the sitting is not ready for operator acceptance (CHALLENGE-RECONCILIATION.md:442-450).

## AF dispositions

| AF | Audit status | AD / contract trace | Proof or hole |
|---|---|---|---|
| AF-01 | Partial | AD-23; CONTRACTS §§11–12 | Alternative Trading Composition and PolicyPair are specified, but venue-touching is deferred to OD-01 and no end-to-end evidence is supplied. |
| AF-02 | Partial | AD-24; CONTRACTS §§1b, 6 | Invocation/idempotency/reconcile fields are specified; no timeout/retry execution proof. |
| AF-03 | Partial | AD-25; CONTRACTS §10 | Owner fencing/restart rule is specified; implementation and stale-predecessor proof remain absent. |
| AF-04 | Partial | AD-26; CONTRACTS §9b | Outbox semantics are designed; durable edge behavior is explicitly still absent at the pin (CHALLENGE-RECONCILIATION.md:430). |
| AF-05 | Partial | AD-24; CONTRACTS §1b | Contribution/pin/unavailability design is present; current wire union remains two-class and implementation is deferred. |
| AF-06 | Partial | AD-31; CONTRACTS §5 | Recipe temporal/unit/licensing/environment schema is amended; no metamorphic/runtime evidence. |
| AF-07 | Partial | AD-26 JobHandle clause; CONTRACTS §6 | Unknown/reconcile vocabulary is connected to JobHandle; no integration execution evidence. |
| AF-08 | Partial | AD-28; CONTRACTS §7 | Stream protocol is specified; no provider/venue stream conformance run. |
| AF-09 | Partial | AD-29; CONTRACTS §3 | Session CAS semantics are specified; runtime is absent (CHALLENGE-RECONCILIATION.md:431). |
| AF-10 | Partial | AD-24 GrantRecord; CONTRACTS §3b | Grant binding is designed; no grant/revocation execution proof. |
| AF-11 | Partial | AD-30; CONTRACTS §8 | Lifecycle/pin behavior is specified; scanner/runtime evidence absent. |
| AF-12 | Partial | AD-26 join clause; CONTRACTS §9c | Join algebra is specified; durable workflow edges remain unproven. |
| AF-13 | Partial | AD-27; CONTRACTS §13 | Checkpoint/resume design is present; no resume execution evidence. |
| AF-14 | Partial | AD-29; CONTRACTS §4 | Change-request/session binding is specified; runtime absent. |
| AF-15 | Partial | AD-30; CONTRACTS §2 | Pin/tombstone/invoke rule is designed; no disable-after-pin proof. |
| AF-16 | Partial | AD-3 plus CONTRACTS §§1, 7 | Schema-complete examples are amended; conformance is a proposed test, not a result. |
| AF-17 | Partial | AD-17; CONTRACTS §14 | UI DTO/authority rules are specified; host stack/chrome remains deferred. |
| AF-18 | Partial | AD-21; CONTRACTS §15 | Door matrix is specified; unsupported-door/integration tests are not evidenced. |
| AF-19 | Partial | AD-31; CONTRACTS §5 | Complete data-recipe schema is specified; temporal/licensing metamorphic tests are not run. |
| AF-20 | Open | ledger / implementation-sequence / testing plan | It expressly preserves P2-INT-001 as unsupported and all other scenarios as specified-not-executed; this is a status guard, not closure. |

## Scenario preservation / traceability

`SCENARIO-CATALOG.jsonl` has 86 JSONL records: one schema header plus 85 scenario objects, with unique IDs. The reconciliation claims “Preserve all 85 scenario IDs” (CHALLENGE-RECONCILIATION.md:47), and no catalog record is deleted or duplicated. However, expanding the AF scenario cells yields only 74 distinct IDs. The following 11 catalog IDs are not named in any AF-01..AF-20 scenario cell:

`P1-MKT-004`, `P1-PLC-001`, `P1-PLC-002`, `P1-SES-006`, `P1-SKL-001`, `P1-SKL-002`, `P1-SKL-003`, `P1-SKL-004`, `P1-WF-001`, `P1-WF-002`, `P1-WF-005`.

This is a ledger traceability hole, not catalog loss: all 11 are present in `SCENARIO-CATALOG.jsonl` and each has a corresponding `Scenario:` in the packet feature files (`catalog-completion.feature`, `placement-and-recovery.feature`, or `workflows-and-sessions.feature`). Conversely, every ID named by an AF row resolves to a catalog ID; there are no AF references to nonexistent IDs.

## Conclusion

The Stage-C artifact is internally coherent as a proposed design update, but it overstates closure if “closed” means proven behavior. Mark AF-01..AF-19 partial and AF-20 open pending the focused AD-23..AD-31 recheck/integration evidence. Add an explicit AF-to-scenario coverage index or rows for the 11 currently unreferenced P1 scenarios before acceptance; do not treat their presence in the catalog/features as proof of execution.
