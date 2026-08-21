# qmf-core

Exact money/time/instrument primitives, asset-neutral nouns, typed refusals, the single fp1 serializer, and protocol seams. Zero outside dependencies.

`qmf-core` imports as `qmf.core` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Scaffold plus the first public contract. Story 1.1 established identity, the
dependency direction, a benchmark-harness slot, and the Tier-1 test surface;
Story 1.2 landed the CT-04 **typed refusal envelope** — `TypedRefusal`, the seven
refusal categories, the `Result[T] = Ok[T] | TypedRefusal` value-or-refusal
pattern, and the validating `try_create` factory. The remaining
CT-01/CT-02/CT-03/CT-05 surface arrives in later stories. Build, lint,
type-check, and test through the workspace `poe` tasks — never in isolation.
