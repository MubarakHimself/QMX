# qmf-core

Exact money/time/instrument primitives, asset-neutral nouns, typed refusals, the single fp1 serializer, and protocol seams. Zero outside dependencies.

`qmf-core` imports as `qmf.core` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Scaffold plus the first public contracts. Story 1.1 established identity, the
dependency direction, a benchmark-harness slot, and the Tier-1 test surface;
Story 1.2 landed the CT-04 **typed refusal envelope** — `TypedRefusal`, the seven
refusal categories, the `Result[T] = Ok[T] | TypedRefusal` value-or-refusal
pattern, and the validating `try_create` factory; Story 1.3 landed CT-03
**instrument, venue, and account identity** — `VenueId` (operator-minted opaque
token), `Instrument` (the never-parsed `(venue, symbol)` pair), the first-class
`Venue` and `Account` nouns with the fixed `AccountRole` set, and the append-only
`DatedRecord` for renames, aliases, asset-class, and metadata; Story 1.4 landed
CT-01 **exact money, price, and quantity values** — `Money`, `Price`,
`PriceDelta`, and `Quantity` as scaled integers with binary float banned on the
money path (a float re-enters only through the named `from_float` boundary), the
closed `UnitKind` vocabulary, mixed-scale lossless auto-promotion, delta-typed
price subtraction, metadata-sourced pip/value-factor conversions, and the pinned
canonical `fp1` identity form where equal value implies equal fingerprint. The
remaining CT-02/CT-05 surface arrives in later stories. Build, lint, type-check,
and test through the workspace `poe` tasks — never in isolation.
