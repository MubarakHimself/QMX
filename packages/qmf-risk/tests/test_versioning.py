"""Story 10.1 AC5 — git-logic-without-git template versioning.

Verifies the append-only ``branches-from`` version graph (multiple heads legal),
the separate dated ``current`` pointer distinct from ``supersedes``, that every old
version stays readable forever and a re-add is refused, and the derivable diff
between two versions (CT-22, CT-27; DEC-0144, DEC-0158).
"""

from __future__ import annotations

from qmf.core import (
    Fingerprint,
    Instant,
    Money,
    UnitKind,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.grammar import AdmissionImpact, TemplateVariable, UiEditability
from qmf.risk.versioning import (
    TemplateVersionGraph,
    VersionEdgeKind,
    diff_variable_maps,
)


def _fp(tag: str) -> Fingerprint:
    result = fingerprint({"class": "test-version", "tag": tag})
    assert is_ok(result)
    return result.value


def _instant(ns: int) -> Instant:
    return Instant(value_ns=ns)


def test_version_edge_kinds_name_branches_from_and_supersedes() -> None:
    assert VersionEdgeKind.BRANCHES_FROM.value == "branches-from"
    assert VersionEdgeKind.SUPERSEDES.value == "supersedes"


def test_append_root_then_branch_child() -> None:
    graph = TemplateVersionGraph()
    root = _fp("v1")
    child = _fp("v2")
    assert is_ok(graph.append_version(root))
    assert is_ok(graph.append_version(child, branches_from=root))
    assert graph.versions() == (root, child)
    assert graph.parent_of(child) == root
    assert graph.parent_of(root) is None


def test_multiple_heads_are_legal() -> None:
    graph = TemplateVersionGraph()
    root = _fp("v1")
    branch_a = _fp("v2a")
    branch_b = _fp("v2b")
    assert is_ok(graph.append_version(root))
    assert is_ok(graph.append_version(branch_a, branches_from=root))
    assert is_ok(graph.append_version(branch_b, branches_from=root))
    heads = graph.heads()
    assert set(heads) == {branch_a, branch_b}
    assert root not in heads  # root is a parent, not a head


def test_re_adding_a_version_is_refused_never_idempotent() -> None:
    graph = TemplateVersionGraph()
    root = _fp("v1")
    assert is_ok(graph.append_version(root))
    result = graph.append_version(root)
    assert is_refusal(result)
    assert result.context["field"] == "fingerprint"


def test_dangling_branch_parent_is_refused() -> None:
    graph = TemplateVersionGraph()
    child = _fp("v2")
    result = graph.append_version(child, branches_from=_fp("absent-parent"))
    assert is_refusal(result)


def test_a_version_may_not_branch_from_itself() -> None:
    graph = TemplateVersionGraph()
    node = _fp("v1")
    assert is_ok(graph.append_version(node))  # present it so self-branch is the failure
    graph_two = TemplateVersionGraph()
    result = graph_two.append_version(node, branches_from=node)
    assert is_refusal(result)


def test_append_rejects_non_fingerprint_inputs() -> None:
    graph = TemplateVersionGraph()
    assert is_refusal(graph.append_version("not-a-fingerprint"))
    root = _fp("v1")
    assert is_ok(graph.append_version(root))
    assert is_refusal(graph.append_version(_fp("v2"), branches_from="not-a-fingerprint"))


def test_current_pointer_is_a_separate_dated_record() -> None:
    graph = TemplateVersionGraph()
    v1 = _fp("v1")
    v2 = _fp("v2")
    assert is_ok(graph.append_version(v1))
    assert is_ok(graph.append_version(v2, branches_from=v1))
    assert graph.current() is None  # unset until a pointer is dated
    assert is_ok(graph.set_current(v1, _instant(1_000)))
    assert graph.current() == v1
    assert is_ok(graph.set_current(v2, _instant(2_000)))
    assert graph.current() == v2
    assert len(graph.pointer_history()) == 2


def test_current_pointer_must_name_a_known_version() -> None:
    graph = TemplateVersionGraph()
    result = graph.set_current(_fp("unknown"), _instant(1))
    assert is_refusal(result)


def test_current_pointer_is_dated_forward() -> None:
    graph = TemplateVersionGraph()
    v1 = _fp("v1")
    assert is_ok(graph.append_version(v1))
    assert is_ok(graph.set_current(v1, _instant(2_000)))
    stale = graph.set_current(v1, _instant(1_000))
    assert is_refusal(stale)
    assert stale.context["field"] == "dated_at"


def test_current_pointer_rejects_non_instant_date() -> None:
    graph = TemplateVersionGraph()
    v1 = _fp("v1")
    assert is_ok(graph.append_version(v1))
    assert is_refusal(graph.set_current(v1, "yesterday"))


def test_current_pointer_rejects_non_fingerprint() -> None:
    graph = TemplateVersionGraph()
    assert is_refusal(graph.set_current("nope", _instant(1)))


def test_every_old_version_stays_readable_forever() -> None:
    graph = TemplateVersionGraph()
    v1 = _fp("v1")
    v2 = _fp("v2")
    assert is_ok(graph.append_version(v1))
    assert is_ok(graph.append_version(v2, branches_from=v1))
    assert graph.is_readable(v1) is True
    assert graph.is_readable(v2) is True
    assert graph.is_readable(_fp("never-added")) is False
    assert graph.is_readable("not-a-fingerprint") is False


def test_current_pointer_fp1_identity_is_stable() -> None:
    graph = TemplateVersionGraph()
    v1 = _fp("v1")
    assert is_ok(graph.append_version(v1))
    pointer = graph.set_current(v1, _instant(5))
    assert is_ok(pointer)
    assert pointer.value.fp1_identity() == pointer.value.fp1_identity()


def test_parent_of_non_fingerprint_is_none() -> None:
    graph = TemplateVersionGraph()
    assert graph.parent_of("not-a-fingerprint") is None


# --- the derivable diff ------------------------------------------------------


def _variable(name: str, minor: int) -> TemplateVariable:
    result = TemplateVariable.try_create(
        name,
        UnitKind.MONEY,
        Money(value=minor, currency="USD", scale=2),
        UiEditability.UI_EDITABLE,
        AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    return result.value


def test_diff_names_added_removed_changed_and_unchanged() -> None:
    old = {"a": _variable("a", 100), "b": _variable("b", 200)}
    new = {"a": _variable("a", 100), "b": _variable("b", 999), "c": _variable("c", 300)}
    result = diff_variable_maps(old, new)
    assert is_ok(result)
    diff = result.value
    assert diff.added == ("c",)
    assert diff.removed == ()
    assert diff.changed == ("b",)
    assert diff.unchanged == ("a",)
    assert diff.is_empty is False


def test_diff_of_identical_maps_is_empty() -> None:
    old = {"a": _variable("a", 100)}
    new = {"a": _variable("a", 100)}
    result = diff_variable_maps(old, new)
    assert is_ok(result)
    assert result.value.is_empty is True


def test_diff_rejects_non_mappings_and_bad_values() -> None:
    assert is_refusal(diff_variable_maps(["a"], {}))
    assert is_refusal(diff_variable_maps({}, "nope"))
    assert is_refusal(diff_variable_maps({"a": "not-a-variable"}, {}))
