"""Story 11.7 — CT-22 format-2 exit_policy catch-all default entry."""

from __future__ import annotations

from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import ExitKind, ExitLogicRef
from qmf.risk.exit_policy import (
    EXIT_POLICY_CATCH_ALL_FORMAT_VERSION,
    ExitPolicy,
    ExitPolicyResolution,
    ProtectiveStopAttachment,
    resolve_exit_policy_entry,
)


def _ref(module_id: str = "book.default.evidence_stop") -> ExitLogicRef:
    result = ExitLogicRef.try_create(module_id, {"style": "structure"})
    assert is_ok(result)
    return result.value


def test_catch_all_exists_only_at_format_2() -> None:
    assert EXIT_POLICY_CATCH_ALL_FORMAT_VERSION == 2
    catch_all = _ref("book.catch-all")
    format_1 = ExitPolicy.try_create(
        {"scalper": _ref()},
        catch_all_default_entry=catch_all,
        contract_format_version=1,
    )
    assert is_refusal(format_1)
    assert format_1.category is RefusalCategory.INVALID_INPUT


def test_format_2_optional_catch_all_resolves_unknown_family() -> None:
    catch_all = _ref("book.catch-all")
    explicit = _ref("book.scalper-exit")
    policy = ExitPolicy.try_create(
        {"scalper": explicit},
        permitted_exit_intent_kinds=(ExitKind.CLOSE_FULL,),
        catch_all_default_entry=catch_all,
    )
    assert is_ok(policy)
    hit = resolve_exit_policy_entry(policy.value, "scalper")
    assert is_ok(hit)
    assert hit.value.resolution is ExitPolicyResolution.EXPLICIT_FAMILY
    assert hit.value.entry is explicit
    fallback = resolve_exit_policy_entry(policy.value, "unknown-family")
    assert is_ok(fallback)
    assert fallback.value.resolution is ExitPolicyResolution.CATCH_ALL_DEFAULT
    assert fallback.value.entry is catch_all
    identity = policy.value.fp1_identity()
    assert "catch_all_default_entry" in identity


def test_format_1_policy_has_no_catch_all_key() -> None:
    policy = ExitPolicy.try_create({"scalper": _ref()}, contract_format_version=1)
    assert is_ok(policy)
    assert policy.value.catch_all_default_entry is None
    assert "catch_all_default_entry" not in policy.value.fp1_identity()
    missed = resolve_exit_policy_entry(policy.value, "other")
    assert is_refusal(missed)


def test_empty_permitted_kinds_is_the_honest_v1_default() -> None:
    policy = ExitPolicy.try_create({}, permitted_exit_intent_kinds=())
    assert is_ok(policy)
    assert policy.value.permitted_exit_intent_kinds == frozenset()
    assert policy.value.protective_stop_attachment is ProtectiveStopAttachment.REQUIRED


def test_close_partial_is_unsupported() -> None:
    result = ExitPolicy.try_create({}, permitted_exit_intent_kinds=("close_partial",))
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_unknown_format_version_is_unsupported() -> None:
    assert is_refusal(ExitPolicy.try_create({}, contract_format_version=99))
    assert is_refusal(ExitPolicy.try_create({}, contract_format_version=True))


def test_field_refusals() -> None:
    assert is_refusal(ExitPolicy.try_create("nope"))
    assert is_refusal(ExitPolicy.try_create({"": _ref()}))
    assert is_refusal(ExitPolicy.try_create({"fam": "not-a-ref"}))
    assert is_refusal(ExitPolicy.try_create({}, permitted_exit_intent_kinds="close_full"))
    assert is_refusal(ExitPolicy.try_create({}, permitted_exit_intent_kinds=("teleport",)))
    assert is_refusal(ExitPolicy.try_create({}, protective_stop_attachment="maybe"))
    assert is_refusal(
        ExitPolicy.try_create({}, catch_all_default_entry="not-a-ref", contract_format_version=2)
    )
    assert is_refusal(resolve_exit_policy_entry("nope", "fam"))
    empty = ExitPolicy.try_create({})
    assert is_ok(empty)
    assert is_refusal(resolve_exit_policy_entry(empty.value, "  "))


def test_resolved_entry_identity() -> None:
    policy = ExitPolicy.try_create({"fam": _ref()}, catch_all_default_entry=_ref("default"))
    assert is_ok(policy)
    resolved = resolve_exit_policy_entry(policy.value, "fam")
    assert is_ok(resolved)
    content = resolved.value.fp1_identity()
    assert content["resolution"] == "explicit-family"
    assert content["family_id"] == "fam"


def test_attachment_optional() -> None:
    policy = ExitPolicy.try_create(
        {},
        permitted_exit_intent_kinds=(ExitKind.TIGHTEN_PROTECTIVE_STOP, ExitKind.CLOSE_FULL),
        protective_stop_attachment=ProtectiveStopAttachment.OPTIONAL,
    )
    assert is_ok(policy)
    kinds = policy.value.fp1_identity()["permitted_exit_intent_kinds"]
    assert kinds == ["close_full", "tighten_protective_stop"]
