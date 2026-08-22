"""In-house Spotware proto compilation, pinned at the AD-6 release tag (Story 8.2).

`COMP-QMF-VENUE` owns its own transport. The venue protocol artifact is the Spotware
``openapi-proto-messages`` package, pinned in the AD-6 dependency register at its
integer release tag (``registry:venue_protocol_artifact``, injected here, never
hardcoded). This module compiles that release **in-house**: it consumes only the proto
**message definitions** — a serialized ``FileDescriptorSet`` carried as *data* — and
builds usable message types through the ``protobuf`` runtime's descriptor pool and
message factory. **Zero Spotware code runs**: the official OpenApiPy SDK is
reference-only (its pinned Twisted reactor is platform-imposing and rejected under
AR-06/DEPENDENCIES.md), so nothing from it is imported or executed here — the only
third-party import is ``google.protobuf`` (AR-43, FR-026, DEC-0141).

Three pieces:

* :class:`ProtoArtifact` — the pinned artifact identity: the Spotware package name, the
  injected integer release tag, and a content digest over the compiled descriptor set.
  The digest is identity-bearing for any artifact whose decode depended on it (CT-18).
* :func:`compile_descriptor_set` / :class:`CompiledProto` — the in-house compiler. It
  parses the message definitions (data), builds an *isolated* descriptor pool, and
  exposes each message type by name for encode/decode, so the adapter owns its own
  wire. A malformed descriptor set is a typed refusal, never an exception; invoking an
  undeclared message is an ``unsupported capability`` refusal.
* :func:`assess_tag_change` / :class:`TagChangeAssessment` — the pin governance. A tag
  change mints a new capability declaration and forces re-verification; it bumps a
  CT-* format version only where the wire change alters that contract's public shape,
  detected as a descriptor-set digest difference. A digest change under an *unchanged*
  tag is a pin-integrity violation — exactly the silent update the pin exists to
  prevent (AR-43, DEC-0141, edge).

A compiled proto message never leaks into ``qmf-core``: this module imports only
``qmf-core`` and the ``protobuf`` runtime, and nothing imports ``qmf-venue`` (AR-06,
AR-42, L30/DEC-0120). No binary float touches the money path here — the module handles
descriptor bytes and message types only, never a decoded money value (DEC-0105).
Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.message import DecodeError, Message
from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "SPOTWARE_PROTO_PACKAGE",
    "CompiledProto",
    "ProtoArtifact",
    "TagChangeAssessment",
    "assess_tag_change",
    "compile_descriptor_set",
    "descriptor_set_digest",
]

# The AD-6 register identity of the venue protocol artifact — the Spotware package
# NAME, whose proto message definitions (data, not code) are the only thing consumed.
# This is a fixed identity string, NOT the tunable release tag: the integer tag is the
# registry value `registry:venue_protocol_artifact`, injected by the composition root
# and never hardcoded in this module (DEC-0141).
SPOTWARE_PROTO_PACKAGE: Final[str] = "openapi-proto-messages"

# The self-describing prefix on a descriptor-set content digest. A plain content hash
# over the compiled protocol bytes — deliberately distinct from CT-05's fp1
# domain-identity recipe, which is for structured domain values, never raw protocol
# descriptors.
_DIGEST_PREFIX: Final[str] = "sha256"


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a malformed artifact or descriptor returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unsupported(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unsupported capability`` refusal an undeclared message returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


# --- validation helpers -----------------------------------------------------


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- the descriptor-set digest ----------------------------------------------


def _digest_of(descriptor_set: descriptor_pb2.FileDescriptorSet) -> str:
    """The content digest of an already-parsed descriptor set.

    Normalized before hashing — files sorted by name, ``source_code_info`` (comments,
    formatting) cleared — so the digest reflects the wire/public shape only: a
    comment-only change never moves it, while a field, type, or name change does.
    """
    normalized = descriptor_pb2.FileDescriptorSet()
    for file_proto in sorted(descriptor_set.file, key=lambda proto: proto.name):
        copied = normalized.file.add()
        copied.CopyFrom(file_proto)
        copied.ClearField("source_code_info")
    canonical = normalized.SerializeToString(deterministic=True)
    return f"{_DIGEST_PREFIX}:{hashlib.sha256(canonical).hexdigest()}"


def _parse_descriptor_set(
    descriptor_set_bytes: object,
) -> Result[descriptor_pb2.FileDescriptorSet]:
    """Parse serialized proto message definitions into a descriptor set, value-or-refusal.

    The bytes are the serialized ``FileDescriptorSet`` — the proto message definitions
    as *data*. Non-bytes input or bytes that are not a valid descriptor set are an
    ``invalid input`` refusal, never an exception.
    """
    if not isinstance(descriptor_set_bytes, (bytes, bytearray)):
        return _invalid(
            "descriptor_set_bytes",
            "the proto message definitions are consumed as bytes (a serialized "
            "FileDescriptorSet), not code",
            given=type(descriptor_set_bytes).__name__,
        )
    parsed = descriptor_pb2.FileDescriptorSet()
    try:
        parsed.ParseFromString(bytes(descriptor_set_bytes))
    except (DecodeError, ValueError) as exc:
        return _invalid(
            "descriptor_set_bytes",
            "the bytes are not a valid proto FileDescriptorSet",
            error=str(exc),
        )
    return Ok(parsed)


def descriptor_set_digest(descriptor_set_bytes: object) -> Result[str]:
    """Compute the content digest over serialized proto message definitions.

    A ``sha256:<hex>`` digest over the normalized descriptor set (see :func:`_digest_of`).
    A malformed descriptor set is an ``invalid input`` refusal.
    """
    parsed = _parse_descriptor_set(descriptor_set_bytes)
    if isinstance(parsed, TypedRefusal):
        return parsed
    return Ok(_digest_of(parsed.value))


# --- the pinned artifact identity -------------------------------------------


@dataclass(frozen=True, slots=True)
class ProtoArtifact:
    """The pinned venue protocol artifact identity (CT-18; AR-43, DEC-0141).

    ``package_name`` is the Spotware package (``openapi-proto-messages``);
    ``release_tag`` is the pinned AD-6 integer release tag (injected from
    ``registry:venue_protocol_artifact``, never hardcoded); ``descriptor_set_digest``
    is the ``sha256:<hex>`` content digest of the compiled message definitions, so a
    wire change is a visible, comparable event and the artifact's identity is
    identity-bearing for any decode that depended on it.
    """

    package_name: str
    release_tag: int
    descriptor_set_digest: str

    @classmethod
    def try_create(
        cls,
        package_name: object,
        release_tag: object,
        descriptor_set_digest: object,
    ) -> Result[ProtoArtifact]:
        """Validate and build a :class:`ProtoArtifact`, returning value-or-refusal.

        A blank package name, a non-positive / ``bool`` / non-integer release tag, or a
        digest that is not a ``sha256:``-prefixed string is an ``invalid input`` refusal.
        The tag is injected — a positive integer, never hardcoded (DEC-0141).
        """
        name = _clean_str(package_name)
        if name is None:
            return _invalid(
                "package_name",
                "the venue protocol artifact names its Spotware package",
                given=repr(package_name),
            )
        # Inline the int check so the type narrows for the constructor below; a ``bool``
        # is not a tag even though it is an ``int`` subclass.
        if isinstance(release_tag, bool) or not isinstance(release_tag, int) or release_tag <= 0:
            return _invalid(
                "release_tag",
                "the pinned Spotware proto release tag is a positive integer, injected "
                "from registry:venue_protocol_artifact and never hardcoded",
                given=repr(release_tag),
            )
        digest = _clean_str(descriptor_set_digest)
        if digest is None or not digest.startswith(f"{_DIGEST_PREFIX}:"):
            return _invalid(
                "descriptor_set_digest",
                f"the descriptor-set digest is a '{_DIGEST_PREFIX}:<hex>' content hash",
                given=repr(descriptor_set_digest),
            )
        return Ok(cls(package_name=name, release_tag=release_tag, descriptor_set_digest=digest))


# --- the in-house compiled protocol -----------------------------------------


@dataclass(frozen=True, slots=True)
class CompiledProto:
    """The in-house-compiled Spotware protocol (Story 8.2; AR-43, DEC-0141).

    Built by :func:`compile_descriptor_set` from proto message definitions consumed as
    data. ``artifact`` is the pinned :class:`ProtoArtifact`; ``pool`` is the *isolated*
    descriptor pool this compilation owns (never the global default pool, so two
    compilations at different tags never collide); ``message_types`` maps each declared
    message's full name to its runtime class. The adapter owns its own transport
    through these classes — no Spotware SDK code runs.
    """

    artifact: ProtoArtifact
    pool: descriptor_pool.DescriptorPool
    message_types: Mapping[str, type[Message]]

    def message_names(self) -> tuple[str, ...]:
        """Every declared message full-name, sorted."""
        return tuple(sorted(self.message_types))

    def message_class(self, full_name: object) -> Result[type[Message]]:
        """The runtime message class for ``full_name``, value-or-refusal.

        A name the pinned release does not declare is an ``unsupported capability``
        refusal — invoking anything undeclared is refused, never emulated (CT-18).
        """
        name = _clean_str(full_name)
        if name is None:
            return _invalid(
                "full_name", "a message full-name is a non-empty string", given=repr(full_name)
            )
        message_class = self.message_types.get(name)
        if message_class is None:
            return _unsupported(
                "full_name",
                "the pinned proto release declares no such message",
                given=name,
                pinned_tag=self.artifact.release_tag,
            )
        return Ok(message_class)

    def decode(self, full_name: object, wire_bytes: object) -> Result[Message]:
        """Decode ``wire_bytes`` as the message ``full_name``, value-or-refusal.

        The adapter's own transport: no Spotware code decodes the wire. An undeclared
        message is an ``unsupported capability`` refusal; bytes that do not parse as
        that message are an ``invalid input`` refusal, never an exception.
        """
        resolved = self.message_class(full_name)
        if isinstance(resolved, TypedRefusal):
            return resolved
        if not isinstance(wire_bytes, (bytes, bytearray)):
            return _invalid(
                "wire_bytes", "a proto message decodes from bytes", given=type(wire_bytes).__name__
            )
        message = resolved.value()
        try:
            message.ParseFromString(bytes(wire_bytes))
        except (DecodeError, ValueError) as exc:
            return _invalid(
                "wire_bytes",
                "the bytes do not parse as this proto message",
                message=self._full_name_of(resolved.value),
                error=str(exc),
            )
        return Ok(message)

    @staticmethod
    def _full_name_of(message_class: type[Message]) -> str:
        """The declared full-name of a compiled message class."""
        return message_class.DESCRIPTOR.full_name


def _message_full_names(file_proto: descriptor_pb2.FileDescriptorProto) -> list[str]:
    """Every message full-name a proto file declares (top-level and nested), from data.

    Read off the parsed ``FileDescriptorProto`` message definitions — the package
    prefix plus each message name, recursing into nested types — so the compiler names
    what it declared without walking the pool's descriptor graph.
    """
    prefix = f"{file_proto.package}." if file_proto.package else ""
    names: list[str] = []

    def _collect(scope: str, message_proto: descriptor_pb2.DescriptorProto) -> None:
        full_name = f"{scope}{message_proto.name}"
        names.append(full_name)
        for nested in message_proto.nested_type:
            _collect(f"{full_name}.", nested)

    for message_proto in file_proto.message_type:
        _collect(prefix, message_proto)
    return names


def compile_descriptor_set(
    descriptor_set_bytes: object,
    *,
    package_name: object,
    release_tag: object,
) -> Result[CompiledProto]:
    """Compile proto message definitions in-house, returning value-or-refusal.

    ``descriptor_set_bytes`` is the serialized ``FileDescriptorSet`` — the Spotware
    ``openapi-proto-messages`` release's message definitions carried as *data*.
    ``release_tag`` is the pinned AD-6 integer tag, injected never hardcoded. The
    compiler builds an isolated descriptor pool (so compilations at different tags
    never collide in the global pool), indexes every declared message by full-name, and
    records the content digest into the returned :class:`ProtoArtifact`. Malformed
    definitions, an unresolved import, or a duplicate file are an ``invalid input``
    refusal — never an exception, and never a silent partial compilation (DEC-0141).
    """
    parsed = _parse_descriptor_set(descriptor_set_bytes)
    if isinstance(parsed, TypedRefusal):
        return parsed
    descriptor_files = parsed.value.file
    pool = descriptor_pool.DescriptorPool()
    message_types: dict[str, type[Message]] = {}
    try:
        for file_proto in descriptor_files:
            pool.Add(file_proto)
        # Message full-names come from the parsed definitions (data); classes are then
        # resolved through the pool — so the message index is built without leaning on
        # the loosely typed descriptor graph the pool's own return values expose.
        for file_proto in descriptor_files:
            for full_name in _message_full_names(file_proto):
                descriptor = pool.FindMessageTypeByName(full_name)
                message_types[full_name] = message_factory.GetMessageClass(descriptor)
    except (TypeError, KeyError, ValueError) as exc:
        return _invalid(
            "descriptor_set_bytes",
            "the proto message definitions did not compile (an unresolved import, a "
            "duplicate file, or a malformed descriptor)",
            error=str(exc),
        )
    digest = _digest_of(parsed.value)
    artifact = ProtoArtifact.try_create(package_name, release_tag, digest)
    if isinstance(artifact, TypedRefusal):
        return artifact
    return Ok(
        CompiledProto(
            artifact=artifact.value,
            pool=pool,
            message_types=MappingProxyType(dict(message_types)),
        )
    )


# --- pin-change governance --------------------------------------------------


@dataclass(frozen=True, slots=True)
class TagChangeAssessment:
    """The governed verdict on a proposed venue-protocol-tag change (AR-43, DEC-0141).

    ``changed`` — the proposed artifact differs from the pinned one at all.
    ``re_verification_required`` / ``capability_declaration_reminted`` — a tag change
    (or a broken pin) mints a new CT-18 capability declaration and forces
    re-verification; both are set on any change.
    ``wire_shape_changed`` — the compiled descriptor set's public shape differs (a
    digest difference).
    ``format_version_bump_required`` — a CT-* format version bumps only where the wire
    change alters that contract's public shape, i.e. exactly when ``wire_shape_changed``.
    ``pin_integrity_violation`` — the descriptor set moved under an *unchanged* tag: the
    silent update the pin exists to prevent, always alarmed.
    """

    changed: bool
    re_verification_required: bool
    capability_declaration_reminted: bool
    wire_shape_changed: bool
    format_version_bump_required: bool
    pin_integrity_violation: bool
    pinned_tag: int
    proposed_tag: int
    detail: str


def assess_tag_change(pinned: object, proposed: object) -> Result[TagChangeAssessment]:
    """Assess a proposed venue-protocol artifact against the pinned one, value-or-refusal.

    Both arguments are :class:`ProtoArtifact` values naming the *same* Spotware package;
    a package-name mismatch (comparing two different protocols) is an ``invalid input``
    refusal. On a tag change, re-verification is forced and a new capability declaration
    is minted; a CT-* format version bumps only when the descriptor-set digest also
    moved. A digest change under an unchanged tag is flagged as a pin-integrity
    violation (DEC-0141).
    """
    if not isinstance(pinned, ProtoArtifact):
        return _invalid("pinned", "the pinned artifact is a ProtoArtifact", given=repr(pinned))
    if not isinstance(proposed, ProtoArtifact):
        return _invalid(
            "proposed", "the proposed artifact is a ProtoArtifact", given=repr(proposed)
        )
    if pinned.package_name != proposed.package_name:
        return _invalid(
            "package_name",
            "a tag-change assessment compares two versions of the same protocol artifact",
            pinned=pinned.package_name,
            proposed=proposed.package_name,
        )
    tag_changed = pinned.release_tag != proposed.release_tag
    digest_changed = pinned.descriptor_set_digest != proposed.descriptor_set_digest
    if not tag_changed and not digest_changed:
        return Ok(
            TagChangeAssessment(
                changed=False,
                re_verification_required=False,
                capability_declaration_reminted=False,
                wire_shape_changed=False,
                format_version_bump_required=False,
                pin_integrity_violation=False,
                pinned_tag=pinned.release_tag,
                proposed_tag=proposed.release_tag,
                detail=(
                    f"pinned tag {pinned.release_tag} unchanged and the compiled descriptor "
                    "set is byte-identical; no re-verification and no format-version bump"
                ),
            )
        )
    if not tag_changed and digest_changed:
        return Ok(
            TagChangeAssessment(
                changed=True,
                re_verification_required=True,
                capability_declaration_reminted=True,
                wire_shape_changed=True,
                format_version_bump_required=True,
                pin_integrity_violation=True,
                pinned_tag=pinned.release_tag,
                proposed_tag=proposed.release_tag,
                detail=(
                    f"the descriptor set moved under an unchanged tag {pinned.release_tag}: a "
                    "silent update the pin exists to prevent — re-verify and re-mint, and alarm"
                ),
            )
        )
    return Ok(
        TagChangeAssessment(
            changed=True,
            re_verification_required=True,
            capability_declaration_reminted=True,
            wire_shape_changed=digest_changed,
            format_version_bump_required=digest_changed,
            pin_integrity_violation=False,
            pinned_tag=pinned.release_tag,
            proposed_tag=proposed.release_tag,
            detail=(
                f"tag change {pinned.release_tag} -> {proposed.release_tag} mints a new "
                "capability declaration and forces re-verification; "
                + (
                    "the wire shape changed, so the touched CT-* format version bumps"
                    if digest_changed
                    else "the wire shape is unchanged, so no CT-* format version bumps"
                )
            ),
        )
    )
