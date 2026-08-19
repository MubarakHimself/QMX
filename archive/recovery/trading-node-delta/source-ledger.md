# Source and authority ledger

## Comparison frame

| Layer | Role in this recovery | Authority treatment |
| --- | --- | --- |
| Public GitBook | Older baseline to compare against; inspected live on 2026-08-15. Its latest visible changelog entry was 2026-07-08. | Primary evidence for what is already public; it is not evidence that a later ambiguity remained unresolved. |
| Immutable GitBook capture, 2026-07-18 | Local page-level cross-check and recursive reference source. | Baseline reference only. The detailed baseline inventory deliberately cites the live GitBook, not this capture. |
| Active local wiki | Primary later documentation source and operator-ratified reconciliation layer. | Evaluate authority claim by claim. Page-level `draft` is a review warning, not automatic demotion of ratified behavior quoted inside it; proposed, inconsistent, schema-empty, or unlogged claims remain open. |
| Architecture Spine / planning artifacts | Source layer from which much of the active wiki was reconciled. | Governs architecture where the wiki cites it and no later operator ruling conflicts. |
| Completed BMAD stories and machine-readable standards | Later implementation/proof decisions, some newer than the wiki. | Structural facts are recoverable; exact defaults and unpropagated choices are `RECONFIRM`; contradictions are `REOPEN`. |
| Backlog stories | Planned work, not recovered behavior. | Never used as proof that a surface was implemented or settled. |
| Attic/recovered donors | Historical ideas used during reconstruction. | Evidence only. Never build from them unless a current source explicitly ratifies the fact. |

**Operator correction, 2026-08-17:** the legacy `QMX-discussion` corpus is not merely discarded attic material. It is the surviving source for many mechanics that remained stable while GitBook introduced Books/BMS and rewrote ownership. Use it claim by claim to supply the body of a surviving concept when GitBook preserves the name but leaves it undefined. Current operator rulings and explicit GitBook dead decisions still take precedence. See `recovery-lineage-addendum.md`.

## Inspected roots

- GitBook URL: `https://elios-1.gitbook.io/qmx`
- GitBook capture: `C:\Users\Mubarak\Documents\QMX\raw\online\qmx-gitbook\captures\2026-07-18T141659Z\pages\markdown`
- Active wiki: `C:\Users\Mubarak\Documents\QMX\wiki`
- BMAD output: `C:\Users\Mubarak\Documents\QMX\_bmad-output`
- Machine-readable standards referenced by completed stories: `C:\Users\Mubarak\Documents\QMX\standards`
- Surviving legacy-mechanics corpus: `C:\Users\Mubarak\Documents\Claude\QMX-discussion`

The two user-supplied roots were treated as seeds. Explicit references from them were followed into the local immutable GitBook capture and `standards` directory. No code repository was mined and no Git or GitHub operation was performed.

## High-value baseline pages

The baseline inspection centers on:

- `system-constitution.md`
- `architecture/overview.md`
- `architecture/dependency-graph.md`
- Book Template, BMS, Treasury, MIS, Adapter, Data Layer, Paper Mode, QML, KSA, and Notification component pages
- contract inventory, variables, formulas, golden scenarios, gap report, and dead decisions

The complete page-by-page baseline inventory is in `work/gitbook-baseline.md`.

## High-value later wiki sources

- `wiki/overview.md`
- `wiki/architecture/system-context.md`
- `wiki/architecture/runtime.md`
- `wiki/architecture/components.md`
- `wiki/architecture/data-and-contracts.md`
- `wiki/system/lifecycle.md`
- `wiki/components/*.md`
- `wiki/contracts/*.md`
- `wiki/topics/registration-and-promotion.md`
- `wiki/topics/attribute-model.md`
- `wiki/topics/position-safety-and-sltp-authority.md`
- `wiki/lenses/operations.md`
- `wiki/lenses/observability.md`
- `wiki/registry/*.md`
- `wiki/knowledge/gap-report.md`
- `wiki/log.md`
- `wiki/sources/bmad-planning-run-2026-07.md`

The wiki chronology matters. The logged sequence is GitBook ingest on 2026-07-18, donor recovery on 2026-07-20, planning delta on 2026-07-21, topology-v2 on 2026-07-24, and CT-BOOK-03 on 2026-07-27. A position-boundary page lacks matching wiki-log/front-matter evidence, but BMAD shows the 2026-07-28 PE-7-neutral scoping ruling applied to current epics/status/context. This recovers the narrow “proceed without position action” scope; final position fate remains `REOPEN`.

## High-value BMAD evidence

The architecture spine is:

`C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-07-20\ARCHITECTURE-SPINE.md`

The completed story/standard material most relevant to this recovery covers:

- CT-SYNC transport, envelope, verification, acknowledgment, and re-request behavior;
- data ownership, secrets, durable commit latency, failures, Powers API, and cold-start preflight;
- cTrader authentication, connection pooling, throttling, retry, heartbeat, labeling, and fill reconciliation;
- MIS labelers, fanout, typed snapshots, degradation, archive, query/result, and materialization;
- Book identity/schema/mode, Treasury birth/sweep/refusal, paper semantics, and reconciliation.

The sprint ledger is also negative evidence. At its 2026-07-28 state, adapter stories 4.1–4.3, kill-line detector 5.7, several reporting/metrics stories, and all later Doors/KSA/QML/promotion epics were still backlog. Completed proof stories therefore cannot be used to claim a complete Trading Node.

## Precision rules applied

1. A current page's status applies to its stated behavior, not automatically to every referenced contract field.
2. A `done` story is evidence only for its accepted slice.
3. Numeric limits copied from broker proofs are platform constraints unless the source explicitly ratifies them as product policy.
4. `null`, `pending`, `proposed`, and schema-empty values remain open; they are not invitations to infer defaults.
5. SQS means **Spread Quality Sensor**, per the current operator ruling. The later `snapshot_quality_score_v1` expansion and weighted multi-sensor aggregate are semantic drift and must not be treated as SQS.
6. Logical event ownership is distinct from the physical Records writer.
7. Agentic, Backtest/certification internals, WF1/WF2, donor-only slot/DPR machinery, and recovered QML APIs remain outside this recovery.
