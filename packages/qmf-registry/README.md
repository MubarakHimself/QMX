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

Every `fp1` fingerprint is computed in `qmf-core`; this package imports only
`qmf.core`, and registration and lineage are invoked at the application composition
root. The human-signed promotion occurrence is Story 2.3, and durable persistence
through `qmf-data`'s store-seam is Story 2.4. Build, lint, type-check, and test
through the workspace `poe` tasks — never in isolation.
