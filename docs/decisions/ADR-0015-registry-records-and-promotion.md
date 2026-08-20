---
id: ADR-0015
title: Registry records, multiplicity, and the promotion skeleton
type: adr
status: provisional
component: COMP-QMF-REGISTRY
depends_on: [COMP-QMF-REGISTRY, COMP-QMF-CORE, COMP-QMF-DATA]
decisions: [DEC-0114, DEC-0115, DEC-0116, DEC-0121]
sources: [DEC-0114, DEC-0115, DEC-0116, DEC-0121, DEC-0034, DEC-0037, DEC-0108, DEC-0110, DEC-0120, EXT-2016, EXT-2017, EXT-2018, EXT-2023, EXT-2028, "_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md", "archive/qmf-3.txt"]
generated: 2026-08-20
verified: 2026-08-20
stale_after: 1y
---

# ADR-0015: Registry records, multiplicity, and the promotion skeleton

Date: 2026-08-20. Status: provisional — AD-16, AD-17, and AD-18 are operator-ratified 2026-08-20 in the reopened foundation architecture sitting; this document stays provisional until the knowledge base is re-ratified.

## Context

`qmf-registry` holds the identity and lineage of every artifact QMX produces, and three questions blocked it. Record shape: unlike objects — instruments, venues, accounts, datasets, results, Bots, Books — needed identity without being forced into one abstract schema, and an earlier universal all-fields card had already been rejected (DEC-0034), as had a graph database for V1 even though lineage is graph-shaped (DEC-0037). Cardinality: a stale ruling fixed a Bot at exactly one confluence, which would foreclose the experiments the operator wants. Promotion: nothing recorded a human's decision to move an artifact toward live money in a form that human could later be held to. The sitting ratified the three as AD-16, AD-17, and AD-18, and deferred the two research-governance mechanisms that sit next to them.

## Options considered

1. **Universal recipe card** — one all-fields schema for every registered object. Rejected as too abstract and too constraining for unlike domain objects (DEC-0034, dead); per-kind record schemas, each its own versioned contract sharing a tiny common header, were selected. The operator's frame was a retail catalog: a common core plus per-category attributes.
2. **Graph database for lineage** — rejected for V1 (DEC-0037, dead) even though lineage is graph-shaped; append-only typed edge records with local rebuildable indexes and no database server were selected.
3. **Minted stable ids** — a registry-assigned identifier per record. Rejected at the increment reviewer gate because two sandboxes doing identical work would mint two ids for one artifact; the stable id is derived from the record's `fp1` fingerprint instead, so identical work deduplicates by construction (DEC-0108).
4. **Created-at as an identity field** — rejected because a wall-clock stamp differs between two sandboxes doing identical work; created-at and other occurrence facts are declared occurrence or display-only, which is what lets identical records deduplicate (DEC-0110).
5. **Lineage carried in the record header** — rejected: readers would have to union header references with edges and would disagree about which was authoritative. At-birth parent references stay in the header as identity-bearing; everything that accrues after birth lives exclusively in edges.
6. **Free-form append files for edges** — rejected: the JSONL format is pinned so two implementations write the same bytes.
7. **A Bot contains exactly one confluence** — rejected; DEC-0040 is superseded. The operator generalized the answer rather than patching it: multiplicity is recursive at every layer of the bot vocabulary (DEC-0115).
8. **Bot identity including its Book or account binding** — rejected because re-binding paper to live would mint a new Bot and destroy comparability; Bot identity is its content and the binding is a separate dated record (DEC-0115).
9. **Cryptographic signatures for promotion** — rejected for V1 as an unnecessary dependency now; signing means the operator's recorded approval captured as an immutable occurrence attesting the record's `fp1` string, with cryptographic signatures left to the ops sitting (DEC-0116).
10. **The journal's promotion event as the promotion record** — rejected as a second schema for one fact; the registry card is canonical and the journal event carries only the card's fingerprint plus `correlation_id` (DEC-0116).
11. **Ratifying the look-ahead gate and attempt counter now** — rejected by the operator, who reads both as backtesting-entangled; both are deferred with the consequence knowingly accepted (DEC-0121).

## Decision

**Registry records and lineage.** The registry uses per-kind record schemas, each its own versioned contract, sharing a tiny common header: kind, contract format version, at-birth parent references that are identity-bearing, plus writer and sequence. A record's stable id is derived from its `fp1` fingerprint and is never minted; created-at and other occurrence facts are declared occurrence or display-only, so identical work from two sandboxes deduplicates. Lineage that accrues after birth — supersedes, promoted-from, occurrence-of, corroborates, disagrees-with — lives exclusively in append-only typed edge records referencing fingerprints, and readers never union header references with edges. Edge files are pinned JSONL: one `fp1`-canonical JSON object per line, LF-terminated, appended with fsync, never rewritten, rotated by size with a monotonic file ordinal; indexes are local and rebuildable. Kinds are addable and never redefined. Bot and Book are reserved kind names whose contents come from their own sittings. No database server exists. (DEC-0114)

