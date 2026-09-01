"""Boot ceremony: doors → boot-attempt → preflight → compose → fingerprint → seal.

Story 25.5 / FR-052 / TN-2 (DEC-0187). The supervisor/door layer binds first so a
boot that never finishes stays observable. The reserved supervisor WriterId lays
down the boot-attempt record as the first durable write. Only a failure to bind
the doors exits nonzero; every later detected refusal enters stand-down-alive with
status evidence still served. Check mode (TN-16) runs the venue-independent subset,
opens no sequencer, mutates no runtime state, and exits nonzero on refusal.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableSequence, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, Protocol, cast

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmn.config.compiler import ResolvedNodeConfig
from qmn.doors import EVIDENCE_DOOR, POWERS_DOOR
from qmn.host._refuse import clean_token, invalid, policy
from qmn.host.light_heavy import (
    ResolvedCompositionClasses,
    WorkloadClaim,
    resolve_composition_classes,
    workload_claim_identity_content,
)

__all__ = [
    "BOOT_BOUND_SURFACES",
    "BOOT_CEREMONY_SURFACE",
    "BOOT_STAGES",
    "CHECK_MODE_EXIT_ON_REFUSAL",
    "CHECK_MODE_OPENS_SEQUENCER",
    "CHECK_MODE_PREFLIGHT_CHECKS",
    "DOOR_BIND_FAILURE_EXIT_CODE",
    "FULL_PREFLIGHT_CHECKS",
    "HAS_OPERATOR_CLI",
    "SUPERVISOR_ROLE",
    "SUPERVISOR_STREAM",
    "BootAttemptRecord",
    "BootAttemptSink",
    "BootCeremonyOutcome",
    "BoundSupervisorDoors",
    "CompositionFingerprintInputs",
    "InMemoryBootAttemptSink",
    "PreflightFacts",
    "SealedBootEpoch",
    "WriterAllocation",
    "allocate_writer_ids",
    "bind_supervisor_doors",
    "compute_composition_fp",
    "preflight_checks_for_mode",
    "reserved_supervisor_writer",
    "run_boot_ceremony",
    "run_check_mode",
    "supervisor_writer_is_reserved",
]

BOOT_CEREMONY_SURFACE: Final[str] = "qmn.host"
HAS_OPERATOR_CLI: Final[bool] = False

# Surfaces that must bind before act 1 (DEC-0187, DEC-0226).
BOOT_BOUND_SURFACES: Final[tuple[str, ...]] = (
    "evidence_channel",
    "preflight_status",
    "resurrect_power",
)

SUPERVISOR_ROLE: Final[str] = "supervisor"
SUPERVISOR_STREAM: Final[str] = "boot-lifecycle"

# Ordered durable stages stamped on the boot-attempt record.
BOOT_STAGES: Final[tuple[str, ...]] = (
    "doors_bound",
    "boot_attempt_written",
    "preflight",
    "compose",
    "fingerprint",
    "seal",
)

FULL_PREFLIGHT_CHECKS: Final[tuple[str, ...]] = (
    "host_machine_tuple",
    "disk_headroom",
    "chrony_waitsync",
    "credential_is_set",
    "store_reachability",
    "tree_ownership_modes",
    "dependency_pins",
    "unit_principals",
    "writer_id_namespace",
)

# Check mode skips venue/credential/store/chrony gates (DEC-0201).
CHECK_MODE_PREFLIGHT_CHECKS: Final[tuple[str, ...]] = (
    "host_machine_tuple",
    "disk_headroom",
    "tree_ownership_modes",
    "dependency_pins",
    "unit_principals",
    "writer_id_namespace",
)

DOOR_BIND_FAILURE_EXIT_CODE: Final[int] = 1
CHECK_MODE_EXIT_ON_REFUSAL: Final[bool] = True
CHECK_MODE_OPENS_SEQUENCER: Final[bool] = False

BootMode = Literal["live", "check"]


class BootAttemptSink(Protocol):
    """Durable sink for the supervisor boot-attempt / lifecycle stream."""

    def append(self, record: BootAttemptRecord, /) -> Result[BootAttemptRecord]:
        """Persist one boot-attempt record; first write of the boot."""
        ...

    def amend(self, record: BootAttemptRecord, /) -> Result[BootAttemptRecord]:
        """Amend stage / composition_fp on the existing attempt (same sequence)."""
        ...


@dataclass(frozen=True, slots=True)
class BootAttemptRecord:
    """First durable write of a boot (DEC-0187, DEC-0226).

    ``composition_fp`` is stamped as an amendment at fingerprint/seal, never as
    hashed content of the attempt's identity.
    """

    boot_epoch_id: str
    unit_role: str
    stage: str
    writer: WriterId
    sequence: int
    reason: str | None = None
    composition_fp: Fingerprint | None = None
    failure_id: str | None = None

    def as_status(self) -> Mapping[str, object]:
        """Evidence-channel projection of the attempt (no secrets)."""
        body: dict[str, object] = {
            "boot_epoch_id": self.boot_epoch_id,
            "unit_role": self.unit_role,
            "stage": self.stage,
            "sequence": self.sequence,
            "writer": {
                "machine": self.writer.machine,
                "role": self.writer.role,
                "stream": self.writer.stream,
                "boot_epoch_id": self.writer.boot_epoch_id,
            },
        }
        if self.reason is not None:
            body["reason"] = self.reason
        if self.composition_fp is not None:
            body["composition_fp"] = self.composition_fp.value
        if self.failure_id is not None:
            body["failure_id"] = self.failure_id
        return MappingProxyType(body)


@dataclass
class InMemoryBootAttemptSink:
    """Test/double sink — append-only list under the reserved supervisor writer."""

    records: MutableSequence[BootAttemptRecord] = field(
        default_factory=list[BootAttemptRecord]
    )

    def append(self, record: BootAttemptRecord, /) -> Result[BootAttemptRecord]:
        if self.records and record.sequence <= self.records[-1].sequence:
            return invalid(
                "sequence",
                "boot-attempt sequence is gapless and strictly increasing per "
                "(supervisor writer, boot-epoch)",
                given=record.sequence,
            )
        self.records.append(record)
        return Ok(record)

    def amend(self, record: BootAttemptRecord, /) -> Result[BootAttemptRecord]:
        if not self.records:
            return invalid(
                "boot_attempt",
                "amend requires a prior durable boot-attempt write",
            )
        last = self.records[-1]
        if (
            last.boot_epoch_id != record.boot_epoch_id
            or last.sequence != record.sequence
            or last.writer != record.writer
        ):
            return policy(
                "boot_attempt",
                "amend updates stage/composition_fp on the same attempt, never a new write",
            )
        self.records[-1] = record
        return Ok(record)


@dataclass(frozen=True, slots=True)
class BoundSupervisorDoors:
    """Doors bound before preflight so stand-down stays observable."""

    evidence_channel: str
    powers_channel: str
    preflight_status_ready: bool
    resurrect_power_ready: bool
    bound: bool = True

    def surfaces(self) -> tuple[str, ...]:
        return BOOT_BOUND_SURFACES


@dataclass(frozen=True, slots=True)
class PreflightFacts:
    """Injectable host facts for the preflight gate (no ambient I/O in tests)."""

    host_machine_tuple_ok: bool = True
    disk_headroom_ok: bool = True
    chrony_synced: bool = True
    required_credential_refs: tuple[str, ...] = ()
    credential_is_set: Mapping[str, bool] = field(default_factory=dict[str, bool])
    stores_reachable: bool = True
    tree_ownership_ok: bool = True
    dependency_pins_ok: bool = True
    unit_principals_ok: bool = True
    writer_id_namespace_ok: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "credential_is_set",
            MappingProxyType(dict(self.credential_is_set)),
        )


@dataclass(frozen=True, slots=True)
class CompositionFingerprintInputs:
    """Governed inputs of ``composition_fp`` (DEC-0187).

    Calendar DATA snapshots and the post-seal venue-observation profile are
    deliberately excluded. Candidate labelers belong on ``shadow_composition_fp``.
    Class-affecting workload declarations (declared four-bound budgets) ride into
    identity as contract surface; the light/heavy *verdict* never does (AD-24).
    """

    config_fp: Fingerprint
    distribution_identities: Mapping[str, str]
    extension_identities: Mapping[str, str] = field(default_factory=dict[str, str])
    proto_release_tag: str = "unset"
    tzdata_version: str = "unset"
    adapter_capability_fps: tuple[Fingerprint, ...] = ()
    registry_as_of_fp: Fingerprint | None = None
    calendar_code_identities: Mapping[str, str] = field(default_factory=dict[str, str])
    os_cpu_class: str = "unset"
    shadow_candidate_identities: Mapping[str, str] = field(default_factory=dict[str, str])
    workload_claim_identities: Mapping[str, object] = field(
        default_factory=dict[str, object]
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "distribution_identities",
            MappingProxyType(dict(self.distribution_identities)),
        )
        object.__setattr__(
            self,
            "extension_identities",
            MappingProxyType(dict(self.extension_identities)),
        )
        object.__setattr__(
            self,
            "calendar_code_identities",
            MappingProxyType(dict(self.calendar_code_identities)),
        )
        object.__setattr__(
            self,
            "shadow_candidate_identities",
            MappingProxyType(dict(self.shadow_candidate_identities)),
        )
        object.__setattr__(
            self,
            "workload_claim_identities",
            MappingProxyType(dict(self.workload_claim_identities)),
        )

    def governed_identity(self) -> dict[str, object]:
        """Fingerprintable body for governed ``composition_fp`` only."""
        return {
            "class": "composition_fp",
            "config_fp": self.config_fp.value,
            "distribution_identities": dict(
                sorted(self.distribution_identities.items())
            ),
            "extension_identities": dict(sorted(self.extension_identities.items())),
            "proto_release_tag": self.proto_release_tag,
            "tzdata_version": self.tzdata_version,
            "adapter_capability_fps": tuple(
                sorted(fp.value for fp in self.adapter_capability_fps)
            ),
            "registry_as_of_fp": (
                None if self.registry_as_of_fp is None else self.registry_as_of_fp.value
            ),
            "calendar_code_identities": dict(
                sorted(self.calendar_code_identities.items())
            ),
            "os_cpu_class": self.os_cpu_class,
            "workload_claim_identities": dict(self.workload_claim_identities),
        }

    def shadow_identity(self) -> dict[str, object]:
        """Separate fingerprint body for candidate labelers (never governed)."""
        return {
            "class": "shadow_composition_fp",
            "candidates": dict(sorted(self.shadow_candidate_identities.items())),
        }


@dataclass(frozen=True, slots=True)
class WriterAllocation:
    """Compose-time WriterId set; supervisor is reserved, not re-issued."""

    supervisor: WriterId
    allocated: tuple[WriterId, ...]

    @property
    def all_writers(self) -> tuple[WriterId, ...]:
        return (self.supervisor, *self.allocated)

    def pairwise_distinct(self) -> bool:
        keys = [w.order_tuple() for w in self.all_writers]
        return len(keys) == len(set(keys))


@dataclass(frozen=True, slots=True)
class SealedBootEpoch:
    """Immutable sealed composition for one boot epoch."""

    composition_fp: Fingerprint
    shadow_composition_fp: Fingerprint | None
    writer_allocation: WriterAllocation
    boot_epoch_id: str
    sealed: bool = True
    ready: bool = True
    opens_sequencer: bool = True
    composition_classes: ResolvedCompositionClasses | None = None


@dataclass(frozen=True, slots=True)
class BootCeremonyOutcome:
    """Result of a live or check-mode boot ceremony after doors have bound."""

    mode: BootMode
    doors: BoundSupervisorDoors
    boot_attempt: BootAttemptRecord
    stage_reached: str
    preflight_status: Mapping[str, object]
    composition_fp: Fingerprint | None
    shadow_composition_fp: Fingerprint | None
    writer_allocation: WriterAllocation | None
    sealed: bool
    ready: bool
    stand_down_alive: bool
    opens_sequencer: bool
    exit_code: int | None
    failure_id: str | None = None
    composition_classes: ResolvedCompositionClasses | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "preflight_status", MappingProxyType(dict(self.preflight_status))
        )


def preflight_checks_for_mode(mode: object) -> Result[tuple[str, ...]]:
    """Return the ordered preflight check roster for ``live`` or ``check``."""
    mode_name = clean_token(mode)
    if mode_name == "live":
        return Ok(FULL_PREFLIGHT_CHECKS)
    if mode_name == "check":
        return Ok(CHECK_MODE_PREFLIGHT_CHECKS)
    return invalid(
        "mode",
        "boot ceremony mode is live or check",
        given=repr(mode),
    )


def reserved_supervisor_writer(*, machine: object, boot_epoch_id: object) -> Result[WriterId]:
    """Mint the reserved supervisor WriterId — constant of the unit role."""
    return WriterId.try_create(machine, SUPERVISOR_ROLE, SUPERVISOR_STREAM, boot_epoch_id)


def supervisor_writer_is_reserved(writer: object) -> bool:
    """True when ``writer`` is the reserved supervisor stream (Compose may not re-issue)."""
    return (
        isinstance(writer, WriterId)
        and writer.role == SUPERVISOR_ROLE
        and writer.stream == SUPERVISOR_STREAM
    )


def bind_supervisor_doors(
    *,
    binder: Callable[[], Result[BoundSupervisorDoors]] | None = None,
) -> Result[BoundSupervisorDoors]:
    """Bind evidence, preflight-status, and resurrect before any state mutation.

    A failure here is the only boot failure that exits nonzero before stand-down
    can serve (FM-14 / DEC-0226).
    """
    if binder is not None:
        bound = binder()
        if is_refusal(bound):
            return _door_bind_refusal(bound)
        if not bound.value.bound:
            return _door_bind_refusal(
                invalid(
                    "doors",
                    "supervisor doors must bind before the boot-attempt write",
                )
            )
        return bound
    return Ok(
        BoundSupervisorDoors(
            evidence_channel=EVIDENCE_DOOR,
            powers_channel=POWERS_DOOR,
            preflight_status_ready=True,
            resurrect_power_ready=True,
            bound=True,
        )
    )


def _door_bind_refusal(refusal: TypedRefusal) -> TypedRefusal:
    context = dict(refusal.context)
    context["exits_nonzero"] = True
    context["exit_code"] = DOOR_BIND_FAILURE_EXIT_CODE
    context["stand_down_alive"] = False
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=context,
    )


def allocate_writer_ids(
    *,
    machine: object,
    boot_epoch_id: object,
    streams: object,
) -> Result[WriterAllocation]:
    """Allocate Compose WriterIds from a declared namespace; prove pairwise distinct.

    ``streams`` is a sequence of ``(role, stream)`` pairs. The reserved supervisor
    WriterId is included in the distinctness proof and must never appear in
    ``streams`` (Compose may never re-issue it).
    """
    machine_token = clean_token(machine)
    if machine_token is None:
        return invalid("machine", "Compose allocates WriterIds on a named machine")
    boot_token = clean_token(boot_epoch_id)
    if boot_token is None:
        return invalid("boot_epoch_id", "WriterIds carry the boot epoch id")
    if not isinstance(streams, Sequence) or isinstance(streams, (str, bytes)):
        return invalid(
            "streams",
            "Compose allocates from a declared (role, stream) namespace sequence",
            given=type(streams).__name__,
        )

    supervisor = reserved_supervisor_writer(machine=machine_token, boot_epoch_id=boot_token)
    if is_refusal(supervisor):
        return supervisor

    allocated: list[WriterId] = []
    seen: set[tuple[str, str, str, str]] = {supervisor.value.order_tuple()}
    stream_items = cast("Sequence[object]", streams)
    for index, raw_item in enumerate(stream_items):
        if isinstance(raw_item, (str, bytes)) or not isinstance(raw_item, Sequence):
            return invalid(
                "streams",
                "each allocation entry is a (role, stream) pair",
                index=index,
                given=type(raw_item).__name__,
            )
        pair = tuple(cast("Sequence[object]", raw_item))
        if len(pair) != 2:
            return invalid(
                "streams",
                "each allocation entry is a (role, stream) pair",
                index=index,
                given=f"len={len(pair)}",
            )
        role, stream = pair[0], pair[1]
        role_token = clean_token(role)
        stream_token = clean_token(stream)
        if role_token is None or stream_token is None:
            return invalid(
                "streams",
                "role and stream tokens are non-blank",
                index=index,
            )
        if role_token == SUPERVISOR_ROLE and stream_token == SUPERVISOR_STREAM:
            return policy(
                "streams",
                "Compose may never re-issue the reserved supervisor WriterId",
                index=index,
            )
        writer = WriterId.try_create(machine_token, role_token, stream_token, boot_token)
        if is_refusal(writer):
            return writer
        key = writer.value.order_tuple()
        if key in seen:
            return policy(
                "writer_ids",
                "allocated WriterIds must be pairwise distinct before Seal",
                colliding=list(key),
            )
        seen.add(key)
        allocated.append(writer.value)

    allocation = WriterAllocation(supervisor=supervisor.value, allocated=tuple(allocated))
    if not allocation.pairwise_distinct():
        return policy(
            "writer_ids",
            "allocated WriterIds must be pairwise distinct before Seal",
        )
    return Ok(allocation)


def compute_composition_fp(inputs: object) -> Result[tuple[Fingerprint, Fingerprint | None]]:
    """Compute governed ``composition_fp`` and optional ``shadow_composition_fp``."""
    if not isinstance(inputs, CompositionFingerprintInputs):
        return invalid(
            "inputs",
            "composition_fp is computed from CompositionFingerprintInputs",
            given=type(inputs).__name__,
        )
    governed = fingerprint(inputs.governed_identity())
    if is_refusal(governed):
        return governed
    shadow: Fingerprint | None = None
    if inputs.shadow_candidate_identities:
        shadow_result = fingerprint(inputs.shadow_identity())
        if is_refusal(shadow_result):
            return shadow_result
        shadow = shadow_result.value
        if shadow.digest == governed.value.digest:
            return policy(
                "shadow_composition_fp",
                "shadow_composition_fp must stay separate from governed composition_fp",
            )
    return Ok((governed.value, shadow))


def _run_preflight(
    *,
    facts: PreflightFacts,
    mode: BootMode,
    config: ResolvedNodeConfig | None,
) -> Result[Mapping[str, object]]:
    checks = FULL_PREFLIGHT_CHECKS if mode == "live" else CHECK_MODE_PREFLIGHT_CHECKS
    status: dict[str, object] = {"mode": mode, "checks": {}}
    check_results = cast("dict[str, object]", status["checks"])

    if config is not None and mode == "live" and not config.may_boot():
        return policy(
            "config",
            "blank boot-blocking value-status rows refuse preflight",
            failure_id="preflight.config.boot_blocking",
            rows=list(config.boot_blocking_rows()),
        )

    for name in checks:
        ok, failure_id, detail = _evaluate_check(name, facts)
        check_results[name] = {"ok": ok, **detail}
        if not ok:
            return policy(
                "preflight",
                f"detected preflight refusal at {name}",
                failure_id=failure_id,
                check=name,
                status=status,
            )
    status["ok"] = True
    return Ok(MappingProxyType(status))


def _evaluate_check(
    name: str, facts: PreflightFacts
) -> tuple[bool, str, dict[str, object]]:
    if name == "host_machine_tuple":
        return (
            facts.host_machine_tuple_ok,
            "preflight.host.machine_tuple",
            {},
        )
    if name == "disk_headroom":
        return facts.disk_headroom_ok, "preflight.disk.headroom", {}
    if name == "chrony_waitsync":
        return facts.chrony_synced, "preflight.clock.chrony", {}
    if name == "credential_is_set":
        missing = [
            ref
            for ref in facts.required_credential_refs
            if facts.credential_is_set.get(ref) is not True
        ]
        return (
            not missing,
            "preflight.credential.is_set",
            {"missing_refs": missing},
        )
    if name == "store_reachability":
        return facts.stores_reachable, "preflight.store.reachability", {}
    if name == "tree_ownership_modes":
        return facts.tree_ownership_ok, "preflight.tree.ownership", {}
    if name == "dependency_pins":
        return facts.dependency_pins_ok, "preflight.deps.pins", {}
    if name == "unit_principals":
        return facts.unit_principals_ok, "preflight.unit.principals", {}
    if name == "writer_id_namespace":
        return facts.writer_id_namespace_ok, "preflight.writer.namespace", {}
    return False, f"preflight.unknown.{name}", {"unknown_check": name}


def run_boot_ceremony(
    *,
    boot_epoch_id: object,
    machine: object,
    unit_role: object = "qmn.service",
    mode: object = "live",
    config: object | None = None,
    composition_inputs: object,
    writer_streams: object = (),
    workload_claims: object = (),
    preflight: object | None = None,
    boot_attempt_sink: object,
    door_binder: Callable[[], Result[BoundSupervisorDoors]] | None = None,
    reason: object | None = None,
    mutate_runtime_state: bool = False,
) -> Result[BootCeremonyOutcome]:
    """Run doors → boot-attempt → preflight → compose → fingerprint → seal.

    Compose evaluates light/heavy claims over assembled definitions before Seal
    (Story 25.14 / AD-24). No operator CLI exists on this path (DEC-0211). Check
    mode never opens a sequencer and never mutates runtime state.
    """
    mode_name = clean_token(mode)
    if mode_name not in {"live", "check"}:
        return invalid("mode", "boot ceremony mode is live or check", given=repr(mode))
    boot_mode: BootMode = "check" if mode_name == "check" else "live"

    boot_token = clean_token(boot_epoch_id)
    if boot_token is None:
        return invalid("boot_epoch_id", "a boot epoch id names the process start")
    machine_token = clean_token(machine)
    if machine_token is None:
        return invalid("machine", "the host machine tuple names the VPS")
    role_token = clean_token(unit_role)
    if role_token is None:
        return invalid("unit_role", "the boot-attempt stamps the unit role")
    if not isinstance(boot_attempt_sink, InMemoryBootAttemptSink) and not (
        hasattr(boot_attempt_sink, "append") and hasattr(boot_attempt_sink, "amend")
    ):
        return invalid(
            "boot_attempt_sink",
            "the supervisor stream sink persists boot-attempt records",
            given=type(boot_attempt_sink).__name__,
        )
    sink = cast("BootAttemptSink", boot_attempt_sink)

    if boot_mode == "check" and mutate_runtime_state:
        return policy(
            "mutate_runtime_state",
            "check mode is safe on production paths without mutating runtime state",
        )

    resolved: ResolvedNodeConfig | None
    if config is None:
        resolved = None
    elif isinstance(config, ResolvedNodeConfig):
        resolved = config
    else:
        return invalid(
            "config",
            "Compose draws from one ResolvedNodeConfig artifact when supplied",
            given=type(config).__name__,
        )

    if preflight is None:
        facts = PreflightFacts()
    elif isinstance(preflight, PreflightFacts):
        facts = preflight
    else:
        return invalid(
            "preflight",
            "preflight facts are a PreflightFacts probe set",
            given=type(preflight).__name__,
        )

    if not isinstance(composition_inputs, CompositionFingerprintInputs):
        return invalid(
            "composition_inputs",
            "Fingerprint reads CompositionFingerprintInputs",
            given=type(composition_inputs).__name__,
        )
    if resolved is not None and composition_inputs.config_fp != resolved.fingerprint:
        return policy(
            "composition_inputs",
            "composition_fp cites the same resolved node-config fingerprint Compose used",
        )

    reason_token = clean_token(reason) if reason is not None else None

    # --- Act 0a: bind doors first ---
    doors = bind_supervisor_doors(binder=door_binder)
    if is_refusal(doors):
        return doors

    supervisor = reserved_supervisor_writer(machine=machine_token, boot_epoch_id=boot_token)
    if is_refusal(supervisor):
        return supervisor

    # --- Act 0b: first durable write ---
    attempt = BootAttemptRecord(
        boot_epoch_id=boot_token,
        unit_role=role_token,
        stage="doors_bound",
        writer=supervisor.value,
        sequence=0,
        reason=reason_token,
    )
    written = sink.append(attempt)
    if is_refusal(written):
        # Sink failure after doors bound → stand-down-alive (not a door-bind exit).
        if boot_mode == "check":
            return _check_mode_refusal(written)
        return Ok(
            _stand_down_outcome(
                mode=boot_mode,
                doors=doors.value,
                boot_attempt=attempt,
                stage="doors_bound",
                preflight_status={"ok": False, "failure": "boot_attempt_write"},
                failure_id="boot.attempt.write",
            )
        )
    attempt = BootAttemptRecord(
        boot_epoch_id=boot_token,
        unit_role=role_token,
        stage="boot_attempt_written",
        writer=supervisor.value,
        sequence=0,
        reason=reason_token,
    )
    amended = sink.amend(attempt)
    if is_refusal(amended):
        if boot_mode == "check":
            return _check_mode_refusal(amended)
        return Ok(
            _stand_down_outcome(
                mode=boot_mode,
                doors=doors.value,
                boot_attempt=written.value,
                stage="doors_bound",
                preflight_status={"ok": False, "failure": "boot_attempt_amend"},
                failure_id="boot.attempt.amend",
            )
        )
    attempt = amended.value

    # --- Act 1: preflight ---
    preflight_result = _run_preflight(facts=facts, mode=boot_mode, config=resolved)
    if is_refusal(preflight_result):
        failure_id = str(preflight_result.context.get("failure_id", "preflight.detected"))
        status = preflight_result.context.get("status", {"ok": False})
        attempt = BootAttemptRecord(
            boot_epoch_id=boot_token,
            unit_role=role_token,
            stage="preflight",
            writer=supervisor.value,
            sequence=0,
            reason=reason_token,
            failure_id=failure_id,
        )
        sink.amend(attempt)
        if boot_mode == "check":
            return _check_mode_refusal(preflight_result)
        return Ok(
            _stand_down_outcome(
                mode=boot_mode,
                doors=doors.value,
                boot_attempt=attempt,
                stage="preflight",
                preflight_status=cast("Mapping[str, object]", status),
                failure_id=failure_id,
            )
        )
    status_map = dict(preflight_result.value)
    attempt = BootAttemptRecord(
        boot_epoch_id=boot_token,
        unit_role=role_token,
        stage="preflight",
        writer=supervisor.value,
        sequence=0,
        reason=reason_token,
    )
    sink.amend(attempt)

    # --- Act 2: compose (WriterIds + light/heavy gate) ---
    allocation = allocate_writer_ids(
        machine=machine_token,
        boot_epoch_id=boot_token,
        streams=writer_streams,
    )
    if is_refusal(allocation):
        attempt = BootAttemptRecord(
            boot_epoch_id=boot_token,
            unit_role=role_token,
            stage="compose",
            writer=supervisor.value,
            sequence=0,
            reason=reason_token,
            failure_id="compose.writer_ids",
        )
        sink.amend(attempt)
        if boot_mode == "check":
            return _check_mode_refusal(allocation)
        return Ok(
            _stand_down_outcome(
                mode=boot_mode,
                doors=doors.value,
                boot_attempt=attempt,
                stage="compose",
                preflight_status=status_map,
                failure_id="compose.writer_ids",
            )
        )

    classified = _classify_workload_claims(workload_claims)
    if is_refusal(classified):
        failure_id = str(
            classified.context.get("failure_id", "compose.light_heavy")
        )
        attempt = BootAttemptRecord(
            boot_epoch_id=boot_token,
            unit_role=role_token,
            stage="compose",
            writer=supervisor.value,
            sequence=0,
            reason=reason_token,
            failure_id=failure_id,
        )
        sink.amend(attempt)
        if boot_mode == "check":
            return _check_mode_refusal(classified)
        return Ok(
            _stand_down_outcome(
                mode=boot_mode,
                doors=doors.value,
                boot_attempt=attempt,
                stage="compose",
                preflight_status=status_map,
                failure_id=failure_id,
            )
        )
    composition_classes = classified.value
    fingerprinted_inputs = _with_workload_claim_identities(
        composition_inputs, composition_classes.identity_content
    )

    attempt = BootAttemptRecord(
        boot_epoch_id=boot_token,
        unit_role=role_token,
        stage="compose",
        writer=supervisor.value,
        sequence=0,
        reason=reason_token,
    )
    sink.amend(attempt)

    # --- Act 3: fingerprint ---
    fps = compute_composition_fp(fingerprinted_inputs)
    if is_refusal(fps):
        attempt = BootAttemptRecord(
            boot_epoch_id=boot_token,
            unit_role=role_token,
            stage="fingerprint",
            writer=supervisor.value,
            sequence=0,
            reason=reason_token,
            failure_id="fingerprint.composition_fp",
        )
        sink.amend(attempt)
        if boot_mode == "check":
            return _check_mode_refusal(fps)
        return Ok(
            _stand_down_outcome(
                mode=boot_mode,
                doors=doors.value,
                boot_attempt=attempt,
                stage="fingerprint",
                preflight_status=status_map,
                failure_id="fingerprint.composition_fp",
            )
        )
    composition_fp, shadow_fp = fps.value
    attempt = BootAttemptRecord(
        boot_epoch_id=boot_token,
        unit_role=role_token,
        stage="fingerprint",
        writer=supervisor.value,
        sequence=0,
        reason=reason_token,
        composition_fp=composition_fp,
    )
    sink.amend(attempt)

    # --- Act 4: seal ---
    opens_sequencer = boot_mode == "live"
    sealed_epoch = SealedBootEpoch(
        composition_fp=composition_fp,
        shadow_composition_fp=shadow_fp,
        writer_allocation=allocation.value,
        boot_epoch_id=boot_token,
        sealed=True,
        ready=True,
        opens_sequencer=opens_sequencer,
        composition_classes=composition_classes,
    )
    attempt = BootAttemptRecord(
        boot_epoch_id=boot_token,
        unit_role=role_token,
        stage="seal",
        writer=supervisor.value,
        sequence=0,
        reason=reason_token,
        composition_fp=composition_fp,
    )
    sink.amend(attempt)
    _ = sealed_epoch  # epoch is carried on the outcome fields below

    return Ok(
        BootCeremonyOutcome(
            mode=boot_mode,
            doors=doors.value,
            boot_attempt=attempt,
            stage_reached="seal",
            preflight_status=status_map,
            composition_fp=composition_fp,
            shadow_composition_fp=shadow_fp,
            writer_allocation=allocation.value,
            sealed=True,
            ready=True,
            stand_down_alive=False,
            opens_sequencer=opens_sequencer,
            exit_code=None,
            failure_id=None,
            composition_classes=composition_classes,
        )
    )


def run_check_mode(
    *,
    boot_epoch_id: object,
    machine: object,
    unit_role: object = "qmn.service",
    config: object | None = None,
    composition_inputs: object,
    writer_streams: object = (),
    workload_claims: object = (),
    preflight: object | None = None,
    boot_attempt_sink: object,
    door_binder: Callable[[], Result[BoundSupervisorDoors]] | None = None,
) -> Result[BootCeremonyOutcome]:
    """Dry-run boot: venue-independent preflight, no sequencer, exit on refusal."""
    return run_boot_ceremony(
        boot_epoch_id=boot_epoch_id,
        machine=machine,
        unit_role=unit_role,
        mode="check",
        config=config,
        composition_inputs=composition_inputs,
        writer_streams=writer_streams,
        workload_claims=workload_claims,
        preflight=preflight,
        boot_attempt_sink=boot_attempt_sink,
        door_binder=door_binder,
        mutate_runtime_state=False,
    )


def _classify_workload_claims(
    workload_claims: object,
) -> Result[ResolvedCompositionClasses]:
    """Evaluate assembled claims at Compose; empty means no light claims."""
    if workload_claims is None:
        claims: tuple[WorkloadClaim, ...] = ()
    elif isinstance(workload_claims, Sequence) and not isinstance(
        workload_claims, (str, bytes)
    ):
        typed: list[WorkloadClaim] = []
        for item in cast("Sequence[object]", workload_claims):
            if not isinstance(item, WorkloadClaim):
                return invalid(
                    "workload_claims",
                    "Compose resolves a sequence of WorkloadClaim values",
                    given=type(item).__name__,
                )
            typed.append(item)
        claims = tuple(typed)
    else:
        return invalid(
            "workload_claims",
            "Compose resolves a sequence of WorkloadClaim values",
            given=type(workload_claims).__name__,
        )
    if not claims:
        return Ok(
            ResolvedCompositionClasses(
                assignments=(),
                identity_content=workload_claim_identity_content(()),
            )
        )
    return resolve_composition_classes(claims)


def _with_workload_claim_identities(
    inputs: CompositionFingerprintInputs,
    claim_identity: Mapping[str, object],
) -> CompositionFingerprintInputs:
    """Stamp class-affecting declarations into composition_fp inputs.

    An empty claim set leaves a blank ``workload_claim_identities`` map so
    compositions without registered producers keep their prior fingerprint
    body (omit-empty, never null).
    """
    claims = claim_identity.get("claims", ())
    if not claims:
        if not inputs.workload_claim_identities:
            return inputs
        stamped: Mapping[str, object] = {}
    else:
        stamped = dict(claim_identity)
    if dict(inputs.workload_claim_identities) == dict(stamped):
        return inputs
    return CompositionFingerprintInputs(
        config_fp=inputs.config_fp,
        distribution_identities=dict(inputs.distribution_identities),
        extension_identities=dict(inputs.extension_identities),
        proto_release_tag=inputs.proto_release_tag,
        tzdata_version=inputs.tzdata_version,
        adapter_capability_fps=inputs.adapter_capability_fps,
        registry_as_of_fp=inputs.registry_as_of_fp,
        calendar_code_identities=dict(inputs.calendar_code_identities),
        os_cpu_class=inputs.os_cpu_class,
        shadow_candidate_identities=dict(inputs.shadow_candidate_identities),
        workload_claim_identities=dict(stamped),
    )


def _stand_down_outcome(
    *,
    mode: BootMode,
    doors: BoundSupervisorDoors,
    boot_attempt: BootAttemptRecord,
    stage: str,
    preflight_status: Mapping[str, object],
    failure_id: str,
) -> BootCeremonyOutcome:
    """Detected refusal after doors bound — stay alive, doors serving, no exit."""
    status = dict(preflight_status)
    status["stand_down_alive"] = True
    status["failure_id"] = failure_id
    status["stage"] = stage
    return BootCeremonyOutcome(
        mode=mode,
        doors=doors,
        boot_attempt=boot_attempt,
        stage_reached=stage,
        preflight_status=status,
        composition_fp=boot_attempt.composition_fp,
        shadow_composition_fp=None,
        writer_allocation=None,
        sealed=False,
        ready=False,
        stand_down_alive=True,
        opens_sequencer=False,
        exit_code=None,
        failure_id=failure_id,
    )


def _check_mode_refusal(refusal: TypedRefusal) -> TypedRefusal:
    context = dict(refusal.context)
    context["exits_nonzero"] = True
    context["exit_code"] = DOOR_BIND_FAILURE_EXIT_CODE
    context["opens_sequencer"] = False
    context["mode"] = "check"
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=context,
    )
