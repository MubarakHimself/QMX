# qmf-registry

Per-kind records, fingerprint-derived ids, append-only typed lineage edges, and the human-signed promotion skeleton.

`qmf-registry` imports as `qmf.registry` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

CT-06 landed (Story 2.1): per-kind, fingerprint-keyed registration records — the
tiny common header (kind, per-kind contract format version, at-birth parent
references, `WriterId`, per-writer sequence) plus a kind-specific body, the
addable-never-redefined `KindRegistry` (honoring the reserved
`promotion-occurrence-card` and `treasury-boundary-event` names), and a pure
in-memory `Registrar` whose stable id is DERIVED from an `fp1` fingerprint and
whose byte-identical re-write is idempotent while a true collision is refused and
alarmed.

CT-07 landed (Story 2.2): append-only typed lineage edges — the ratified `EdgeType`
vocabulary (fourteen V1 kinds, addable never redefined), the frozen `LineageEdge`
that references both endpoints by their `fp1` fingerprint, derives its own edge
fingerprint, and serializes to the pinned JSONL line (one `fp1`-canonical JSON
object, LF-terminated), and a pure in-memory single-writer `EdgeLog`. The log holds
`supersedes` pinned linear (one outgoing edge per subject, one resolvable
`current_head`, no fork and no cycle) while leaving `branches-from` multi-headed,
keeps a byte-identical re-append idempotent while refusing and alarming a true
collision, keeps `corroborates` / `disagrees-with` disagreements visible, and
rebuilds its derived indexes from the edge evidence. Physical persistence
(append-with-fsync, size-rotation, the CT-11 append-store) is Story 2.4; this story
defines the vocabulary, validation, and in-memory surface.

CT-06 promotion card + CT-13 promotion event landed (Story 2.3): the human-signed
promotion occurrence — the only path to live money. `PromotionCard.sign` mints the
reserved `promotion-occurrence-card` CT-06 kind with a human-only signer, a mandatory
plain-words summary declared an identity field (so the signature attests the exact
words read), the attested record's `fp1`, and — for an AD-32 risk admission — the
Book-definition (or BMS-definition) fingerprint as an identity field, so a signature
can never attest a superseded template. `authorize_live_promotion` is the refusal law:
with no human-signed card present, promotion does not occur (FM-4) — only a human
promotes into the live zone. `correct_summary` mints a NEW card linked to the prior via
a CT-07 `supersedes` edge rather than editing the signed words. `PromotionEvent` /
`emit_promotion_event` emit the CT-13 `promotion` event — only the card's `fp1` plus
`correlation_id`, never a second schema — through the core `JournalSink` seam; the
registry card stays canonical. V1 signing is the operator's recorded approval, with no
cryptographic dependency.

CT-09 registry persistence landed (Story 2.4): the durable tail, over the single ratified
inter-library edge `qmf-registry → qmf-data`. `RegistryPersistence` persists CT-06 records
(SQLite metadata) and CT-07 lineage edges (JSONL append streams) into the **per-world
registry room** through `qmf-data`'s CT-11 append-store — no database server, stdlib-typed
at the seam. Storage is content-addressed on `fp1` (`persistence_fingerprint`, never a
timestamp or minted id): a byte-identical re-write is idempotent while a true collision is
refused and alarmed; a persisted record round-trips to a `LoadedRecord` (its recomputed
stable id equal to the original's) and an edge to a `LineageEdge` (keyed on its own edge
fingerprint exactly). Rooms are per world — a cross-world read and a `world = simulated`
write are policy rejections (FM-7). An underlying store failure — disk-full, corrupt,
locked, truncated — is a `storage failure` typed refusal translated at the qmf-data
boundary, never raised across the package seam, and no partial registration is claimed
successful (FM-8). `migrate_registry_format` runs the staged
preflight→backup-first→dry-run→migrate→verify format migration to a distinct destination —
never mutating the only copy in place — with the source store as the documented restore
path, and every serialized artifact stamps its contract format version so history stays
readable forever.

Every `fp1` fingerprint is computed in `qmf-core`; this package imports `qmf.core`, its own
siblings (`records`, `lineage`, `promotion`), and — through the one ratified edge —
`qmf.data.store` for persistence. Under default-deny no library imports `qmf-registry`;
registration, lineage, promotion, and persistence are invoked at the application composition
root. The promotion gate's own workflow, UI, and timing remain platform territory outside
QMF. Build, lint, type-check, and test through the workspace `poe` tasks — never in
isolation.
