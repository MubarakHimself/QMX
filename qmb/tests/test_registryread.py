"""Story 13.2 — the single registry-read port over immutable as-of sets."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import TypeVar

from qmb.doors import api
from qmb.registryread import (
    AS_OF_FORMAT_VERSION,
    HUB_KIND,
    STALE_EVIDENCE_SEVERITY_KEY,
    STATE_KIND,
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryFragment,
    RegistryReadPort,
    SupersedesRef,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_SEVERITY = "workspace-declared"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", "book-definition", "boot-1"))


def _record(*, note: str, machine: str = "node-a") -> RegistrationRecord:
    return _ok(
        RegistrationRecord.try_create(
            "book-definition",
            1,
            [],
            {"alias": "scalping", "note": note},
            _writer(machine),
            0,
            _instant(),
        )
    )


def _pointer(alias: str, target: object, dated_at: Instant | None = None) -> DatedPointer:
    return _ok(DatedPointer.try_create(alias, target, dated_at or _instant()))


def _as_of(
    instant: Instant,
    records: tuple[RegistrationRecord, ...],
    *,
    fragments: tuple[RegistryFragment, ...] = (),
    pointers: tuple[DatedPointer, ...] = (),
    supersedes: tuple[SupersedesRef, ...] = (),
) -> AsOfSet:
    return _ok(
        AsOfSet.try_create(
            instant,
            records=records,
            fragments=fragments,
            pointers=pointers,
            supersedes=supersedes,
        )
    )


def _port(
    hub: PassiveHub,
    *,
    bound: AsOfSet | None = None,
    frozen: bool = False,
    severity: str = _SEVERITY,
) -> RegistryReadPort:
    return _ok(
        RegistryReadPort.try_create(
            hub,
            stale_evidence_severity=severity,
            bound=bound,
            frozen=frozen,
        )
    )


def test_as_of_set_is_fingerprinted_and_excludes_semver() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,), pointers=(_pointer("scalping", record.stable_id),))
    assert as_of.registry_as_of.value_ns == _CREATED_NS
    assert as_of.fingerprint.value.startswith("fp1:sha256:")
    identity = as_of.fp1_identity()
    assert identity["class"] == STATE_KIND
    assert identity["format_version"] == AS_OF_FORMAT_VERSION
    assert qmb.__version__ not in str(identity)
    again = _as_of(_instant(), (record,), pointers=(_pointer("scalping", record.stable_id),))
    assert again.fingerprint.value == as_of.fingerprint.value


def test_human_alias_resolves_by_fp1_never_name_at_version() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,), pointers=(_pointer("scalping", record.stable_id),))
    hub = _ok(PassiveHub.try_create((as_of,)))
    port = _port(hub)
    resolved = _ok(port.resolve("scalping"))
    assert resolved.cite() == record.stable_id.value
    assert resolved.alias == "scalping"
    assert resolved.record is record
    by_fp = _ok(port.resolve(record.stable_id))
    assert by_fp.cite() == record.stable_id.value
    banned = port.resolve("scalping@1")
    assert is_refusal(banned)
    assert banned.category is RefusalCategory.INVALID_INPUT
    latest = port.resolve("scalping@latest")
    assert is_refusal(latest)
    assert latest.category is RefusalCategory.INVALID_INPUT


def test_dated_current_pointer_is_legal_ux() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,), pointers=(_pointer("current", record.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    resolved = _ok(port.resolve("current"))
    assert resolved.cite() == record.stable_id.value


def test_stale_evidence_is_returned_not_raised_at_injected_severity() -> None:
    first = _record(note="v1")
    second = _record(note="v2", machine="node-b")
    older = _as_of(
        _instant(_CREATED_NS),
        (first,),
        pointers=(_pointer("scalping", first.stable_id, _instant(_CREATED_NS)),),
    )
    newer = _as_of(
        _instant(_CREATED_NS + 1),
        (first, second),
        pointers=(_pointer("scalping", second.stable_id, _instant(_CREATED_NS + 1)),),
        supersedes=(_ok(SupersedesRef.try_create(second.stable_id, first.stable_id)),),
    )
    hub = _ok(PassiveHub.try_create((older, newer)))
    current = _port(hub)
    live = _ok(current.resolve("scalping"))
    assert live.cite() == second.stable_id.value
    stale_ref = current.resolve(first.stable_id)
    assert is_refusal(stale_ref)
    assert stale_ref.category is RefusalCategory.STALE_EVIDENCE
    assert stale_ref.context["severity"] == _SEVERITY
    assert stale_ref.context["severity_key"] == STALE_EVIDENCE_SEVERITY_KEY
    assert stale_ref.context["fingerprint"] == first.stable_id.value
    bound_old = _port(hub, bound=older)
    stale_via_alias = bound_old.resolve("scalping")
    assert is_refusal(stale_via_alias)
    assert stale_via_alias.category is RefusalCategory.STALE_EVIDENCE


def test_sweep_freezes_one_as_of_and_resolves_by_explicit_fingerprint() -> None:
    first = _record(note="v1")
    second = _record(note="v2", machine="node-b")
    older = _as_of(
        _instant(_CREATED_NS),
        (first,),
        pointers=(_pointer("scalping", first.stable_id, _instant(_CREATED_NS)),),
    )
    newer = _as_of(
        _instant(_CREATED_NS + 1),
        (first, second),
        pointers=(_pointer("scalping", second.stable_id, _instant(_CREATED_NS + 1)),),
        supersedes=(_ok(SupersedesRef.try_create(second.stable_id, first.stable_id)),),
    )
    hub = _ok(PassiveHub.try_create((older,)))
    admitted = _port(hub, bound=older).admit_batch()
    assert admitted.frozen is True
    assert admitted.admit_batch() is admitted
    grown = _ok(hub.with_set(newer))
    frozen = _ok(
        RegistryReadPort.try_create(
            grown,
            stale_evidence_severity=_SEVERITY,
            bound=older,
            frozen=True,
        )
    )
    trial = _ok(frozen.resolve(first.stable_id))
    assert trial.cite() == first.stable_id.value
    alias = frozen.resolve("scalping")
    assert is_refusal(alias)
    assert alias.category is RefusalCategory.INVALID_INPUT
    named_latest = frozen.resolve("book@latest")
    assert is_refusal(named_latest)
    assert named_latest.category is RefusalCategory.INVALID_INPUT
    by_string = _ok(frozen.resolve(first.stable_id.value))
    assert by_string.cite() == first.stable_id.value
    extra = _record(note="unrelated", machine="node-c")
    additive = _as_of(
        _instant(_CREATED_NS + 2),
        (first, extra),
        pointers=(_pointer("scalping", first.stable_id, _instant(_CREATED_NS + 2)),),
    )
    additive_hub = _ok(PassiveHub.try_create((older, additive)))
    still_current = _ok(_port(additive_hub, bound=older).resolve(first.stable_id))
    assert still_current.cite() == first.stable_id.value


def test_fragment_resolves_by_fp1() -> None:
    record = _record(note="v1")
    fragment = _ok(RegistryFragment.try_create(record.stable_id, {"preset": "stress-spread"}))
    as_of = _as_of(_instant(), (record,), fragments=(fragment,))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    resolved = _ok(port.resolve(fragment.fingerprint))
    assert resolved.fragment is fragment
    assert resolved.record is None
    assert resolved.cite() == fragment.fingerprint.value


def test_one_port_serves_compiler_and_door_with_no_second_cache() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,), pointers=(_pointer("scalping", record.stable_id),))
    hub = _ok(PassiveHub.try_create((as_of,)))
    compiler = _port(hub)
    door = _port(hub)
    assert compiler.bound.fingerprint == door.bound.fingerprint
    assert _ok(compiler.resolve("scalping")).cite() == _ok(door.resolve("scalping")).cite()
    assert compiler.enumerate_aliases() == door.enumerate_aliases()
    assert api.RegistryReadPort is qmb.RegistryReadPort
    assert api.PassiveHub is qmb.PassiveHub
    assert api.AsOfSet is qmb.AsOfSet
    assert api.HUB_KIND == HUB_KIND == "passive-storage"
    assert api.STATE_KIND == STATE_KIND == "as-of set"
    assert api.STALE_EVIDENCE_SEVERITY_KEY == STALE_EVIDENCE_SEVERITY_KEY
    assert "version" not in qmb.read_port_identity()
    assert qmb.__version__ not in qmb.read_port_identity().values()


def test_hub_is_dumb_passive_storage() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,))
    hub = _ok(PassiveHub.try_create((as_of,)))
    assert hub.kind == HUB_KIND == "passive-storage"
    assert _ok(hub.latest()).fingerprint == as_of.fingerprint
    same = _ok(hub.with_set(as_of))
    assert same is hub
    docs = (PassiveHub.__doc__ or "") + (AsOfSet.__doc__ or "")
    assert "passive" in docs.lower()
    assert "snapshot" not in docs.lower()
    empty = _ok(PassiveHub.try_create(()))
    missing = empty.latest()
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_doors_hold_no_registry_cache() -> None:
    doors = _SRC / "doors"
    offenders: list[str] = []
    for path in sorted(doors.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if value is None:
                continue
            if isinstance(value, ast.Call) and _names_port_or_hub(value):
                offenders.append(str(path.relative_to(_SRC)))
    assert offenders == []


def _names_port_or_hub(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in {"RegistryReadPort", "PassiveHub", "AsOfSet"}
    if isinstance(func, ast.Attribute):
        return func.attr in {"try_create", "RegistryReadPort", "PassiveHub", "AsOfSet"}
    return False


def test_port_refuses_blank_severity_and_missing_ref() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,))
    hub = _ok(PassiveHub.try_create((as_of,)))
    blank = RegistryReadPort.try_create(hub, stale_evidence_severity="  ")
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT
    port = _port(hub)
    absent = _ok(Fingerprint.try_create("fp1:sha256:" + "ab" * 32))
    missing = port.resolve(absent)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    unknown_alias = port.resolve("unknown-book")
    assert is_refusal(unknown_alias)
    assert unknown_alias.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_pointer_and_supersedes_validation() -> None:
    record = _record(note="v1")
    other = _record(note="v2", machine="node-b")
    at_version = DatedPointer.try_create("scalping@1", record.stable_id, _instant())
    assert is_refusal(at_version)
    dangling = AsOfSet.try_create(
        _instant(),
        records=(record,),
        pointers=(_pointer("scalping", other.stable_id),),
    )
    assert is_refusal(dangling)
    cycle = SupersedesRef.try_create(record.stable_id, record.stable_id)
    assert is_refusal(cycle)
    pair = _ok(SupersedesRef.try_create(other.stable_id, record.stable_id))
    missing_end = AsOfSet.try_create(_instant(), records=(record,), supersedes=(pair,))
    assert is_refusal(missing_end)


def test_as_of_set_is_immutable() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,))
    try:
        as_of.records = ()  # type: ignore[misc]
    except FrozenInstanceError:
        return
    raise AssertionError("as-of set mutated")


def test_as_of_and_fragment_construction_refusals() -> None:
    record = _record(note="v1")
    assert is_refusal(AsOfSet.try_create("not-an-instant", records=(record,)))
    assert is_refusal(AsOfSet.try_create(_instant(), records="not-a-sequence"))
    assert is_refusal(AsOfSet.try_create(_instant(), records=(object(),)))
    assert is_ok(AsOfSet.try_create(_instant(), records=None))
    assert is_refusal(AsOfSet.try_create(_instant(), records=1))
    assert is_refusal(AsOfSet.try_create(_instant(), fragments="nope"))
    assert is_refusal(AsOfSet.try_create(_instant(), pointers="nope"))
    assert is_refusal(AsOfSet.try_create(_instant(), supersedes="nope"))
    assert is_refusal(DatedPointer.try_create("  ", record.stable_id, _instant()))
    assert is_refusal(DatedPointer.try_create("scalping", "not-fp1", _instant()))
    assert is_refusal(DatedPointer.try_create("scalping", record.stable_id, "now"))
    assert is_refusal(RegistryFragment.try_create("not-fp1", {"preset": "stress"}))
    assert is_refusal(RegistryFragment.try_create(record.stable_id, "body"))
    floated = RegistryFragment.try_create(record.stable_id, {"spread": 1.5})
    assert is_refusal(floated)
    nested = _ok(
        RegistryFragment.try_create(
            record.stable_id,
            {"preset": "stress-spread", "tags": ["a", "b"], "meta": {"k": "v"}},
        )
    )
    assert nested.fp1_identity()["class"] == "registry-fragment"
    assert is_refusal(SupersedesRef.try_create("not-fp1", record.stable_id))
    assert is_refusal(SupersedesRef.try_create(record.stable_id, "not-fp1"))
    later = _pointer("scalping", record.stable_id, _instant(_CREATED_NS + 5))
    assert is_refusal(AsOfSet.try_create(_instant(_CREATED_NS), (record,), pointers=(later,)))
    first = _pointer("scalping", record.stable_id)
    second = _pointer("scalping", record.stable_id)
    assert is_refusal(AsOfSet.try_create(_instant(), (record,), pointers=(first, second)))
    other = _record(note="v2", machine="node-b")
    third = _record(note="v3", machine="node-c")
    pair = _ok(SupersedesRef.try_create(other.stable_id, record.stable_id))
    fork = _ok(SupersedesRef.try_create(third.stable_id, record.stable_id))
    assert is_refusal(
        AsOfSet.try_create(_instant(), (record, other, third), supersedes=(pair, fork))
    )
    back = _ok(SupersedesRef.try_create(record.stable_id, other.stable_id))
    assert is_refusal(AsOfSet.try_create(_instant(), (record, other), supersedes=(pair, back)))
    twice = _ok(SupersedesRef.try_create(other.stable_id, third.stable_id))
    assert is_refusal(
        AsOfSet.try_create(_instant(), (record, other, third), supersedes=(pair, twice))
    )


def test_duplicate_members_are_idempotent_or_collisions() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record, record))
    assert len(as_of.records) == 1
    fragment = _ok(RegistryFragment.try_create(record.stable_id, {"preset": "stress-spread"}))
    again = _as_of(_instant(), (record,), fragments=(fragment, fragment))
    assert len(again.fragments) == 1
    forged = RegistrationRecord(
        kind=record.kind,
        contract_format_version=record.contract_format_version,
        at_birth_parent_refs=record.at_birth_parent_refs,
        body={"alias": "scalping", "note": "forged"},
        writer=record.writer,
        sequence=record.sequence,
        created_at=record.created_at,
        stable_id=record.stable_id,
    )
    collided = AsOfSet.try_create(_instant(), records=(record, forged))
    assert is_refusal(collided)
    fake_fragment = RegistryFragment(
        source_fp1=record.stable_id,
        body={"preset": "other"},
        fingerprint=fragment.fingerprint,
    )
    collided_frag = AsOfSet.try_create(
        _instant(), records=(record,), fragments=(fragment, fake_fragment)
    )
    assert is_refusal(collided_frag)
    overlap = RegistryFragment(
        source_fp1=record.stable_id,
        body={"preset": "overlap"},
        fingerprint=record.stable_id,
    )
    assert is_refusal(AsOfSet.try_create(_instant(), (record,), fragments=(overlap,)))


def test_hub_and_port_lookup_edges() -> None:
    record = _record(note="v1")
    as_of = _as_of(_instant(), (record,), pointers=(_pointer("scalping", record.stable_id),))
    assert as_of.get(record.stable_id.value) is record
    assert as_of.get("not-fp1") is None
    assert as_of.pointer_for("  ") is None
    assert as_of.pointer_for("missing") is None
    assert is_refusal(as_of.current_head("not-fp1"))
    assert as_of.is_superseded("not-fp1") is False
    head = _ok(as_of.current_head(record.stable_id))
    assert head.value == record.stable_id.value
    assert as_of.is_superseded(record.stable_id) is False
    assert is_refusal(PassiveHub.try_create("sets"))
    assert is_refusal(PassiveHub.try_create({"sets": 1}))
    assert is_refusal(PassiveHub.try_create((object(),)))
    empty = _ok(PassiveHub.try_create(None))
    assert is_refusal(empty.latest())
    hub = _ok(PassiveHub.try_create((as_of, as_of)))
    assert len(hub.sets) == 1
    assert is_ok(hub.get(as_of.fingerprint.value))
    assert is_refusal(hub.get("not-fp1"))
    absent = _ok(Fingerprint.try_create("fp1:sha256:" + "cd" * 32))
    assert is_refusal(hub.get(absent))
    assert hub.fresher_than("now") == ()
    assert is_refusal(hub.with_set("not-a-set"))
    clone = AsOfSet(
        registry_as_of=as_of.registry_as_of,
        fingerprint=as_of.fingerprint,
        records=(),
        fragments=(),
        pointers=(),
        supersedes=(),
    )
    assert is_refusal(hub.with_set(clone))
    assert is_refusal(PassiveHub.try_create((as_of, clone)))
    assert is_refusal(RegistryReadPort.try_create("hub", stale_evidence_severity=_SEVERITY))
    assert is_refusal(
        RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY, frozen="yes")
    )
    by_fp = _ok(
        RegistryReadPort.try_create(
            hub, stale_evidence_severity=_SEVERITY, bound=as_of.fingerprint.value
        )
    )
    assert by_fp.bound.fingerprint == as_of.fingerprint
    other = _as_of(_instant(_CREATED_NS + 9), (record,))
    assert is_refusal(
        RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY, bound=other)
    )
    assert is_refusal(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY, bound=1))
    port = _port(hub)
    assert is_refusal(port.resolve(None))
    assert qmb.port_home() == api.port_home()
    assert "KindRegistry" in qmb.port_home()
    fragment = _ok(RegistryFragment.try_create(record.stable_id, {"preset": "stress-spread"}))
    assert is_refusal(AsOfSet.try_create(_instant(), fragments=(object(),)))
    assert is_refusal(AsOfSet.try_create(_instant(), pointers=(object(),)))
    assert is_refusal(AsOfSet.try_create(_instant(), supersedes=(object(),)))
    assert is_refusal(AsOfSet.try_create(_instant(), records=b"raw"))
    _ = fragment
