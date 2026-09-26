"""Reference usage — the CT-04 typed refusal envelope (COMP-QMF-CORE).

Executable::

    python packages/qmf-core/examples/refusal_usage.py

Every public qmf-core operation returns ``Result[T] = Ok[T] | TypedRefusal``
instead of raising a domain error. A caller branches on structure — ``is_ok`` /
``is_refusal`` — never on error prose. This module shows both halves of the
value-construction pattern: the unchecked constructor for a call site that
already knows the exact category, and the validating ``try_create`` factory for a
category that arrives dynamically.
"""

from __future__ import annotations

from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
)


def parse_lot_count(raw: str) -> Result[int]:
    """A stand-in public operation: parse a strictly-positive integer lot count.

    On bad input it RETURNS an ``invalid input`` refusal built with the unchecked
    constructor — the call site knows the exact category — never raising.
    """
    text = raw.strip()
    if not text.isdigit() or int(text) == 0:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={"raw": raw, "expected": "a positive base-10 integer"},
        )
    return Ok(int(text))


def describe(raw: str) -> str:
    """Branch on the ``Result`` structure, not on any error string."""
    result = parse_lot_count(raw)
    if is_ok(result):
        return f"accepted {result.value} lots"
    # `result` is narrowed to TypedRefusal here.
    return f"refused ({result.category.value}, retry={result.retryability.value})"


def refusal_from_dynamic(
    category: str,
    retryability: str,
    after_condition_descriptor: str | None = None,
) -> TypedRefusal:
    """Build a refusal whose category arrives dynamically (say, mapped from a
    venue error code) through the validating factory. If the parts are themselves
    invalid, ``try_create`` hands back an ``invalid input`` refusal explaining the
    rejection — the value-or-refusal pattern all the way down.
    """
    result = TypedRefusal.try_create(
        category,
        retryability,
        after_condition_descriptor=after_condition_descriptor,
    )
    if is_ok(result):
        return result.value
    return result


def main() -> None:
    for raw in ("3", "0", "abc"):
        print(describe(raw))
    print(refusal_from_dynamic("transient venue failure", "after-condition", "retry after 2s"))
    print(refusal_from_dynamic("not-a-category", "no"))


if __name__ == "__main__":
    main()
