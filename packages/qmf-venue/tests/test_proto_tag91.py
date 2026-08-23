"""Story 8.2 tests — in-house proto compilation pinned at Spotware release tag 91.

These pin every acceptance criterion of the story:

* **AC1** — the venue protocol artifact names the Spotware ``openapi-proto-messages``
  integer release tag **91** (asserted against ``docs/registry/variables.yaml``), and
  only the proto **message definitions** (data, not code) are consumed: a serialized
  ``FileDescriptorSet`` is compiled in-house into usable message types.
* **AC2** — the SDK is reference-only and no Spotware code executes: the ``protobuf``
  runtime is declared a dependency of **qmf-venue alone**, ``qmf-venue`` src imports no
  Spotware SDK / Twisted / OpenApiPy, and compiling loads no such module.
* **AC3** — a tag change mints a new capability declaration and forces re-verification,
  and bumps a CT-* format version only where the wire change alters the public shape;
  a digest change under an unchanged tag is a pin-integrity violation (the edge).
* **AC4** — a compiled proto message never leaks into ``qmf-core``: default-deny holds,
  ``qmf-venue`` imports only ``qmf-core`` (plus the ``protobuf`` runtime), and nothing
  imports ``qmf-venue``.

Fixture-driven: every descriptor set is built in-test as data through the protobuf
runtime; no host is contacted and no registry value is hardcoded in shipped source
(AR-43, FR-026, DEC-0141).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, TypeVar

import tomllib
import yaml
from google.protobuf import descriptor_pb2
from qmf.core import Ok, RefusalCategory, Result, TypedRefusal, is_ok
from qmf.venue import (
    SPOTWARE_PROTO_PACKAGE,
    CompiledProto,
    ProtoArtifact,
    TagChangeAssessment,
    assess_tag_change,
    compile_descriptor_set,
    descriptor_set_digest,
)

T = TypeVar("T")

# The pinned Spotware openapi-proto-messages release tag — registry:venue_protocol_artifact.
# A test-only fixture constant (shipped source never hardcodes it); asserted against the
# actual registry in test_registry_pins_release_tag_91_for_venue below.
_PINNED_TAG = 91

_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE = "qmx.venue.spot"
_MESSAGE = "Envelope"
_FULL_NAME = f"{_PACKAGE}.{_MESSAGE}"

# A generous ceiling on any single source file the import walk reads (kilobytes in
# practice); it bounds the read in _imported_modules so a hostile tree entry can never
# force an unbounded one.
_MAX_SOURCE_BYTES = 1 << 20  # 1 MiB


# --- helpers ----------------------------------------------------------------


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    assert isinstance(result, Ok)
    return result.value


def _refusal(result: object) -> TypedRefusal:
    # Typed `object` (not `Result[object]`): `Result[T]` is invariant, so a concrete
    # `Result[CompiledProto]` would not be assignable to `Result[object]`.
    assert isinstance(result, TypedRefusal), result
    return result


def _descriptor_set_bytes(
    *,
    package: str = _PACKAGE,
    message_name: str = _MESSAGE,
    with_extra_field: bool = False,
    with_comment: bool = False,
) -> bytes:
    """Build a serialized FileDescriptorSet — proto message definitions as data.

    A single ``Envelope`` message carrying ``payload_type`` (uint32) and ``payload``
    (bytes), optionally with an extra field (a public-shape change) or a leading comment
    (a source-only change the normalized digest must ignore).
    """
    file_set = descriptor_pb2.FileDescriptorSet()
    file_proto = file_set.file.add()
    file_proto.name = f"{package.replace('.', '_')}.proto"
    file_proto.package = package
    file_proto.syntax = "proto3"
    message = file_proto.message_type.add()
    message.name = message_name
    type_field = message.field.add()
    type_field.name = "payload_type"
    type_field.number = 1
    type_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    type_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    payload_field = message.field.add()
    payload_field.name = "payload"
    payload_field.number = 2
    payload_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    payload_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
    if with_extra_field:
        extra = message.field.add()
        extra.name = "client_msg_id"
        extra.number = 3
        extra.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        extra.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    if with_comment:
        location = file_proto.source_code_info.location.add()
        location.leading_comments = " a comment that never alters the wire shape "
    return file_set.SerializeToString()


def _compiled(**kwargs: Any) -> CompiledProto:
    return _ok(
        compile_descriptor_set(
            _descriptor_set_bytes(**kwargs),
            package_name=SPOTWARE_PROTO_PACKAGE,
            release_tag=_PINNED_TAG,
        )
    )


def _artifact(*, tag: int, digest: str) -> ProtoArtifact:
    return _ok(ProtoArtifact.try_create(SPOTWARE_PROTO_PACKAGE, tag, digest))


def _registry_variable(name: str) -> dict[str, Any]:
    raw = (_ROOT / "docs" / "registry" / "variables.yaml").read_text(encoding="utf-8")
    document: Any = yaml.safe_load(raw)
    for entry in document["variables"]:
        if entry.get("name") == name:
            return dict(entry)
    raise AssertionError(f"registry variable {name!r} not found")


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by one source file (import + from-import).

    The path is resolved and must be a regular file inside ``_ROOT`` — never a symlink,
    never resolving out of the workspace — and its size is capped before the read, so a
    planted symlink or an oversized file can neither redirect nor unbound it.
    """
    resolved = path.resolve()
    assert not path.is_symlink(), resolved
    assert resolved.is_file() and resolved.is_relative_to(_ROOT), resolved
    size = resolved.stat().st_size
    assert size <= _MAX_SOURCE_BYTES, resolved
    tree = ast.parse(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _venue_src_imports() -> set[str]:
    src = _ROOT / "packages" / "qmf-venue" / "src" / "qmf" / "venue"
    imports: set[str] = set()
    for path in sorted(src.rglob("*.py")):
        imports.update(_imported_modules(path))
    return imports


# --- AC1: pin names Spotware openapi-proto-messages release tag 91 -----------


def test_registry_pins_release_tag_91_for_venue() -> None:
    entry = _registry_variable("venue_protocol_artifact")
    assert entry["value"] == 91
    assert entry["value"] == _PINNED_TAG
    assert entry["type"] == "integer"
    assert entry["units"] == "spotware-proto-release-tag"
    assert entry["component"] == "COMP-QMF-VENUE"
    assert entry["configurable"] is False


def test_artifact_names_the_spotware_package_and_pinned_tag() -> None:
    assert SPOTWARE_PROTO_PACKAGE == "openapi-proto-messages"
    artifact = _artifact(
        tag=_PINNED_TAG, digest=_ok(descriptor_set_digest(_descriptor_set_bytes()))
    )
    assert artifact.package_name == "openapi-proto-messages"
    assert artifact.release_tag == 91


def test_compile_consumes_message_definitions_as_data() -> None:
    compiled = _compiled()
    assert compiled.message_names() == (_FULL_NAME,)
    assert compiled.artifact.release_tag == _PINNED_TAG
    assert compiled.artifact.package_name == "openapi-proto-messages"
    assert compiled.artifact.descriptor_set_digest.startswith("sha256:")


def test_compiled_message_round_trips_on_its_own_transport() -> None:
    compiled = _compiled()
    message_class = _ok(compiled.message_class(_FULL_NAME))
    wire = message_class(payload_type=2126, payload=b"\x01\x02\x03").SerializeToString()
    decoded = _ok(compiled.decode(_FULL_NAME, wire))
    assert decoded.payload_type == 2126  # type: ignore[attr-defined]
    assert decoded.payload == b"\x01\x02\x03"  # type: ignore[attr-defined]


def test_compile_indexes_nested_messages() -> None:
    file_set = descriptor_pb2.FileDescriptorSet()
    file_proto = file_set.file.add()
    file_proto.name = "nested.proto"
    file_proto.package = "qmx.venue.nested"
    file_proto.syntax = "proto3"
    outer = file_proto.message_type.add()
    outer.name = "Outer"
    outer.nested_type.add().name = "Inner"
    compiled = _ok(
        compile_descriptor_set(
            file_set.SerializeToString(),
            package_name=SPOTWARE_PROTO_PACKAGE,
            release_tag=_PINNED_TAG,
        )
    )
    assert compiled.message_names() == (
        "qmx.venue.nested.Outer",
        "qmx.venue.nested.Outer.Inner",
    )


def test_compile_refuses_definitions_that_parse_but_do_not_compile() -> None:
    # A descriptor set that parses cleanly yet cannot compile — it declares a
    # dependency on a file that was never added — is a typed refusal, never an
    # exception and never a silent partial compilation.
    file_set = descriptor_pb2.FileDescriptorSet()
    file_proto = file_set.file.add()
    file_proto.name = "needs_import.proto"
    file_proto.package = "qmx.venue.bad"
    file_proto.syntax = "proto3"
    file_proto.dependency.append("missing.proto")
    file_proto.message_type.add().name = "M"
    refusal = _refusal(
        compile_descriptor_set(
            file_set.SerializeToString(),
            package_name=SPOTWARE_PROTO_PACKAGE,
            release_tag=_PINNED_TAG,
        )
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "descriptor_set_bytes"


def test_release_tag_is_never_hardcoded_in_shipped_proto_source() -> None:
    # The tag is injected from the registry; the string "91" must not appear in the
    # shipped proto module (the do-not-hardcode-a-registry-value rule).
    proto_src = (_ROOT / "packages" / "qmf-venue" / "src" / "qmf" / "venue" / "proto.py").read_text(
        encoding="utf-8"
    )
    assert "91" not in proto_src


# --- AC2: SDK reference-only, protobuf is a qmf-venue-only dependency --------


def test_protobuf_declared_only_in_qmf_venue() -> None:
    declared_in: list[str] = []
    manifests = sorted((_ROOT / "packages").glob("*/pyproject.toml")) + sorted(
        (_ROOT / "extensions").glob("*/pyproject.toml")
    )
    for manifest in manifests:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        if any(dep.split("==")[0].strip() == "protobuf" for dep in deps):
            declared_in.append(data["project"]["name"])
    assert declared_in == ["qmf-venue"]


def test_venue_src_imports_no_spotware_sdk_or_twisted() -> None:
    forbidden_prefixes = ("twisted", "ctrader", "openapi", "spotware", "OpenApiPy")
    offending = {
        imported
        for imported in _venue_src_imports()
        if imported.lower().startswith(tuple(p.lower() for p in forbidden_prefixes))
    }
    assert offending == set(), f"venue src imports a reference-only/banned runtime: {offending}"


def test_venue_src_only_third_party_import_is_protobuf() -> None:
    third_party: set[str] = set()
    for imported in _venue_src_imports():
        top = imported.split(".")[0]
        if top in sys.stdlib_module_names or top in {"qmf", "__future__"}:
            continue
        third_party.add(top)
    assert third_party == {"google"}, third_party


def test_compiling_loads_no_spotware_or_twisted_module() -> None:
    _compiled()
    forbidden = ("twisted", "ctrader", "openapipy", "spotware")
    loaded = {name for name in sys.modules if name.lower().startswith(forbidden)}
    assert loaded == set(), f"a Spotware/Twisted module is loaded: {loaded}"


# --- AC3: a tag change is a governed re-verification event -------------------


def test_no_change_when_tag_and_descriptor_set_are_identical() -> None:
    digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    verdict = _ok(
        assess_tag_change(_artifact(tag=91, digest=digest), _artifact(tag=91, digest=digest))
    )
    assert verdict == TagChangeAssessment(
        changed=False,
        re_verification_required=False,
        capability_declaration_reminted=False,
        wire_shape_changed=False,
        format_version_bump_required=False,
        pin_integrity_violation=False,
        pinned_tag=91,
        proposed_tag=91,
        detail=verdict.detail,
    )


def test_tag_change_same_shape_reverifies_without_a_format_bump() -> None:
    digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    verdict = _ok(
        assess_tag_change(_artifact(tag=91, digest=digest), _artifact(tag=92, digest=digest))
    )
    assert verdict.changed is True
    assert verdict.re_verification_required is True
    assert verdict.capability_declaration_reminted is True
    assert verdict.wire_shape_changed is False
    assert verdict.format_version_bump_required is False
    assert verdict.pin_integrity_violation is False
    assert verdict.pinned_tag == 91
    assert verdict.proposed_tag == 92


def test_tag_change_with_new_shape_reverifies_and_bumps_format_version() -> None:
    pinned_digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    changed_digest = _ok(descriptor_set_digest(_descriptor_set_bytes(with_extra_field=True)))
    assert pinned_digest != changed_digest
    verdict = _ok(
        assess_tag_change(
            _artifact(tag=91, digest=pinned_digest), _artifact(tag=92, digest=changed_digest)
        )
    )
    assert verdict.changed is True
    assert verdict.re_verification_required is True
    assert verdict.capability_declaration_reminted is True
    assert verdict.wire_shape_changed is True
    assert verdict.format_version_bump_required is True
    assert verdict.pin_integrity_violation is False


def test_same_tag_with_moved_descriptor_set_is_a_pin_integrity_violation() -> None:
    pinned_digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    moved_digest = _ok(descriptor_set_digest(_descriptor_set_bytes(with_extra_field=True)))
    verdict = _ok(
        assess_tag_change(
            _artifact(tag=91, digest=pinned_digest), _artifact(tag=91, digest=moved_digest)
        )
    )
    assert verdict.pin_integrity_violation is True
    assert verdict.re_verification_required is True
    assert verdict.capability_declaration_reminted is True
    assert verdict.wire_shape_changed is True
    assert verdict.format_version_bump_required is True


def test_comment_only_change_never_moves_the_digest() -> None:
    # A source-only change (a leading comment) leaves the wire/public shape untouched,
    # so the normalized digest is identical — no spurious format-version bump.
    plain = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    commented = _ok(descriptor_set_digest(_descriptor_set_bytes(with_comment=True)))
    assert plain == commented


def test_assess_rejects_comparing_two_different_protocols() -> None:
    digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    other = _ok(ProtoArtifact.try_create("some-other-proto", 91, digest))
    refusal = _refusal(assess_tag_change(_artifact(tag=91, digest=digest), other))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "package_name"


def test_assess_rejects_non_artifact_inputs() -> None:
    digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    good = _artifact(tag=91, digest=digest)
    assert _refusal(assess_tag_change("not-an-artifact", good)).context["field"] == "pinned"
    assert _refusal(assess_tag_change(good, "not-an-artifact")).context["field"] == "proposed"


# --- AC4: no leak into qmf-core; default-deny holds --------------------------


def test_qmf_core_src_imports_no_protobuf_and_no_venue() -> None:
    core_src = _ROOT / "packages" / "qmf-core" / "src" / "qmf" / "core"
    for path in sorted(core_src.rglob("*.py")):
        for imported in _imported_modules(path):
            top = imported.split(".")[0]
            assert top != "google", f"{path} imports a protobuf runtime into qmf-core"
            assert not imported.startswith("qmf.venue"), f"{path} imports qmf.venue into qmf-core"


def test_venue_src_imports_only_qmf_core_among_qmf() -> None:
    qmf_imports = {i for i in _venue_src_imports() if i.startswith("qmf.")}
    for imported in qmf_imports:
        assert imported.startswith(("qmf.core", "qmf.venue")), (
            f"qmf-venue imports a non-core roster package: {imported}"
        )
    assert any(i.startswith("qmf.core") for i in qmf_imports)


def test_no_other_package_imports_qmf_venue() -> None:
    violations: list[str] = []
    for base in (_ROOT / "packages", _ROOT / "extensions"):
        for path in sorted(base.rglob("src/**/*.py")):
            if "qmf-venue" in path.parts:
                continue
            for imported in _imported_modules(path):
                if imported == "qmf.venue" or imported.startswith("qmf.venue."):
                    violations.append(f"{path}: imports {imported}")
    assert violations == [], f"nothing may import the venue edge module: {violations}"


# --- ProtoArtifact and compiler construction refusals -----------------------


def test_artifact_rejects_blank_package_name() -> None:
    digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    refusal = _refusal(ProtoArtifact.try_create("  ", 91, digest))
    assert refusal.context["field"] == "package_name"


def test_artifact_rejects_non_positive_or_bool_or_string_tag() -> None:
    digest = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    for bad_tag in (0, -1, True, "91", 1.0):
        refusal = _refusal(ProtoArtifact.try_create(SPOTWARE_PROTO_PACKAGE, bad_tag, digest))
        assert refusal.category is RefusalCategory.INVALID_INPUT
        assert refusal.context["field"] == "release_tag"


def test_artifact_rejects_a_digest_without_the_sha256_prefix() -> None:
    for bad_digest in ("", "   ", "deadbeef", 123, None):
        refusal = _refusal(ProtoArtifact.try_create(SPOTWARE_PROTO_PACKAGE, 91, bad_digest))
        assert refusal.context["field"] == "descriptor_set_digest"


def test_digest_rejects_non_bytes_and_malformed_bytes() -> None:
    assert _refusal(descriptor_set_digest("not-bytes")).context["field"] == "descriptor_set_bytes"
    # Bytes that are not a valid FileDescriptorSet: a truncated varint field header.
    malformed = _refusal(descriptor_set_digest(b"\x08"))
    assert malformed.category is RefusalCategory.INVALID_INPUT


def test_digest_is_deterministic_for_identical_definitions() -> None:
    first = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    second = _ok(descriptor_set_digest(_descriptor_set_bytes()))
    assert first == second == first  # stable across calls
    assert first.startswith("sha256:")


def test_compile_rejects_non_bytes_and_malformed_definitions() -> None:
    non_bytes = _refusal(
        compile_descriptor_set(42, package_name=SPOTWARE_PROTO_PACKAGE, release_tag=_PINNED_TAG)
    )
    assert non_bytes.context["field"] == "descriptor_set_bytes"
    malformed = _refusal(
        compile_descriptor_set(
            b"\x08", package_name=SPOTWARE_PROTO_PACKAGE, release_tag=_PINNED_TAG
        )
    )
    assert malformed.category is RefusalCategory.INVALID_INPUT


def test_compile_rejects_an_invalid_release_tag() -> None:
    refusal = _refusal(
        compile_descriptor_set(
            _descriptor_set_bytes(), package_name=SPOTWARE_PROTO_PACKAGE, release_tag=0
        )
    )
    assert refusal.context["field"] == "release_tag"


# --- CompiledProto message resolution ---------------------------------------


def test_message_class_refuses_an_undeclared_message() -> None:
    compiled = _compiled()
    refusal = _refusal(compiled.message_class("qmx.venue.spot.NoSuchMessage"))
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "full_name"


def test_message_class_refuses_a_blank_name() -> None:
    compiled = _compiled()
    refusal = _refusal(compiled.message_class("   "))
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_decode_refuses_an_undeclared_message_and_non_bytes_wire() -> None:
    compiled = _compiled()
    assert (
        _refusal(compiled.decode("qmx.venue.spot.NoSuchMessage", b"")).category
        is RefusalCategory.UNSUPPORTED_CAPABILITY
    )
    assert _refusal(compiled.decode(_FULL_NAME, "not-bytes")).context["field"] == "wire_bytes"


def test_decode_refuses_malformed_wire_bytes() -> None:
    compiled = _compiled()
    refusal = _refusal(compiled.decode(_FULL_NAME, b"\x08"))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "wire_bytes"
