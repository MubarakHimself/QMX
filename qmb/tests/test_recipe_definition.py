"""Story 58.3 — RecipeDefinition identity is not the release fingerprint."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.data import (
    RECIPE_CT06_KIND_DEFERRED,
    RECIPE_DEF_HASH_FIELDS,
    RECIPE_DEF_IDENTITY_FIELDS,
    RECIPE_DEFINITION_CLASS,
    RECIPE_DELIVERY_MODES,
    RECIPE_IS_LIBRARY_KIND,
    RECIPE_LINEAGE_BINDS,
    RECIPE_LINEAGE_EDGE_TYPE,
    RECIPE_OUTPUT_COMPLETENESS,
    RECIPE_RELEASE_CLASS,
    RECIPE_ROOM_MACHINERY,
    RECIPE_WRAP_OWNER,
    data_front_identity,
    hash_recipe_definition,
    recipe_identity,
    review_recipe_definition,
    run_recipe_definition,
)
from qmf.core.chrono import WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import EdgeType

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _assert_invalid(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    if field is not None:
        assert result.context["field"] == field


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", "recipe-run", "boot-1"))


def _ticks() -> dict[str, object]:
    return {
        "calendar": "FOREX",
        "coverage": {"end": "2026-09-01", "resolution": "1m", "start": "2020-01-01"},
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
    }


def _calendar() -> dict[str, object]:
    return {
        "calendar": "NYSE",
        "coverage": {"end": "2026-09-01", "resolution": "event", "start": "2020-01-01"},
        "entitlement_ref": "cred:calendar-feed",
        "freshness": {"as_of_policy": "event-time", "max_lag": "1d"},
        "kind": "ct10",
        "licensing": "vendor-terms",
        "provider": "calendar-feed",
        "provenance": {"lineage_kind": "CT-07", "source_class": "news-calendar"},
        "revision": "rev:calendar-feed:NYSE:2026-09-01",
        "schema_roles": ["event"],
        "timezone": "America/New_York",
        "units": "event",
    }


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "completeness_required": "complete",
        "environment_pin": {
            "code_fp1": "fp1:sha256:" + "ab" * 32,
            "python": "3.14",
        },
        "inputs": [_ticks(), _calendar()],
        "output_completeness_enumeration": list(RECIPE_OUTPUT_COMPLETENESS),
        "output_schema": "derived.asof.v1",
        "recipe_def_id": "rdef:asof-eurusd",
        "recipe_def_version": 3,
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
    body.update(overrides)
    return body


def test_identity_is_id_version_hash_and_catalogue_is_complete() -> None:
    reviewed = _ok(review_recipe_definition(_payload()))
    identity = reviewed.identity()
    assert set(identity) == set(RECIPE_DEF_IDENTITY_FIELDS)
    assert identity["recipe_def_id"] == "rdef:asof-eurusd"
    assert identity["recipe_def_version"] == 3
    assert identity["recipe_def_hash"] == reviewed.recipe_def_hash.value
    catalogue = reviewed.catalogue()
    for field in (
        "inputs",
        "transforms",
        "split_policy",
        "environment_pin",
        "output_schema",
        "output_completeness_enumeration",
        "completeness_required",
    ):
        assert field in catalogue
    inputs = catalogue["inputs"]
    assert isinstance(inputs, list)
    first = cast("Mapping[str, object]", inputs[0])
    for field in (
        "coverage",
        "schema_roles",
        "units",
        "timezone",
        "calendar",
        "freshness",
        "provenance",
        "entitlement_ref",
        "licensing",
        "revision",
        "provider",
    ):
        assert field in first
    transforms = catalogue["transforms"]
    assert isinstance(transforms, list)
    transform = cast("Mapping[str, object]", transforms[0])
    for field in (
        "alignment",
        "known_at_policy",
        "missing_policy",
        "late_policy",
        "adjustment",
    ):
        assert field in transform
    schema = recipe_identity()
    assert schema["recipe_definition_class"] == RECIPE_DEFINITION_CLASS
    assert schema["recipe_identity_fields"] == RECIPE_DEF_IDENTITY_FIELDS
    assert schema["recipe_hash_fields"] == RECIPE_DEF_HASH_FIELDS
    assert schema["recipe_output_completeness_enumeration"] == RECIPE_OUTPUT_COMPLETENESS
    assert schema["recipe_wrap_owner"] == RECIPE_WRAP_OWNER
    assert schema["recipe_room_machinery"] == RECIPE_ROOM_MACHINERY
    assert schema["recipe_ct06_kind_deferred"] is True
    front = data_front_identity()
    assert front["recipe_definition_class"] == RECIPE_DEFINITION_CLASS
    assert front["recipe_is_library_kind"] is False


def test_hash_excludes_display_rename_and_credential_values() -> None:
    first = _ok(hash_recipe_definition(_payload()))
    renamed = _ok(hash_recipe_definition(_payload(recipe_id="Pretty As-of Join")))
    also_named = _ok(hash_recipe_definition(_payload(display_recipe_id="Pretty As-of Join")))
    assert first == renamed == also_named
    reviewed = _ok(review_recipe_definition(_payload(recipe_id="Pretty As-of Join")))
    assert reviewed.display_recipe_id == "Pretty As-of Join"
    assert "recipe_id" not in reviewed.hash_preimage()
    assert "display_recipe_id" not in reviewed.hash_preimage()
    hashed = fingerprint(reviewed.hash_preimage())
    assert is_ok(hashed)
    assert hashed.value == first
    _assert_invalid(
        review_recipe_definition(
            _payload(
                inputs=[
                    {**_ticks(), "secret": "s3cret"},
                    _calendar(),
                ]
            )
        ),
        field="secret",
    )
    _assert_invalid(
        review_recipe_definition(_payload(credential="hunter2")),
        field="credential",
    )
    _assert_invalid(
        review_recipe_definition(
            _payload(
                inputs=[
                    {**_ticks(), "entitlement_ref": "dukascopy-password"},
                    _calendar(),
                ]
            )
        ),
        field="entitlement_ref",
    )
    supplied = _ok(review_recipe_definition(_payload(recipe_def_hash=first.value)))
    assert supplied.recipe_def_hash == first
    other = _ok(Fingerprint.try_create("fp1:sha256:" + "cd" * 32))
    _assert_invalid(
        review_recipe_definition(_payload(recipe_def_hash=other.value)),
        field="recipe_def_hash",
    )


def test_two_runs_are_two_releases_not_two_recipes() -> None:
    definition = _ok(review_recipe_definition(_payload()))
    first = _ok(
        run_recipe_definition(definition, run_id="run:one", writer=_writer(), delivery="export")
    )
    second = _ok(
        run_recipe_definition(definition, run_id="run:two", writer=_writer(), delivery="export")
    )
    assert first.recipe_def_hash == second.recipe_def_hash == definition.recipe_def_hash
    assert first.recipe_def_id == second.recipe_def_id == definition.recipe_def_id
    assert first.output_release != second.output_release
    assert first.output_release != definition.recipe_def_hash
    assert first.run_id != second.run_id
    assert first.lineage.edge_type is EdgeType.OCCURRENCE_OF is RECIPE_LINEAGE_EDGE_TYPE
    assert first.lineage.to_ref == definition.recipe_def_hash
    assert first.lineage.from_ref == first.output_release
    identity = first.fp1_identity()
    assert identity["class"] == RECIPE_RELEASE_CLASS
    assert identity["lineage_binds"] == list(RECIPE_LINEAGE_BINDS)
    assert identity["is_library_kind"] is False
    assert "recipe_id" not in identity
    _assert_invalid(
        review_recipe_definition({"output_release": first.output_release.value}),
        field="output_release",
    )


def test_provider_is_not_venue_and_delivery_modes_stay_distinct() -> None:
    collided = _ticks()
    collided["venue"] = collided["provider"]
    _assert_invalid(
        review_recipe_definition(_payload(inputs=[collided, _calendar()])),
        field="venue",
    )
    _assert_invalid(
        review_recipe_definition(_payload(provider_venue="dukascopy")),
        field="provider_venue",
    )
    definition = _ok(review_recipe_definition(_payload()))
    preview = _ok(
        run_recipe_definition(
            definition, run_id="run:preview", writer=_writer(), delivery="preview"
        )
    )
    export = _ok(
        run_recipe_definition(definition, run_id="run:preview", writer=_writer(), delivery="export")
    )
    stream = _ok(
        run_recipe_definition(definition, run_id="run:preview", writer=_writer(), delivery="stream")
    )
    assert preview.output_release != export.output_release != stream.output_release
    assert preview.recipe_def_hash == export.recipe_def_hash == stream.recipe_def_hash
    assert {preview.delivery, export.delivery, stream.delivery} == set(RECIPE_DELIVERY_MODES)
    _assert_invalid(
        run_recipe_definition(definition, run_id="run:x", writer=_writer(), delivery="download"),
        field="delivery",
    )
    _assert_invalid(
        review_recipe_definition(_payload(preview=True, export=True)),
        field="preview",
    )


def test_non_trading_output_refuses_wrap_and_ct06_stays_deferred() -> None:
    definition = _ok(review_recipe_definition(_payload()))
    wrapped = run_recipe_definition(
        definition,
        run_id="run:wrap",
        writer=_writer(),
        wrap={"book_fp1": "fp1:sha256:" + "ab" * 32},
    )
    assert is_refusal(wrapped)
    assert wrapped.category is RefusalCategory.POLICY_REJECTION
    assert wrapped.context["field"] == "book_fp1"
    bot = run_recipe_definition(definition, run_id="run:bot", writer=_writer(), wrap={"ct33": True})
    assert is_refusal(bot)
    assert bot.context["field"] == "ct33"
    seat = run_recipe_definition(
        definition, run_id="run:seat", writer=_writer(), wrap={"qmn_seat": True}
    )
    assert is_refusal(seat)
    deferred = run_recipe_definition(
        definition, run_id="run:ct06", writer=_writer(), register_ct06=True
    )
    assert is_refusal(deferred)
    assert deferred.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert deferred.context["ct06_kind_deferred"] is True is RECIPE_CT06_KIND_DEFERRED
    library = run_recipe_definition(
        definition, run_id="run:lib", writer=_writer(), library_kind=True
    )
    assert is_refusal(library)
    assert library.category is RefusalCategory.POLICY_REJECTION
    assert library.context["is_library_kind"] is False is RECIPE_IS_LIBRARY_KIND
    release = _ok(run_recipe_definition(definition, run_id="run:plain", writer=_writer()))
    assert release.wraps_book is False
    assert release.wraps_ct33 is False
    assert release.wraps_qmn is False
    assert release.is_library_kind is False
    missing = dict(_payload())
    del missing["split_policy"]
    _assert_invalid(review_recipe_definition(missing), field="split_policy")
