"""Reference usage — RecipeDefinition identity vs release fp1 (Story 58.3).

Executable::

    python qmb/examples/recipe_definition_usage.py

Shows the things AD-31 / Story 58.3 pin down:

1. Authored identity is (recipe_def_id, recipe_def_version, recipe_def_hash)
   and is reviewable before a run. Display recipe_id is not identity.
2. recipe_def_hash excludes display rename and credential values.
3. Two runs of one definition are two releases, not two recipes.
4. Provider ≠ venue. Preview ≠ export ≠ stream.
5. Non-trading output needs no CT-33 / Book / QMN wrap. CT-06 stays deferred.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.data import (
    RECIPE_OUTPUT_COMPLETENESS,
    hash_recipe_definition,
    review_recipe_definition,
    run_recipe_definition,
)
from qmf.core.chrono import WriterId
from qmf.core.refusal import Result, is_ok, is_refusal

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _payload() -> dict[str, object]:
    return {
        "completeness_required": "complete",
        "environment_pin": {
            "code_fp1": "fp1:sha256:" + "ab" * 32,
            "python": "3.14",
        },
        "inputs": [
            {
                "calendar": "FOREX",
                "coverage": {
                    "end": "2026-09-01",
                    "resolution": "1m",
                    "start": "2020-01-01",
                },
                "entitlement_ref": "cred:dukascopy",
                "freshness": {"as_of_policy": "event-time", "max_lag": "5m"},
                "instrument": "EURUSD",
                "kind": "ct10",
                "licensing": "operator-owned",
                "provider": "dukascopy",
                "provenance": {"lineage_kind": "CT-07", "source_class": "vendor-tick"},
                "revision": "rev:dukascopy:EURUSD:2026-09-01",
                "schema_roles": ["price", "bid", "ask"],
                "timezone": "UTC",
                "units": "price",
            },
            {
                "calendar": "NYSE",
                "coverage": {
                    "end": "2026-09-01",
                    "resolution": "event",
                    "start": "2020-01-01",
                },
                "entitlement_ref": "cred:calendar-feed",
                "freshness": {"as_of_policy": "event-time", "max_lag": "1d"},
                "kind": "ct10",
                "licensing": "vendor-terms",
                "provider": "calendar-feed",
                "provenance": {
                    "lineage_kind": "CT-07",
                    "source_class": "news-calendar",
                },
                "revision": "rev:calendar-feed:NYSE:2026-09-01",
                "schema_roles": ["event"],
                "timezone": "America/New_York",
                "units": "event",
            },
        ],
        "output_completeness_enumeration": list(RECIPE_OUTPUT_COMPLETENESS),
        "output_schema": "derived.asof.v1",
        "recipe_def_id": "rdef:asof-eurusd",
        "recipe_def_version": 3,
        "recipe_id": "Pretty As-of Join",
        "split_policy": {"kind": "purged-kfold"},
        "transforms": [
            {
                "adjustment": "none",
                "alignment": "event-time",
                "known_at_policy": "no-lookahead",
                "late_policy": "label-late",
                "missing_policy": "exclude",
                "name": "asof-join",
            }
        ],
    }


def main() -> None:
    payload = _payload()
    writer = _unwrap(
        WriterId.try_create("node-a", "authoring", "recipe-run", "boot-1"),
        "writer",
    )
    reviewed = _unwrap(review_recipe_definition(payload), "review recipe")
    hashed = _unwrap(hash_recipe_definition(payload), "hash recipe")
    renamed = _unwrap(
        hash_recipe_definition({**payload, "recipe_id": "Other Display Name"}),
        "hash renamed recipe",
    )
    first = _unwrap(
        run_recipe_definition(reviewed, run_id="run:one", writer=writer),
        "run one",
    )
    second = _unwrap(
        run_recipe_definition(reviewed, run_id="run:two", writer=writer),
        "run two",
    )
    preview = _unwrap(
        run_recipe_definition(reviewed, run_id="run:one", writer=writer, delivery="preview"),
        "preview run",
    )
    wrap = run_recipe_definition(
        reviewed,
        run_id="run:wrap",
        writer=writer,
        wrap={"book_fp1": "fp1:sha256:" + "ab" * 32},
    )
    ct06 = run_recipe_definition(reviewed, run_id="run:ct06", writer=writer, register_ct06=True)
    print("recipe definition ok")
    print(
        "identity "
        f"{reviewed.recipe_def_id} v{reviewed.recipe_def_version} "
        f"{reviewed.recipe_def_hash.value}"
    )
    print("display recipe_id is not identity")
    if hashed == renamed:
        print("display rename does not change recipe_def_hash")
    print(f"release one {first.output_release.value}")
    print(f"release two {second.output_release.value}")
    if first.output_release != second.output_release:
        print("two runs of one definition are two releases, not two recipes")
    print(f"CT-07 to recipe_def_hash {first.lineage.to_ref.value}")
    if preview.output_release != first.output_release:
        print("preview ≠ export ≠ stream")
    if is_refusal(wrap):
        print("non-trading output needs no Book wrap")
    if is_refusal(ct06):
        print("CT-06 recipe kind stays deferred")


if __name__ == "__main__":
    main()
