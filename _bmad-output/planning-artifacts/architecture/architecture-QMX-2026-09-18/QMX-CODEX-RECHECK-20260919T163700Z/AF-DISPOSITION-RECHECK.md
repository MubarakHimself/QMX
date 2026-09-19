# AF-01..AF-20 disposition recheck

“Open” below means the Stage C architecture/contract disposition is not yet complete. It does not mean the candidate must be implemented before epics. “Holds” means the stated honesty/control disposition remains valid.

| AF | Recheck status | Reason / controlling finding |
|---|---|---|
| AF-01 | **Open** | ATC now exists, but its stable identity and authoritative admission proof do not: RC-01, RC-02. The ledger also still calls it deferred on OD-01 despite OD-01 being closed (`CHALLENGE-RECONCILIATION.md:88-95`). |
| AF-02 | **Open** | Envelope exists, but key scope/canonical binding, nested-call identity, descriptor/grant revalidation, and replay horizon remain unspecified: RC-03, RC-04. |
| AF-03 | **Open** | Sequential fencing exists, but the ATC contract omits owner epoch/admission evidence and the fence payload/state machine is incomplete: RC-02, RC-06. |
| AF-04 | **Open** | Transactional outbox is specified, but receiver-side dedupe and ack/effect semantics are absent: RC-07. |
| AF-05 | **Open** | Invocation identity does not yet bind authoritative descriptor/grant resolution or nested/delegated calls: RC-03, RC-04. |
| AF-06 | **Open** | Recipe identity is named, but canonical hash inputs and complete definition schema/lineage are absent: RC-15. |
| AF-07 | **Open** | `unknown-blocked` intent is sound, but reconcile creates no defined new attempt/epoch/evidence and the transition chain is ambiguous: RC-06. |
| AF-08 | **Open** | Stream intent is broad, but cutover, lease, gap/duplicate/late evidence and reconnect are not contract-complete: RC-10. |
| AF-09 | **Open** | Session CAS exists, but command dedupe namespace/retention, in-flight duplicate, and cursor compaction/resync are absent: RC-11. |
| AF-10 | **Open** | Grant snapshot exists, but immutable grant vs `revoked_at` and in-flight expiry/revocation semantics are unresolved: RC-05. |
| AF-11 | **Open** | Lifecycle/pin direction is correct, but transition, migration, dependency, retention, and scan-proof contracts are incomplete: RC-13, RC-14. |
| AF-12 | **Open** | Join vocabulary exists, but durable graph/edge/join identity and deterministic `first-wins` are missing: RC-08. |
| AF-13 | **Open** | Checkpoint manifest exists, but it lacks a consistent cut, generation, prepare/commit outcomes, backup refs, and bootstrap/recovery protocol: RC-09. |
| AF-14 | **Open** | Change requests cite bases, but hash authority and immutable request vs validation/apply evidence are not separated: RC-12. |
| AF-15 | **Open** | Availability revision is named, but atomic lifecycle/roster and in-flight byte-retention/GC records are not contract-complete: RC-13, RC-14. |
| AF-16 | **Open** | The operation descriptor is still incomplete while labelled schema-complete: RC-16. |
| AF-17 | **Open** | The UI payload has no normative event/progress/reconnect/resync protocol; per-op behavior is not demonstrable from `CONTRACTS.md:417-442`. |
| AF-18 | **Open** | The headless matrix is owner-wide rather than per `op_id`: RC-17. |
| AF-19 | **Open** | Recipe definition/release separation exists, but the contract omits normative fields and executable lineage: RC-15. |
| AF-20 | **Holds / closed as a claim-honesty control** | Spine/docs consistently state the machines are proposed and not implementation evidence (`ARCHITECTURE-SPINE.md:288`; `docs/decisions/ADR-0024-workflows-construction-kit.md:23`; SCN-0018..0022 implementation-status paragraphs). Implementation remains unproven by design, but that is not an architecture disposition defect. |

## Ledger correction required

The Stage C reconciliation ledger is internally inconsistent:

- It records OD-01 as closed (`CHALLENGE-RECONCILIATION.md:31-33`, `53-74`).
- It still conditions venue ATC on a future OD-01 amendment and marks AF-01/AF-03 venue ATC deferred (`CHALLENGE-RECONCILIATION.md:60`, `92`, `120`).
- `CONFLICT-REGISTER.md:33` likewise says L36 is weakened only if the operator chooses option A, although the handoff says L36 already received named amendment DEC-0448.

Delete the live conditional/deferred wording; preserve the closed operator meaning. This is a reconciliation correction, not an invitation to re-ask OD-01.