**Multiplicity at every layer.** A Bot contains one-or-more confluences; a confluence contains one-or-more levels, triggers, and confirmations; components may compose, and a composite is its own artifact carrying lineage to its children. No layer of the bot vocabulary may hardcode exactly-one. Multiplicity collections are canonically ordered by child fingerprint ascending unless the owning contract explicitly declares the collection order-significant. Bot identity is its content; the Bot-to-Book-to-account binding is a separate dated binding record outside Bot identity — one Bot at exactly one Book at any time, and re-binding from paper to live never mints a new Bot, so paper and live performance stay comparable for alpha-decay sensing. Exits remain Book, risk, and node territory. (DEC-0115)

**Promotion record skeleton.** The registry reserves a promotion-occurrence card kind with a human-only signer, a signed immutable record, and a mandatory plain-words summary field explicitly declared an identity field — the signature attests the exact words the human read, so a typo fix mints a new record with a supersedes edge. V1 signing is the operator's recorded approval captured as an immutable occurrence attesting the record's `fp1` string with reviewer identity and instant; no cryptographic dependency is taken now. The registry card is canonical: the journal's `promotion` event carries only the card's fingerprint plus `correlation_id`, never a second schema. The evidence checklist accretes from later sittings — untouched-test proof from the data area, the causality slot from backtesting, risk binding from the risk sitting. The promotion gate itself — workflow, UI, timing — is platform territory outside QMF. (DEC-0116)

**Deferred research governance.** The look-ahead and causality registration gate and the attempt counter are deferred to the backtesting sitting, with the consequence knowingly accepted that artifacts registered before then carry no causality evidence and that this evidence is not retroactively reconstructible. The bitemporal ingredients — event time versus knowledge time — remain ratified, and registry occurrence records still log every run, so the tally's raw material accrues without a policy that reads it. (DEC-0121)

- `GAP(GAP-0016): what exact causality and look-ahead registration test must an artifact pass, and what evidence proves the pass?` — deferred to the backtesting sitting (DEC-0121), not closed.
- `GAP(GAP-0017): what does the attempt counter count, at which scope, when does it reset, and how does it constrain registration or research budget?` — deferred to the backtesting sitting (DEC-0121), not closed.

## Consequences

Sandbox merges become an ordinary operation rather than a reconciliation problem: two agents that computed the same artifact write the same id and the same bytes, and the idempotent-rewrite rule accepts it silently. Lineage stays queryable without a server, at the cost of rebuilding local indexes after a crash and of edge files that only ever grow. Per-kind schemas mean every new kind is a new versioned contract with its own conformance suite, so adding a kind is deliberate work rather than a field addition. The recursive multiplicity rule forbids convenience shortcuts throughout the future Bot and QML vocabulary — no layer may assume one child even where one is the common case. The promotion summary being an identity field means the human-readable sentence cannot be edited after signing, which is the point and also a papercut. Two consequences are open by ruling rather than by omission: artifacts registered before the backtesting sitting carry no causality evidence, and no attempt budget constrains research until that sitting defines one.

## Blast radius

- **Component specs:** COMP-QMF-REGISTRY carries record header, id derivation, edge files, kind catalog, multiplicity, and the promotion card; COMP-QMF-CORE supplies the fingerprint implementation, `WriterId`, and the shared nouns whose records the registry owns; COMP-QMF-DATA holds the registry room and the append-store the registry writes through (DEC-0120, ADR-0016); COMP-QMF-RISK and COMP-QMF-STRUCTURE consume Bot, Book, and composite records once their sittings define them; COMP-QMF-INDICATORS and COMP-QMF-VENUE register their results and venue records through the same header.
- **Contracts:** CT-06 registration, CT-07 lineage edge, CT-09 registry persistence are filled by this ruling; CT-08 gate evidence holds the promotion skeleton and stays partial until the evidence checklist accretes; CT-11 evidence persistence and CT-13 journal carry the storage and event side.
- **Registry:** `registry:registry_attempt_scope`, `registry:registry_attempt_budget`, `registry:registry_attempt_reset_policy` stay unset and marked deferred against GAP-0017 (DEC-0121); `registry:result_identity_key` and `registry:canonical_hash_algorithm` govern the derived stable id.
- **Downstream sittings:** the Bot and QML schema session, the risk sitting, and the backtesting sitting all inherit the reserved kind names and the multiplicity invariant.

## Architecture preflight

Verdict: **reuse**. No new component, no authority shrink. COMP-QMF-REGISTRY gains fully specified record, lineage, and promotion-card shape it was already declared to own; COMP-QMF-CORE keeps the fingerprint and noun definitions; COMP-QMF-DATA keeps storage authority and gains the registry room through the ratified edge in ADR-0016. No component's prohibitions change: the registry still stores no market data itself and still runs no promotion gate.
