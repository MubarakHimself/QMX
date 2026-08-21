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
canonical `fp1` identity form where equal value implies equal fingerprint; and
Story 1.5 landed CT-02 **exact time, calendars, and the injected Clock** —
`Instant` as an `int64` UTC-nanosecond count with checked arithmetic (overflow
refused, never wrapped), `Duration`/`Interval`, the distinct `CivilDate` and
`TradingDate` (calendar identity carried in-band, cross-calendar comparison
refused), causality on instants only (`compare_causal` refuses at equal instants),
the type-separated wall/monotonic kinds behind the injected `Clock` protocol with
a pure `DataDrivenClock` for replay, `MonotonicReading` as a boot-scoped diagnostic
that is never an `Instant`, `WriterId` with strictly-increasing `OrderingKey`s that
carry no causal meaning, the `verify_tzdb_pin` calendar-extension seam, and
display-only labelled rendering excluded from identity. Story 1.6 landed CT-05 **the
single canonical serializer, fp1 fingerprint, result label, and worlds** — the one
`canonical_bytes` serializer and `fingerprint` function (emitted form
`fp1:sha256:<hex>`, living only in qmf-core) over the pinned recipe (sorted UTF-8
JSON, NFC-normalized strings, integer-only identity numerics with floats and nulls
refused, CT-01 canonical rationals, order-significant arrays, SHA-256), the
`Fingerprint` value, the `ResultLabel` whose parts are its identity with a
content-derived `computation_identity`, the `OccurrenceRecord` that sits outside
identity, the `World` (`live | replay | simulated`, with `simulated` a policy-rejection
refusal into governed evidence) and `EvidenceClass` enums, `governed_namespace`
storage separation, and the FM-6 idempotent/collision guard (`reconcile_write` plus
the in-memory `GovernedEvidenceLedger`). Build, lint, type-check, and test through the
workspace `poe` tasks — never in isolation.
