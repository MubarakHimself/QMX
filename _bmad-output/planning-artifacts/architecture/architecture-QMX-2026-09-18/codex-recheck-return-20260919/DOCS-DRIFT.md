# Docs-vs-spine drift recheck

## L36

No direct semantic reversal of the operator's closed L36 amendment was found in the supplied folded pages. `SCN-0020:29` correctly states that bot → Book → BMS → operator is the default authority chain, that Book/BMS are replaceable implementations rather than the ceiling, and that QMN remains the only venue importer. `SCN-0020:37-53` also preserves adoption, sequential fencing, paper-then-live, and L17.

The drift is in surrounding Stage C working documents: `CHALLENGE-RECONCILIATION.md:60,92,120` and `CONFLICT-REGISTER.md:33` still make the ATC/L36 outcome conditional on a live OD-01 choice. That conflicts with `CODEX-RECHECK-HANDOFF.md:21,28-32` and must be removed without reopening the decision.

## ADR-0024

1. **Process status is stale.** The ADR says focused Codex recheck was skipped (`docs/decisions/ADR-0024-workflows-construction-kit.md:25,74`). This recheck now exists. Replace that statement with a citation to this return and its “repairs required; not ratified” disposition.
2. **Adoption language is too unconditional.** The ADR says the spine was adopted in full (`ADR-0024:39`) while its frontmatter is `ratified` (`ADR-0024:5`). The docs fold may be ratified as the current documentation authority, but it must not imply Codex approval of AD-23..31. Preserve the explicit honesty sentence at `ADR-0024:116` and qualify the new-machine sections as subject to the focused recheck repairs.
3. **Machine summaries are lossy.** `ADR-0024:63-71` is directionally aligned but does not carry the durable keys and evidence now found missing in RC-01..RC-15. After the spine/contracts are repaired, update the summary or link normatively to the corrected schemas rather than copying a second, smaller machine.
4. **A1-A6 require amendment, not deference.** The field catalogues at `ADR-0024:124-129` are sitting machinery, not operator-spoken schemas. A1 (PolicyPair), A3/A4 (package/export), A5 (recipe), and A6 (checkpoint) must absorb the corresponding findings.

## Folded scenarios

### SCN-0018 — Contribution-hit honesty

Directionally aligned. After the package fix, ensure its manifest examples use AD-2 `{point, local_id}` entries and that pin/invoke describes the corrected availability/roster generation semantics. Do not imply that a pin is a grant.

### SCN-0019 — App-use change request

The scenario currently describes validation and later apply evidence as fields of one payload. That mirrors the ambiguity in AD-29. Split immutable request, validator result, and append-only apply record; pair each target ref with its base hash and define the request hash preimage. Preserve the central rule that app-use mints but cannot apply implementation edits.

### SCN-0020 — Two trading compositions

The behavior is aligned with closed OD-01. The frontmatter assigns `component: COMP-QMF-RISK` (`SCN-0020:6`) even though the ADR architecture-preflight entry says QMB/QML/QMN own the new PolicyPair path and QMF-RISK supplies default shapes only (`ADR-0024:91`). Use the actual architecture owner or a neutral cross-component owner; do not make QMF-RISK the owner of all ATCs. Add the corrected composition/PolicyPair identity and authoritative admission evidence from RC-01/RC-02.

### SCN-0021 — Outbox / JobHandle

JobHandle vocabulary is correct. The statement “exactly one logical B” (`SCN-0021:17,39`) is stronger than the current outbox contract can prove. Retain it as the required outcome only after the contract adds a unique dispatch identity, durable receiver acceptance/dedupe, and effect-result replay. Otherwise say at-least-once dispatch with exactly-once logical acceptance/effect under the receiver ledger.

### SCN-0022 — Package lifecycle / headless

Its per-`op_id` door rule (`SCN-0022:27`) is correct and exposes drift in the owner-wide contract matrix. Its scanner language “prove absence” (`SCN-0022:44`) needs a bounded threat model and a versioned scan report rather than an unqualified universal proof. Add lifecycle generation/migration/pin-lease details from RC-13/RC-14.

## Other stale fold metadata

- `REQUIREMENTS-ADDENDUM.md:4` still says Documentation Factory was not issued, contradicting the recheck handoff's completed-fold status.
- `CHALLENGE-RECONCILIATION.md:442-450` still says the recheck was skipped and Documentation Factory is next. Replace with this focused result and keep epics paused until repair.

These are desk edits. They do not justify rerunning Documentation Factory.
