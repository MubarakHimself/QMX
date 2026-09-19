# Docs-versus-spine drift: Workflows construction kit

Scope: independent comparison of `ARCHITECTURE-SPINE.md` AD-23..AD-31 and `CONTRACTS.md` against ADR-0024, SCN-0018..SCN-0022, and the dated rider. This is a documentation audit only. OD-01 remains closed; the rider/ADR correctly record that the focused Codex recheck was skipped and must not be represented as approval.

## Material findings

1. **No direct semantic contradiction was found in the golden scenarios or rider.** Their operational statements generally agree with the spine. The principal drift is omission/compression: ADR-0024's AD-23..AD-31 bullets do not carry the complete contract surface. The ADR says the spine is adopted in full (`ADR-0024`, §“Adopted decisions”, lines 39, 63-71), but the bullets are not a substitute for `CONTRACTS.md`.

2. **AD-23 / DEC-0448 is safe but under-specified in ADR.** Spine `ARCHITECTURE-SPINE.md`, §AD-23 requires closed AccountingPolicy and RiskPolicy semantics, command binding, selected-composition adoption by QML/QMB/MIS/QMN, distinct `composition_fp`s, and evidence/compare rules. ADR-0024 §AD-23 (line 63) records completeness, admission, evidence, QMN ownership, and dummy prohibition, but omits the policy field obligations, command target binding, “consumer must not remain Book-shaped”, distinct composition/version fencing, and conserved-measure comparison. SCN-0020 lines 23-69 covers the main ATC path and L36; it still does not enumerate the closed policy fields. **Desk fix:** add a short pointer to `CONTRACTS.md` §11 and explicitly state that Book/BMS are defaults, not required dummy records; retain DEC-0448 wording exactly.

3. **AD-24 contract fields are materially compressed.** Spine AD-24 and `CONTRACTS.md` §1b/§3b require caller/callee `psess` refs, `op_id`/version, grant snapshot, effect class, reconcile policy, input hash, and effect-specific retry rules; GrantRecord also has audience, parameter ceiling, account scope, expiry/revocation, and context-revision regrant semantics. ADR-0024 §AD-24 (line 64) only names a subset. SCN-0021 lines 23-25 carries most envelope fields but not the complete GrantRecord. **Desk fix:** cross-reference `CONTRACTS.md` §§1b, 3b, 13 and state that the prose bullet is non-exhaustive.

4. **AD-25 omits required fencing evidence.** Spine AD-25 and `CONTRACTS.md` §10 require epoch/token, account/venue/composition, typed positions/orders snapshots, residual disposition, predecessor acknowledgement, timeout/escalation, immutable completion evidence, and stale-token refusal. ADR-0024 §AD-25 (line 65) records only owner/state machine and broad applicability; SCN-0020 covers the transition and stale predecessor but not the complete record schema. **Desk fix:** add a `CONTRACTS.md` §10 pointer and the typed-snapshot/residual-evidence requirement.

5. **AD-26 scenario is strong, ADR is abbreviated.** `CONTRACTS.md` §6 and spine AD-26 also require durable `edges:{from,to,mapping}`, handle `logical_run_id`/`attempt_id`, artifact completeness states, first-terminal-wins behavior, partition/key/watermark/late-arrival algebra, and partial retry rules. ADR §AD-26 (line 66) says transaction/outbox, parent vocabulary, and broad join policies only. SCN-0021 lines 23-67 correctly preserves timeout→`unknown`, no second scheduler, and idempotent replay. **Desk fix:** add the missing handle/join invariants or an explicit §6 citation.

6. **AD-27/28/29/30/31 are summary-only in ADR and scenarios.**
   - AD-27: ADR line 67 omits owner fence/content hashes, cross-store reference verification, orphan quarantine rationale, and post-restore external-effect reconciliation (`ARCHITECTURE-SPINE.md` §AD-27; `CONTRACTS.md` §13).
   - AD-28: ADR line 68 omits cursor, event/receive times, cutover watermark, bounded buffer/backpressure, gap/duplicate/late evidence, heartbeat, and cancellation/refcount behavior (`CONTRACTS.md` §7).
   - AD-29: ADR line 69 omits mutation result variants and change-request base hashes, source instance/config, context revision, request hash, typed patch, validation status, and apply evidence (`CONTRACTS.md` §4; `SCN-0019` lines 23-62 covers authority boundaries but not the full payload).
   - AD-30: ADR line 70 omits failed migration rollback, dependant naming, in-flight byte retention, and the scanner's private-path/transcript/typed-ref checks (`CONTRACTS.md` §8; `SCN-0022` lines 23-64 covers lifecycle honesty).
   - AD-31: ADR line 71 omits the complete temporal/unit/licensing/provenance/transform/split/environment/output schema and preview/export/stream distinction (`ARCHITECTURE-SPINE.md` §AD-31; `CONTRACTS.md` §12). No SCN-0018..22 scenario covers recipe schema.
   These are omissions, not contradictory rules; desk-fix by adding section citations and an explicit “full schema in CONTRACTS” qualifier.

7. **Scenario coverage is intentionally incomplete.** SCN-0018 covers ContributionHit pin/disable honesty; SCN-0019 app-use boundaries; SCN-0020 ATC/L36/fencing; SCN-0021 outbox/JobHandle; SCN-0022 pack lifecycle/headless parity. None is a full AD-27, AD-28, or AD-31 contract test. Do not infer coverage from the ADR's “golden docs scenarios” statement (`ADR-0024` line 25).

## L36 / DEC-0448 checks

The folded docs preserve the required semantics: L36 remains **bot → Book → BMS → operator as the default authority chain**; Book/BMS are default implementations, not the only possible accounting/risk implementations; a complete PolicyPair may occupy those roles; dummy Book/BMS/PolicyPair is `INVALID_INPUT`; human L17 promote, sequential paper-then-live, and QMN as sole venue importer remain. See rider lines 41, ADR-0024 §AD-11/AD-23 and DEC-0448, and SCN-0020 lines 17-31, 47-57. No L36 contradiction found.

One wording hazard remains: ADR line 39 says AD-1..AD-31 are “adopted in full”, while DEC-0447 says the focused Codex recheck of AD-23..AD-31 was skipped. This is adoption of the architecture sitting, not Codex verification. The ADR line 25 and rider line 20 correctly preserve that distinction. **Desk fix:** qualify “adopted in full” as “documentation-factory adoption; not Codex recheck approval.”

## OD-01 / DEC-0447 preservation

OD-01 is correctly closed (`ADR-0024` line 25; rider lines 19-21). Do not change the record to “rechecked”, “approved”, or “verified”. The packet's scenarios are specifications, not executed proof; DEC-0450 absence claims at `integration@270e992` remain intact (ADR lines 23, 77; SCN-0019 line 19; SCN-0021 line 19; SCN-0022 line 64).

## Recommended desk fixes (no production edits)

- Add explicit `CONTRACTS.md` section citations to each ADR AD-23..AD-31 bullet and state that the bullet is a summary.
- Add a compact appendix/table listing the omitted contract invariants above, especially AD-23 policy fields, AD-24 GrantRecord, AD-25 evidence, AD-26 join algebra, AD-28 backpressure, and AD-31 recipe schema.
- Keep DEC-0448/L36 language and dummy refusal unchanged; do not introduce a new COMP/CT or turn `ContributionHit`/sessions/outbox/ATC into implemented claims.
- Keep the focused recheck marked skipped and OD-01 closed.
